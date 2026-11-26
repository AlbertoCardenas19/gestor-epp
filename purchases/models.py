from django.core.validators import MinValueValidator
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse


class Supplier(models.Model):
    name = models.CharField('nombre o razón social', max_length=200)
    rut = models.CharField('RUT', max_length=30)
    contact = models.CharField('persona de contacto', max_length=200, blank=True)
    phone = models.CharField('teléfono', max_length=50, blank=True)
    email = models.EmailField('correo electrónico', blank=True)

    class Meta:
        ordering = ['name', 'pk']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('purchases:supplier', args=[self.pk])


class ReferencePrice(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT)
    unit_price = models.PositiveBigIntegerField('precio unitario sin IVA (CLP)')
    recorded_at = models.DateTimeField('registrado el', auto_now_add=True)

    class Meta:
        ordering = ['-pk']
        indexes = [models.Index(fields=['supplier', 'item', '-id'], name='purchase_reference_history')]


class Invoice(models.Model):
    class Payment(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PAID = 'paid', 'Pagada'

    supplier = models.ForeignKey(Supplier, verbose_name='proveedor', on_delete=models.PROTECT)
    number = models.CharField('número de factura', max_length=80)
    issued_on = models.DateField('fecha de emisión')
    due_on = models.DateField('fecha de vencimiento')
    total = models.PositiveBigIntegerField('total con IVA indicado en la factura (CLP)')
    payment_status = models.CharField('estado de pago', choices=Payment.choices, default=Payment.PENDING, max_length=10)
    paid_on = models.DateField('fecha de pago', null=True, blank=True)
    purchase_order = models.CharField('número de orden de compra', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['supplier', 'number'], name='purchase_unique_invoice_number'),
            models.CheckConstraint(condition=(
                models.Q(payment_status='pending', paid_on__isnull=True)
                | models.Q(payment_status='paid', paid_on__isnull=False)
            ), name='purchase_valid_invoice_payment'),
        ]

    def get_absolute_url(self):
        return reverse('purchases:invoice', args=[self.pk])


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='lines', on_delete=models.PROTECT)
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT)
    quantity = models.PositiveBigIntegerField('cantidad', validators=[MinValueValidator(1)])
    unit_price = models.PositiveBigIntegerField('precio unitario sin IVA (CLP)')

    class Meta:
        ordering = ['pk']
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='purchase_positive_line')]

    @property
    def unassigned(self):
        return self.quantity - sum(allocation.quantity for allocation in self.allocations.all())


class Allocation(models.Model):
    line = models.ForeignKey(InvoiceLine, related_name='allocations', on_delete=models.CASCADE)
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT)
    quantity = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(fields=['line', 'project'], name='purchase_unique_line_project'),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='purchase_positive_allocation'),
        ]


class InvoiceEvent(models.Model):
    class Action(models.TextChoices):
        CORRECT = 'correct', 'Corrección'
        CANCEL = 'cancel', 'Anulación'
        PAYMENT = 'payment', 'Cambio de pago'

    invoice = models.ForeignKey(Invoice, related_name='events', on_delete=models.PROTECT)
    action = models.CharField(choices=Action.choices, max_length=10)
    reason = models.TextField(blank=True)
    before = models.JSONField(encoder=DjangoJSONEncoder)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pk']
