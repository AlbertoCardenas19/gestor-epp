from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView

from catalog.models import Item
from projects.models import Project

from .forms import CorrectionForm, DeliveryCorrectionForm, DeliveryForm, StockForm
from .models import StockPosition, StockRecord, stock_delta_expression
from .services import correct_record, deliver_stock, open_stock, receive_stock


class ProjectMixin:
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(project=self.project, **kwargs)


class ProjectItemMixin(ProjectMixin):
    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(Item, pk=kwargs['item_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(item=self.item, **kwargs)


class InventoryListView(ProjectMixin, TemplateView):
    template_name = 'inventory/list.html'

    def get_context_data(self, **kwargs):
        positions = {
            position.item_id: position
            for position in StockPosition.objects.filter(project=self.project).annotate(
                total=Sum(stock_delta_expression('records__'), filter=Q(records__voided_at__isnull=True)),
            )
        }
        rows = [{'item': item, 'position': positions.get(item.pk)} for item in Item.objects.all()]
        return super().get_context_data(rows=rows, **kwargs)


class HistoryView(ProjectItemMixin, TemplateView):
    template_name = 'inventory/history.html'

    def get_context_data(self, **kwargs):
        position = StockPosition.objects.filter(project=self.project, item=self.item).first()
        records = list(position.records.select_related('position', 'replaces__position', 'replacement__position')) if position else []
        balance = sum(record.delta for record in records if record.voided_at is None)
        return super().get_context_data(position=position, records=records, balance=balance, **kwargs)


class RecordCreateView(ProjectItemMixin, FormView):
    template_name = 'inventory/form.html'
    form_class = StockForm
    operation = StockRecord.Operation.OPENING

    def get_form_class(self):
        return DeliveryForm if self.operation == StockRecord.Operation.DELIVERY else StockForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'operation': self.operation}

    def get_context_data(self, **kwargs):
        position = StockPosition.objects.filter(project=self.project, item=self.item).first()
        is_opening = self.operation == StockRecord.Operation.OPENING
        return super().get_context_data(
            position=position, is_opening=is_opening, is_delivery=self.operation == StockRecord.Operation.DELIVERY,
            can_record=(position is None if is_opening else position is not None), **kwargs,
        )

    def form_valid(self, form):
        service = {
            StockRecord.Operation.OPENING: open_stock,
            StockRecord.Operation.RECEIPT: receive_stock,
            StockRecord.Operation.DELIVERY: deliver_stock,
        }[self.operation]
        try:
            record = service(self.project, self.item, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        messages.success(self.request, 'Registro guardado correctamente.')
        return redirect(record.position.get_absolute_url() + f'#registro-{record.pk}')


class CorrectionView(ProjectItemMixin, FormView):
    template_name = 'inventory/correction.html'
    form_class = CorrectionForm

    def get_original(self):
        return get_object_or_404(StockRecord, pk=self.kwargs['record_pk'],
                                 position__project=self.project, position__item=self.item)

    def get_form_class(self):
        return DeliveryCorrectionForm if self.get_original().operation == StockRecord.Operation.DELIVERY else CorrectionForm

    def get_form_kwargs(self):
        original = self.get_original()
        kwargs = super().get_form_kwargs()
        kwargs['operation'] = original.operation
        kwargs['initial'].update({key: getattr(original, key) for key in ['quantity', 'occurred_on', 'observation']})
        if original.operation == StockRecord.Operation.DELIVERY:
            kwargs['initial'].update(destination_project=self.project.pk, destination_item=self.item.pk,
                                     worker_full_name=original.worker_full_name)
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(original=self.get_original(), **kwargs)

    def form_valid(self, form):
        original = self.get_original()
        try:
            record = correct_record(self.project, original.pk, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        messages.success(self.request, 'Corrección guardada. El original se conserva sustituido en el historial.')
        return redirect(record.get_absolute_url())
