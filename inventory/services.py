"""Operaciones de inventario; las escrituras se serializan por posición.

El historial es la fuente del saldo. Corregir anula y reemplaza en una única
transacción; nunca se actualiza una cantidad histórica ni un saldo almacenado.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from projects.models import Project

from .models import StockPosition, StockRecord


def _repeated_submission(position, operation, data, replaces=None):
    existing = StockRecord.objects.filter(submission_key=data['submission_key']).first()
    if existing is None:
        return None
    matches = (
        existing.position_id == position.pk and existing.operation == operation
        and existing.quantity == data['quantity'] and existing.occurred_on == data['occurred_on']
        and existing.observation == data['observation']
        and existing.worker_full_name == data.get('worker_full_name', '').strip()
        and existing.replaces_id == (replaces.pk if replaces else None)
        and (replaces is None or replaces.void_reason == data.get('reason', '').strip())
    )
    if not matches:
        raise ValidationError('Este formulario ya se utilizó. Vuelve a abrir el registro e inténtalo otra vez.')
    return existing


def _create_record(position, operation, data, replaces=None):
    record = StockRecord(position=position, operation=operation, replaces=replaces,
                         worker_full_name=data.get('worker_full_name', '').strip(),
                         **{key: data[key] for key in ['quantity', 'occurred_on', 'observation', 'submission_key']})
    record.full_clean()
    record.save()
    return record


@transaction.atomic
def open_stock(project, item, data):
    # La posición aún puede no existir: bloquear el proyecto serializa su creación.
    Project.objects.select_for_update().get(pk=project.pk)
    position, _ = StockPosition.objects.get_or_create(project=project, item=item)
    position = StockPosition.objects.select_for_update().get(pk=position.pk)
    repeated = _repeated_submission(position, StockRecord.Operation.OPENING, data)
    if repeated:
        return repeated
    if position.records.exists():
        raise ValidationError('Este elemento ya tiene una apertura. Para cambiarla, corrige el registro existente.')
    return _create_record(position, StockRecord.Operation.OPENING, data)


@transaction.atomic
def receive_stock(project, item, data):
    position = StockPosition.objects.select_for_update().filter(project=project, item=item).first()
    if position is None or not position.records.filter(operation=StockRecord.Operation.OPENING, voided_at__isnull=True).exists():
        raise ValidationError('Registra primero la existencia inicial de este elemento en el proyecto.')
    repeated = _repeated_submission(position, StockRecord.Operation.RECEIPT, data)
    return repeated or _create_record(position, StockRecord.Operation.RECEIPT, data)


@transaction.atomic
def deliver_stock(project, item, data):
    position = StockPosition.objects.select_for_update().filter(project=project, item=item).first()
    if position is None or not position.records.filter(operation=StockRecord.Operation.OPENING, voided_at__isnull=True).exists():
        raise ValidationError('Registra primero la existencia inicial de este elemento en el proyecto.')
    repeated = _repeated_submission(position, StockRecord.Operation.DELIVERY, data)
    if repeated:
        return repeated
    # Validar y guardar dentro del bloqueo; un error posterior revierte la entrega.
    record = _create_record(position, StockRecord.Operation.DELIVERY, data)
    if position.balance < 0:
        raise ValidationError('La cantidad supera el saldo disponible del proyecto. No se registró la entrega.')
    return record


@transaction.atomic
def cancel_delivery(project, record_id, reason):
    record = StockRecord.objects.get(pk=record_id, position__project=project)
    if record.operation != StockRecord.Operation.DELIVERY:
        raise ValidationError('Solo se pueden anular entregas directas.')
    # El mismo bloqueo usado por entregas y correcciones protege el estado y el saldo.
    StockPosition.objects.select_for_update().get(pk=record.position_id)
    record.refresh_from_db()
    reason = reason.strip()
    if not reason:
        raise ValidationError('Escribe el motivo de la anulación.')
    if StockRecord.objects.filter(replaces=record).exists():
        raise ValidationError('Este registro fue sustituido. Solo puedes anular su reemplazo vigente.')
    if record.voided_at is not None:
        return record, False
    record.voided_at = timezone.now()
    record.void_reason = reason
    record.full_clean()
    record.save(update_fields=['voided_at', 'void_reason'])
    # No se crea una entrada: el saldo excluye este descuento una sola vez.
    return record, True


@transaction.atomic
def correct_delivery(project, record_id, data):
    original = StockRecord.objects.get(pk=record_id, position__project=project)
    if original.operation != StockRecord.Operation.DELIVERY:
        raise ValidationError('Este registro no es una entrega directa.')
    destination_project = data.get('destination_project')
    destination_item = data.get('destination_item')
    if destination_project is None or destination_item is None:
        raise ValidationError('Selecciona el proyecto y el elemento correctos.')
    destination = StockPosition.objects.filter(project=destination_project, item=destination_item).first()
    if destination is None:
        raise ValidationError('El destino no tiene apertura. Registra primero su existencia inicial.')

    # Un orden global de bloqueo evita ciclos cuando dos correcciones cruzan posiciones.
    positions = {position.pk: position for position in StockPosition.objects.select_for_update().filter(
        pk__in=[original.position_id, destination.pk],
    ).order_by('pk')}
    source = positions[original.position_id]
    destination = positions[destination.pk]
    original.refresh_from_db()
    repeated = _repeated_submission(destination, StockRecord.Operation.DELIVERY, data, replaces=original)
    if repeated:
        return repeated
    if original.voided_at is not None:
        if original.is_cancelled:
            raise ValidationError('Esta entrega está anulada y no se puede corregir.')
        raise ValidationError('Este registro ya fue corregido. Abre el registro vigente para corregirlo.')
    if not destination.records.filter(operation=StockRecord.Operation.OPENING, voided_at__isnull=True).exists():
        raise ValidationError('El destino no tiene apertura. Registra primero su existencia inicial.')
    reason = data.get('reason', '').strip()
    if not reason:
        raise ValidationError('Escribe el motivo de la corrección.')
    original.voided_at = timezone.now()
    original.void_reason = reason
    original.save(update_fields=['voided_at', 'void_reason'])
    replacement = _create_record(destination, StockRecord.Operation.DELIVERY, data, replaces=original)
    if source.balance < 0 or destination.balance < 0:
        raise ValidationError('La corrección supera el saldo disponible. No se modificó ningún registro ni saldo.')
    return replacement


@transaction.atomic
def correct_record(project, record_id, data):
    original = StockRecord.objects.get(pk=record_id, position__project=project)
    if original.operation == StockRecord.Operation.DELIVERY:
        return correct_delivery(project, record_id, data)
    position = StockPosition.objects.select_for_update().get(pk=original.position_id)
    original.refresh_from_db()
    repeated = _repeated_submission(position, original.operation, data, replaces=original)
    if repeated:
        return repeated
    if original.voided_at is not None:
        raise ValidationError('Este registro ya fue corregido. Abre el registro vigente para corregirlo.')
    reason = data.get('reason', '').strip()
    if not reason:
        raise ValidationError('Escribe el motivo de la corrección.')
    original.voided_at = timezone.now()
    original.void_reason = reason
    original.save(update_fields=['voided_at', 'void_reason'])
    replacement = _create_record(position, original.operation, data, replaces=original)
    if position.balance < 0:
        raise ValidationError('La corrección dejaría un saldo negativo por las entregas registradas. No se aplicó ningún cambio.')
    return replacement
