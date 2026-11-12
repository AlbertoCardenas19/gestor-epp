import uuid

from django.db import models
from django.db.models import BigIntegerField, Case, F, Q, Sum, When
from django.urls import reverse


def stock_delta_expression(prefix=''):
    return Case(
        When(**{f'{prefix}operation': 'delivery'}, then=-F(f'{prefix}quantity')),
        default=F(f'{prefix}quantity'), output_field=BigIntegerField(),
    )


class StockPosition(models.Model):
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name='stock_positions')
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='stock_positions')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'item'], name='inventory_project_item_unique')]

    @property
    def balance(self):
        return self.records.filter(voided_at__isnull=True).aggregate(total=Sum(stock_delta_expression()))['total'] or 0

    def get_absolute_url(self):
        return reverse('inventory:history', args=[self.project_id, self.item_id])


class StockRecord(models.Model):
    class Operation(models.TextChoices):
        OPENING = 'opening', 'Existencia inicial'
        RECEIPT = 'receipt', 'Entrada'
        DELIVERY = 'delivery', 'Entrega directa'

    position = models.ForeignKey(StockPosition, on_delete=models.PROTECT, related_name='records')
    operation = models.CharField(max_length=16, choices=Operation.choices)
    quantity = models.BigIntegerField('cantidad')
    occurred_on = models.DateField('fecha del hecho')
    observation = models.TextField('observación', blank=True)
    worker_full_name = models.TextField('nombre completo del trabajador', blank=True)
    recorded_by = models.TextField('registrado por', default='Prevencionista', editable=False)
    created_at = models.DateTimeField('fecha de registro', auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)
    replaces = models.OneToOneField('self', on_delete=models.PROTECT, null=True, blank=True, related_name='replacement')
    submission_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [
            models.CheckConstraint(
                condition=(Q(operation='opening', quantity__gte=0) |
                           Q(operation__in=['receipt', 'delivery'], quantity__gt=0)),
                name='inventory_valid_operation_quantity',
            ),
            models.UniqueConstraint(fields=['position'], condition=Q(operation='opening', voided_at__isnull=True),
                                    name='inventory_one_valid_opening'),
            models.CheckConstraint(
                condition=(Q(voided_at__isnull=True, void_reason='') |
                           (Q(voided_at__isnull=False) & ~Q(void_reason=''))),
                name='inventory_void_requires_reason',
            ),
            models.CheckConstraint(
                condition=(Q(operation='delivery', worker_full_name__regex=r'\S') |
                           (~Q(operation='delivery') & Q(worker_full_name=''))),
                name='inventory_delivery_requires_worker',
            ),
        ]

    @property
    def delta(self):
        return -self.quantity if self.operation == self.Operation.DELIVERY else self.quantity

    def get_absolute_url(self):
        return self.position.get_absolute_url() + f'#registro-{self.pk}'
