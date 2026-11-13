"""Project requests, partial reservation and actual deliveries; atomic and idempotent."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .availability import available_quantity, ensure_available, lock_items
from .models import StockPosition, StockRecord, StockRequest, StockRequestEvent


def _snapshot(request):
    return {'allocated': request.allocated_quantity, 'cancelled': request.cancelled_quantity}


def _repeat_event(request, action, data, payload):
    event = StockRequestEvent.objects.filter(submission_key=data['submission_key']).first()
    if event:
        if event.request_id != request.pk or event.action != action or event.payload != payload:
            raise ValidationError('Este formulario ya se utilizó con otros datos. Vuelve a abrirlo.')
        return True
    return False


@transaction.atomic
def create_request(project, item, data):
    lock_items(item.pk)
    existing = StockRequest.objects.filter(submission_key=data['submission_key']).first()
    if existing:
        if (existing.project_id, existing.item_id, existing.quantity, existing.observation) != (
                project.pk, item.pk, data['quantity'], data['observation']):
            raise ValidationError('Este formulario ya se utilizó con otros datos. Vuelve a abrirlo.')
        return existing
    request = StockRequest(project=project, item=item, quantity=data['quantity'], occurred_on=timezone.localdate(),
                           observation=data['observation'], submission_key=data['submission_key'])
    request.allocated_quantity = min(request.quantity, max(0, available_quantity(item.pk)))
    request.full_clean()
    request.save()
    StockRequestEvent.objects.create(request=request, action='created', after=_snapshot(request))
    ensure_available(item.pk)
    return request


@transaction.atomic
def reserve_more(request, data):
    lock_items(request.item_id)
    request = StockRequest.objects.select_for_update().get(pk=request.pk)
    if _repeat_event(request, 'reserved', data, {}):
        return request
    amount = min(request.purchase_quantity, max(0, available_quantity(request.item_id)))
    if amount <= 0:
        raise ValidationError('No hay unidades disponibles para ampliar esta reserva.')
    before = _snapshot(request)
    request.allocated_quantity += amount
    request.full_clean()
    request.save(update_fields=['allocated_quantity'])
    StockRequestEvent.objects.create(request=request, action='reserved', before=before, after=_snapshot(request),
                                    submission_key=data['submission_key'])
    ensure_available(request.item_id)
    return request


@transaction.atomic
def reduce_request(request, data):
    lock_items(request.item_id)
    request = StockRequest.objects.select_for_update().get(pk=request.pk)
    target = data['pending_quantity']
    reason = data.get('reason', '').strip()
    payload = {'pending_quantity': target, 'reason': reason}
    if _repeat_event(request, 'reduced', data, payload):
        return request
    if not reason:
        raise ValidationError({'reason': 'Escribe el motivo de la reducción o cancelación.'})
    if target < 0 or target >= request.pending_quantity:
        raise ValidationError({'pending_quantity': 'Indica una cantidad menor que el pendiente actual, incluido cero para cancelarlo.'})
    before = _snapshot(request)
    delivered = request.delivered_quantity
    request.cancelled_quantity = request.quantity - delivered - target
    # User rule: preserve reservations; reduce the uncovered purchase need first.
    request.allocated_quantity = delivered + min(request.reserved_quantity, target)
    request.full_clean()
    request.save(update_fields=['allocated_quantity', 'cancelled_quantity'])
    StockRequestEvent.objects.create(request=request, action='reduced', before=before, after=_snapshot(request),
                                    payload=payload, reason=reason, submission_key=data['submission_key'])
    ensure_available(request.item_id)
    return request


@transaction.atomic
def deliver_request(request, data):
    from .services import _create_record, _repeated_submission
    lock_items(request.item_id)
    request = StockRequest.objects.select_for_update().get(pk=request.pk)
    position, _ = StockPosition.objects.get_or_create(item=request.item, project=None)
    position = StockPosition.objects.select_for_update().get(pk=position.pk)
    values = {**data, 'stock_request': request}
    repeated = _repeated_submission(position, StockRecord.Operation.DELIVERY, values)
    if repeated:
        return repeated
    if data['quantity'] <= 0 or data['quantity'] > request.reserved_quantity:
        raise ValidationError({'quantity': 'La cantidad supera las unidades reservadas pendientes de entrega.'})
    record = _create_record(position, StockRecord.Operation.DELIVERY, values)
    ensure_available(request.item_id)
    return record


@transaction.atomic
def correct_request_delivery(project, original, data):
    from .services import _create_record, _repeated_submission
    destination = data['destination_request']
    lock_items(original.position.item_id, destination.item_id)
    requests = {request.pk: request for request in StockRequest.objects.select_for_update().filter(
        pk__in=[original.stock_request_id, destination.pk]).order_by('pk')}
    destination = requests[destination.pk]
    position, _ = StockPosition.objects.get_or_create(project=None, item_id=destination.item_id)
    position = StockPosition.objects.select_for_update().get(pk=position.pk)
    original.refresh_from_db()
    values = {**data, 'stock_request': destination}
    repeated = _repeated_submission(position, StockRecord.Operation.DELIVERY, values, replaces=original)
    if repeated:
        return repeated
    if original.voided_at is not None:
        raise ValidationError('Este registro ya no está vigente. Abre su reemplazo o su historial.')
    reason = data.get('reason', '').strip()
    if not reason:
        raise ValidationError({'reason': 'Escribe el motivo de la corrección.'})
    original.voided_at = timezone.now()
    original.void_reason = reason
    original.save(update_fields=['voided_at', 'void_reason'])
    if data['quantity'] <= 0 or data['quantity'] > destination.reserved_quantity:
        raise ValidationError({'quantity': 'La solicitud de destino no tiene cantidad reservada pendiente suficiente.'})
    result = _create_record(position, StockRecord.Operation.DELIVERY, values, replaces=original)
    ensure_available(original.position.item_id, destination.item_id)
    return result
