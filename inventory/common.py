"""Common stock: read the existing ledger without duplicating historical quantities.

The visible columns combine actual deliveries and pending reservations.
Historical records remain in the same ledger, without fictitious requests.
"""
from django.db import transaction
from django.db.models import BigIntegerField, Case, CharField, Exists, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce

from catalog.models import Item
from .models import StockPosition, StockRecord, StockRequest, stock_delta_expression
from .services import _create_record, _repeated_submission


def common_item_basics():
    """Return searchable/sortable catalog fields without calculating stock totals."""
    return Item.objects.annotate(
        type_label=Case(When(item_type=Item.Type.EPP, then=Value('EPP')),
                        default=Value('Señalética'), output_field=CharField()),
    ).order_by('name', 'pk')


def common_items():
    totals = StockRecord.objects.filter(position__item_id=OuterRef('pk'), voided_at__isnull=True).order_by().values(
        'position__item_id',
    ).annotate(total=Sum(stock_delta_expression())).values('total')
    delivered = StockRecord.objects.filter(position__item_id=OuterRef('pk'), voided_at__isnull=True,
                                            operation=StockRecord.Operation.DELIVERY).order_by().values('position__item_id').annotate(total=Sum('quantity')).values('total')
    requested_deliveries = StockRecord.objects.filter(stock_request__item_id=OuterRef('pk'), voided_at__isnull=True).order_by().values('stock_request__item_id').annotate(total=Sum('quantity')).values('total')
    allocated = StockRequest.objects.filter(item_id=OuterRef('pk')).order_by().values('item_id').annotate(total=Sum('allocated_quantity')).values('total')
    def amount(query):
        return Coalesce(Subquery(query, output_field=BigIntegerField()), Value(0), output_field=BigIntegerField())
    return common_item_basics().annotate(
        physical_total=amount(totals), delivered_total=amount(delivered), allocated_total=amount(allocated),
        fulfilled_total=amount(requested_deliveries),
    ).annotate(reserved_total=F('allocated_total') - F('fulfilled_total')).annotate(
        total=F('physical_total') - F('reserved_total'),
    ).order_by('name', 'pk')


def common_items_for_page(items):
    """Add stock totals after pagination while preserving the requested page order."""
    items = list(items)
    if not items or all(hasattr(item, 'total') for item in items):
        return items
    totals_by_id = {item.pk: item for item in common_items().filter(pk__in=[item.pk for item in items])}
    return [totals_by_id[item.pk] for item in items]



def common_records(item):
    return StockRecord.objects.filter(position__item=item).select_related(
        'position__item', 'position__project', 'stock_request__project', 'replaces__position', 'replacement__position',
    ).annotate(
        delta_quantity=stock_delta_expression(),
        has_replacement=Exists(StockRecord.objects.filter(replaces_id=OuterRef('pk'))),
        operation_label=Case(*[When(operation=key, then=Value(label)) for key, label in StockRecord.Operation.choices],
                             output_field=CharField()),
        state_label=Case(When(voided_at__isnull=True, then=Value('Vigente')),
                         When(replacement__isnull=False, then=Value('Sustituido')),
                         default=Value('Anulado'), output_field=CharField()),
        origin_label=Coalesce('stock_request__project__name', 'position__project__name', Value('Empresa'), output_field=CharField()),
    ).order_by('-occurred_on', '-pk')


@transaction.atomic
def receive_common_stock(item, data):
    # Serializes creation of the common position and retries for this item.
    item = Item.objects.select_for_update().get(pk=item.pk)
    position, _ = StockPosition.objects.get_or_create(project=None, item=item)
    position = StockPosition.objects.select_for_update().get(pk=position.pk)
    repeated = _repeated_submission(position, StockRecord.Operation.RECEIPT, data)
    return repeated or _create_record(position, StockRecord.Operation.RECEIPT, data)


def item_projects(item):
    """Requested and actually delivered are separate aggregates, including legacy history."""
    from projects.models import Project
    from django.db.models import Q
    requests = StockRequest.objects.filter(item=item, project_id=OuterRef('pk')).order_by()
    deliveries = StockRecord.objects.filter(position__item=item, operation='delivery', voided_at__isnull=True).filter(
        Q(stock_request__project_id=OuterRef('pk')) |
        Q(stock_request__isnull=True, position__project_id=OuterRef('pk'))).order_by()
    history = StockRecord.objects.filter(position__item=item).filter(
        Q(stock_request__project_id=OuterRef('pk')) | Q(position__project_id=OuterRef('pk')))
    return Project.objects.annotate(
        has_requests=Exists(requests), has_history=Exists(history),
        requested_quantity=Coalesce(Subquery(requests.values('project_id').annotate(
            total=Sum(F('quantity') - F('cancelled_quantity'))).values('total'), output_field=BigIntegerField()),
            Value(0), output_field=BigIntegerField()),
        delivered_quantity=Coalesce(Subquery(deliveries.annotate(
            project_key=Coalesce('stock_request__project_id', 'position__project_id')).values('project_key').annotate(
            total=Sum('quantity')).values('total'), output_field=BigIntegerField()), Value(0), output_field=BigIntegerField()),
    ).filter(Q(has_requests=True) | Q(has_history=True)).order_by('name', 'pk')


def filter_movement_project(records, project_id):
    from django.db.models import Q
    if not project_id:
        return records
    if project_id == 'company':
        return records.filter(stock_request__isnull=True, position__project__isnull=True)
    if str(project_id).isdigit() and len(str(project_id)) <= 19 and int(project_id) <= 9223372036854775807:
        return records.filter(Q(stock_request__project_id=project_id) |
                              Q(stock_request__isnull=True, position__project_id=project_id))
    return records.none()
