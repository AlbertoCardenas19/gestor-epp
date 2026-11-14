from datetime import datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from catalog.models import Item
from projects.datatables import DataTableView
from .common import (common_item_basics, common_items, common_items_for_page, common_records,
                     receive_common_stock, item_projects, filter_movement_project)
from .availability import available_quantity
from .forms import CorrectionForm, StockForm
from .models import StockRecord
from .services import correct_record
from .views import add_service_error


class CommonItemMixin:
    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(Item, pk=kwargs['item_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(item=self.item, balance=available_quantity(self.item.pk), **kwargs)


class CommonInventoryView(TemplateView):
    template_name = 'inventory/common_list.html'


class CommonInventoryDataView(DataTableView):
    order_columns = ('name', 'type_label', 'total', 'delivered_total', None)
    search_fields = ('name', 'type_label', 'description')
    default_order = ('name', 'pk')

    def get_queryset(self):
        # Numeric ordering needs totals for every candidate to remain globally exact.
        # Other orders can paginate the catalog first and aggregate only that page.
        for index in range(len(self.order_columns)):
            column = self.request.GET.get(f'order[{index}][column]')
            if column is None:
                break
            if column in {'2', '3'} and self.request.GET.get(f'order[{index}][dir]') in {'asc', 'desc'}:
                return common_items()
        return common_item_basics()

    def paginate_records(self, records, start, length):
        return common_items_for_page(super().paginate_records(records, start, length))

    def serialize_record(self, item):
        return {'name': item.name, 'type': item.type_label, 'quantity': str(item.total), 'delivered': str(item.delivered_total), 'item_url': item.get_absolute_url(),
                'actions': render_to_string('inventory/common_actions.html', {
                    'action_id': item.pk, 'action_label': item.name,
                    'detail_url': reverse('stock:history', args=[item.pk]), 'item_url': item.get_absolute_url(),
                    'receipt_url': reverse('stock:receive', args=[item.pk]),
                })}


class CommonHistoryView(CommonItemMixin, TemplateView):
    template_name = 'inventory/common_history.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(project_options=item_projects(self.item),
                                       movement_project=self.request.GET.get('project', ''), **kwargs)


class CommonHistoryDataView(CommonItemMixin, DataTableView):
    order_columns = ('occurred_on', 'operation_label', 'origin_label', 'delta_quantity', 'state_label', None)
    search_fields = ('occurred_on', 'operation_label', 'origin_label', 'state_label', 'worker_full_name', 'observation')
    default_order = ('-occurred_on', '-pk')

    def normalize_search(self, query):
        try:
            return datetime.strptime(query, '%d/%m/%Y').date().isoformat()
        except ValueError:
            return query

    def get_queryset(self):
        return filter_movement_project(common_records(self.item), self.request.GET.get('project', ''))

    def serialize_record(self, record):
        return {'date': record.occurred_on.isoformat(), 'operation': record.operation_label,
                'origin': record.origin_label, 'quantity': str(record.delta_quantity), 'state': record.state_label,
                'actions': render_to_string('projects/row_actions.html', {
                    'action_id': record.pk, 'action_label': f'registro {record.pk}',
                    'detail_url': reverse('stock:record', args=[self.item.pk, record.pk]), 'detail_label': 'Ver registro',
                })}


class CommonRecordMixin(CommonItemMixin):
    def get_record(self):
        return get_object_or_404(common_records(self.item), pk=self.kwargs['record_pk'])

    def get_context_data(self, **kwargs):
        return super().get_context_data(record=self.get_record(), **kwargs)


class CommonRecordView(CommonRecordMixin, TemplateView):
    template_name = 'inventory/common_record.html'


class CommonReceiptView(CommonItemMixin, FormView):
    form_class = StockForm
    template_name = 'inventory/common_form.html'

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'operation': StockRecord.Operation.RECEIPT}

    def form_valid(self, form):
        try:
            record = receive_common_stock(self.item, form.cleaned_data)
        except ValidationError as error:
            add_service_error(form, error)
            return self.form_invalid(form)
        return redirect(record.get_absolute_url())


class CommonCorrectionView(CommonRecordMixin, FormView):
    form_class = CorrectionForm
    template_name = 'inventory/common_form.html'

    def get_record(self):
        return get_object_or_404(common_records(self.item), pk=self.kwargs['record_pk'], position__project__isnull=True,
                                 operation__in=[StockRecord.Operation.OPENING, StockRecord.Operation.RECEIPT])

    def get_form_kwargs(self):
        original = self.get_record()
        kwargs = super().get_form_kwargs()
        kwargs['operation'] = original.operation
        kwargs['initial'].update({field: getattr(original, field) for field in ['quantity', 'occurred_on', 'observation']})
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(is_correction=True, **kwargs)

    def form_valid(self, form):
        original = self.get_record()
        try:
            record = correct_record(None, original.pk, form.cleaned_data)
        except ValidationError as error:
            add_service_error(form, error)
            return self.form_invalid(form)
        return redirect(record.get_absolute_url())


class ItemProjectsDataView(CommonItemMixin, DataTableView):
    order_columns = ('name', 'requested_quantity', 'delivered_quantity', None)
    search_fields = ('name',)
    default_order = ('name', 'pk')

    def get_queryset(self):
        return item_projects(self.item)

    def serialize_record(self, project):
        return {'name': project.name, 'requested': str(project.requested_quantity),
                'delivered': str(project.delivered_quantity),
                'actions': render_to_string('projects/row_actions.html', {
                    'action_id': project.pk, 'action_label': project.name,
                    'detail_url': project.get_absolute_url(), 'detail_label': 'Ver proyecto'})}
