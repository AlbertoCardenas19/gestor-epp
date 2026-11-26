"""Factura y libro de inventario se actualizan dentro de la misma transacción."""
from collections import Counter
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.availability import ensure_available, lock_items
from inventory.common import receive_common_stock
from inventory.models import StockRecord
from inventory.services import _create_record

from .models import Allocation, Invoice, InvoiceEvent, InvoiceLine, ReferencePrice, Supplier

HEADER = ('supplier', 'number', 'issued_on', 'due_on', 'total', 'payment_status', 'paid_on', 'purchase_order')
MAX_QUANTITY = 2**63 - 1


@transaction.atomic
def record_reference_price(supplier, item, unit_price):
    Supplier.objects.select_for_update().get(pk=supplier.pk)
    price = ReferencePrice(supplier=supplier, item=item, unit_price=unit_price)
    price.full_clean()
    price.save()
    return price


def validate_lines(lines):
    if not lines:
        raise ValidationError('Agrega al menos una línea a la factura.')
    for line in lines:
        allocations = line['allocations']
        if any(quantity <= 0 for _, quantity in allocations) or sum(q for _, q in allocations) > line['quantity']:
            raise ValidationError('La distribución por proyecto supera la cantidad de la línea o contiene cantidades inválidas.')


def save_lines(invoice, lines):
    for entry in lines:
        item = entry['item']
        if item is None:
            item = entry['new_item'].save()
        line = InvoiceLine(invoice=invoice, item=item, quantity=entry['quantity'], unit_price=entry['unit_price'])
        line.full_clean()
        line.save()
        distribution = Counter()
        for project, quantity in entry['allocations']:
            distribution[project.pk] += quantity
        Allocation.objects.bulk_create([
            Allocation(line=line, project_id=project_id, quantity=quantity)
            for project_id, quantity in distribution.items()
        ])


def snapshot(invoice):
    values = {name: getattr(invoice, name) for name in HEADER if name != 'supplier'}
    values.update(supplier_id=invoice.supplier_id, supplier=str(invoice.supplier), supplier_rut=invoice.supplier.rut,
                  received_at=invoice.received_at, cancelled_at=invoice.cancelled_at)
    values['lines'] = [
        {'item_id': line.item_id, 'item': str(line.item), 'quantity': line.quantity, 'unit_price': line.unit_price,
         'allocations': [{'project_id': row.project_id, 'project': str(row.project), 'quantity': row.quantity}
                         for row in line.allocations.all()]}
        for line in invoice.lines.select_related('item').prefetch_related('allocations__project')
    ]
    return values


def quantities(invoice):
    totals = Counter()
    for item_id, quantity in invoice.lines.values_list('item_id', 'quantity'):
        totals[item_id] += quantity
    if any(total > MAX_QUANTITY for total in totals.values()):
        raise ValidationError('La cantidad total de un elemento excede el máximo permitido.')
    return totals


def reconcile_receipts(invoice, desired, reason=''):
    movements = {
        record.position.item_id: record for record in invoice.movements.filter(voided_at__isnull=True)
        .select_related('position')
    }
    affected = {item_id for item_id in set(movements) | set(desired)
                if item_id not in movements or movements[item_id].quantity != desired.get(item_id, 0)}
    if not affected:
        return
    items = {item.pk: item for item in lock_items(*affected)}
    for item_id in sorted(affected):
        original = movements.get(item_id)
        quantity = desired.get(item_id, 0)
        if original:
            original.voided_at = timezone.now()
            original.void_reason = reason
            original.save(update_fields=['voided_at', 'void_reason'])
        if quantity:
            data = {'quantity': quantity, 'occurred_on': timezone.localdate(invoice.received_at),
                    'observation': '', 'submission_key': uuid4(), 'invoice': invoice}
            if original:
                _create_record(original.position, StockRecord.Operation.RECEIPT, data, replaces=original)
            else:
                receive_common_stock(items[item_id], data)
    try:
        ensure_available(*affected)
    except ValidationError as error:
        raise ValidationError(
            'El ajuste dejaría stock insuficiente para cubrir solicitudes o entregas existentes. '
            'La factura y el inventario se conservaron.'
        ) from error


def save_header(invoice, data):
    for name in HEADER:
        setattr(invoice, name, data[name])
    invoice.full_clean()
    invoice.save()


def check_revision(invoice, revision):
    if revision != invoice.revision:
        raise ValidationError('La factura cambió desde que abriste el formulario. Vuelve al detalle y ábrelo nuevamente.')


@transaction.atomic
def save_invoice(data, lines, *, invoice_id=None, reason='', revision=None):
    validate_lines(lines)
    if invoice_id is None:
        invoice = Invoice()
    else:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        check_revision(invoice, revision)
        reason = reason.strip()
        if invoice.cancelled_at or not reason:
            raise ValidationError('La corrección requiere una factura vigente y un motivo.')
        InvoiceEvent.objects.create(invoice=invoice, action=InvoiceEvent.Action.CORRECT,
                                    reason=reason, before=snapshot(invoice))
        invoice.revision += 1
    # Serialize supplier/number validation with other invoice writes for this supplier.
    Supplier.objects.select_for_update().get(pk=data['supplier'].pk)
    save_header(invoice, data)
    if invoice_id is not None:
        invoice.lines.all().delete()
    save_lines(invoice, lines)
    desired = quantities(invoice)
    if invoice.received_at:
        reconcile_receipts(invoice, desired, reason)
    return invoice


@transaction.atomic
def receive_invoice(invoice_id, revision=None):
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.cancelled_at:
        raise ValidationError('La factura está anulada.')
    if invoice.received_at:
        return invoice
    if revision is not None:
        check_revision(invoice, revision)
    desired = quantities(invoice)
    if not desired:
        raise ValidationError('La factura debe tener al menos una línea para recibirse.')
    invoice.received_at = timezone.now()
    reconcile_receipts(invoice, desired)
    invoice.revision += 1
    invoice.save(update_fields=['received_at', 'revision'])
    return invoice


@transaction.atomic
def cancel_invoice(invoice_id, reason, revision):
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.cancelled_at:
        return invoice
    check_revision(invoice, revision)
    reason = reason.strip()
    if not reason:
        raise ValidationError('Escribe el motivo de la anulación.')
    InvoiceEvent.objects.create(invoice=invoice, action=InvoiceEvent.Action.CANCEL,
                                reason=reason, before=snapshot(invoice))
    if invoice.received_at:
        reconcile_receipts(invoice, {}, reason)
    invoice.cancelled_at = timezone.now()
    invoice.revision += 1
    invoice.save(update_fields=['cancelled_at', 'revision'])
    return invoice


@transaction.atomic
def mark_paid(invoice_id, paid_on, revision):
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    check_revision(invoice, revision)
    if invoice.cancelled_at or invoice.payment_status != Invoice.Payment.PENDING or not paid_on:
        raise ValidationError('Selecciona una fecha de pago para una factura pendiente y vigente.')
    InvoiceEvent.objects.create(invoice=invoice, action=InvoiceEvent.Action.PAYMENT,
                                before=snapshot(invoice))
    invoice.payment_status = Invoice.Payment.PAID
    invoice.paid_on = paid_on
    invoice.revision += 1
    invoice.save(update_fields=['paid_on', 'payment_status', 'revision'])
    return invoice
