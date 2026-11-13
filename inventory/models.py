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
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name='stock_positions', null=True, blank=True)
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='stock_positions')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'item'], name='inventory_project_item_unique'),
            models.UniqueConstraint(fields=['item'], condition=Q(project__isnull=True), name='inventory_one_common_position'),
        ]

    @property
    def balance(self):
        if self.project_id is None:
            return self.common_balance(self.item_id)
        return self.records.filter(voided_at__isnull=True).aggregate(total=Sum(stock_delta_expression()))['total'] or 0

    @staticmethod
    def common_balance(item_id):
        # One source of truth: existing ledger + new common records, never copied balances.
        return StockRecord.objects.filter(position__item_id=item_id, voided_at__isnull=True).aggregate(
            total=Sum(stock_delta_expression()),
        )['total'] or 0

    def get_absolute_url(self):
        if self.project_id is None:
            return reverse('stock:history', args=[self.item_id])
        return reverse('inventory:history', args=[self.project_id, self.item_id])


class StockRecord(models.Model):
    class Operation(models.TextChoices):
        OPENING = 'opening', 'Existencia inicial'
        RECEIPT = 'receipt', 'Entrada'
        DELIVERY = 'delivery', 'Entrega directa'

    position = models.ForeignKey(StockPosition, on_delete=models.PROTECT, related_name='records')
    stock_request = models.ForeignKey('StockRequest', on_delete=models.PROTECT, null=True, blank=True, related_name='deliveries')
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
            models.CheckConstraint(condition=Q(stock_request__isnull=True) | Q(operation='delivery'), name='inventory_request_only_delivery'),
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
        if self.position.project_id is None:
            return reverse('stock:record', args=[self.position.item_id, self.pk])
        return self.position.get_absolute_url() + f'#registro-{self.pk}'

    @property
    def is_replaced(self):
        return self.voided_at is not None and hasattr(self, 'replacement')

    @property
    def is_cancelled(self):
        return (self.operation == self.Operation.DELIVERY and self.voided_at is not None
                and not self.is_replaced)


class StockRequest(models.Model):
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name='stock_requests')
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='stock_requests')
    quantity = models.BigIntegerField('cantidad solicitada')
    allocated_quantity = models.BigIntegerField(default=0)
    cancelled_quantity = models.BigIntegerField(default=0)
    occurred_on = models.DateField('fecha de solicitud')
    observation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submission_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.CheckConstraint(
            condition=Q(quantity__gt=0, allocated_quantity__gte=0, cancelled_quantity__gte=0)
                      & Q(allocated_quantity__lte=F('quantity') - F('cancelled_quantity')),
            name='inventory_valid_request_quantities',
        )]

    @property
    def delivered_quantity(self):
        if hasattr(self, 'fulfilled_total'):
            return self.fulfilled_total
        return self.deliveries.filter(voided_at__isnull=True).aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def reserved_quantity(self):
        return self.allocated_quantity - self.delivered_quantity

    @property
    def purchase_quantity(self):
        return self.quantity - self.cancelled_quantity - self.allocated_quantity

    @property
    def pending_quantity(self):
        return self.quantity - self.cancelled_quantity - self.delivered_quantity

    @property
    def state_label(self):
        if self.reserved_quantity:
            return 'Reservado'
        if self.purchase_quantity:
            return 'Pendiente de compra' if not self.delivered_quantity else 'Entregado parcialmente'
        if self.cancelled_quantity and not self.delivered_quantity:
            return 'Cancelado'
        return 'Entregado'

    def __str__(self):
        return f'{self.project.name} · {self.item.name} · solicitud {self.pk}'

    def get_absolute_url(self):
        return reverse('requests:detail', args=[self.project_id, self.pk])


class StockRequestEvent(models.Model):
    request = models.ForeignKey(StockRequest, on_delete=models.PROTECT, related_name='events')
    action = models.CharField(max_length=16, choices=[('created', 'Solicitud registrada'), ('reserved', 'Reserva ampliada'), ('reduced', 'Pendiente reducido')])
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    payload = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submission_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['created_at', 'pk']
