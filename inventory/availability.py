"""Availability accounting. All stock writes lock Item rows before other rows."""
from django.core.exceptions import ValidationError
from django.db.models import Sum

from catalog.models import Item
from .models import StockPosition, StockRecord, StockRequest


def lock_items(*item_ids):
    return list(Item.objects.select_for_update().filter(pk__in=sorted(set(item_ids))).order_by('pk'))


def reserved_quantity(item_id):
    allocated = StockRequest.objects.filter(item_id=item_id).aggregate(total=Sum('allocated_quantity'))['total'] or 0
    delivered = StockRecord.objects.filter(stock_request__item_id=item_id, voided_at__isnull=True).aggregate(total=Sum('quantity'))['total'] or 0
    return allocated - delivered


def available_quantity(item_id):
    return StockPosition.common_balance(item_id) - reserved_quantity(item_id)


def ensure_available(*item_ids):
    if any(available_quantity(item_id) < 0 for item_id in set(item_ids)):
        raise ValidationError({'quantity': 'La operación supera las existencias disponibles. No se aplicó ningún cambio.'})
