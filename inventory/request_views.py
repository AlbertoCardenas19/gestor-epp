from django.core.exceptions import ValidationError
from django.db.models import BigIntegerField, Case, CharField, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from projects.datatables import DataTableView
from .availability import available_quantity
from .forms import DeliveryForm
from .models import StockRecord, StockRequest
from .request_forms import ItemRequestForm, RequestActionForm, RequestEditForm, RequestForm, RequestReductionForm
from .request_services import create_request, deliver_request, edit_request, reduce_request, reserve_more
from .views import ProjectMixin, add_service_error


def request_rows(project):
    delivered = StockRecord.objects.filter(stock_request_id=OuterRef('pk'), voided_at__isnull=True).order_by().values(
        'stock_request_id').annotate(total=Sum('quantity')).values('total')
    return StockRequest.objects.filter(project=project).select_related('project', 'item').annotate(
        fulfilled_total=Coalesce(Subquery(delivered, output_field=BigIntegerField()), Value(0), output_field=BigIntegerField()),
    ).annotate(reserved_total=F('allocated_quantity') - F('fulfilled_total'),
               purchase_total=F('quantity') - F('cancelled_quantity') - F('allocated_quantity')).annotate(
        request_label=Case(When(quantity__gt=F('cancelled_quantity') + F('fulfilled_total'), then=Value('En proceso')),
            When(cancelled_quantity__gt=0, fulfilled_total=0, then=Value('Cancelado')),
            default=Value('Entregado'), output_field=CharField()),
    ).order_by('-created_at', '-pk')


class RequestListView(ProjectMixin, TemplateView):
    template_name = 'inventory/request_list.html'


class RequestDataView(ProjectMixin, DataTableView):
    order_columns = ('occurred_on', 'item__name', 'quantity', 'fulfilled_total', 'purchase_total', 'request_label', None)
    search_fields = ('item__name', 'observation', 'request_label')
    default_order = ('-occurred_on', '-pk')

    def get_queryset(self):
        return request_rows(self.project)

    def serialize_record(self, request):
        return {'date': request.occurred_on.isoformat(), 'item': request.item.name, 'quantity': str(request.quantity),
                'delivered': str(request.delivered_quantity), 'purchase': str(request.purchase_quantity),
                'state': request.state_label, 'pending': request.pending_quantity > 0,
                'item_url': request.item.get_absolute_url(),
                'actions': render_to_string('inventory/request_row_actions.html', {'request_record': request})}


class RequestCreateView(ProjectMixin, FormView):
    form_class = RequestForm
    template_name = 'inventory/request_form.html'

    def get_initial(self):
        return {**super().get_initial(), 'item': self.request.GET.get('item')}

    def get_context_data(self, **kwargs):
        from .selector import selector_context
        context = super().get_context_data(**kwargs)
        form = context['form']
        context.update(selector_context(self.request.GET, form['item'].value()))
        context['is_request_create'] = True
        return context

    def form_valid(self, form):
        try:
            request = create_request(self.project, form.cleaned_data['item'], form.cleaned_data)
        except ValidationError as error:
            add_service_error(form, error)
            return self.form_invalid(form)
        return redirect(reverse('requests:list', args=[request.project_id]))


class ItemRequestCreateView(FormView):
    form_class = ItemRequestForm
    template_name = 'inventory/request_form.html'

    def dispatch(self, request, *args, **kwargs):
        from catalog.models import Item
        self.item = get_object_or_404(Item, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {**super().get_initial(), 'item': self.item.pk}

    def get_context_data(self, **kwargs):
        return super().get_context_data(item=self.item, from_item=True, **kwargs)

    def form_valid(self, form):
        if form.cleaned_data['item'].pk != self.item.pk:
            form.add_error('item', 'El elemento seleccionado no coincide con esta ficha.')
            return self.form_invalid(form)
        try:
            request = create_request(form.cleaned_data['project'], self.item, form.cleaned_data)
        except ValidationError as error:
            add_service_error(form, error)
            return self.form_invalid(form)
        return redirect(reverse('requests:list', args=[request.project_id]))


class RequestMixin(ProjectMixin):
    def get_request(self):
        if not hasattr(self, '_stock_request'):
            self._stock_request = get_object_or_404(request_rows(self.project), pk=self.kwargs['request_pk'])
        return self._stock_request

    def get_context_data(self, **kwargs):
        request = self.get_request()
        return super().get_context_data(request_record=request, available=available_quantity(request.item_id), **kwargs)


class RequestDetailView(RequestMixin, TemplateView):
    template_name = 'inventory/request_history_modal.html'

    def get_context_data(self, **kwargs):
        request = self.get_request()
        return super().get_context_data(
            events=request.events.all(),
            deliveries=request.deliveries.select_related('position', 'replacement').all(),
            **kwargs,
        )

    def get(self, request, *args, **kwargs):
        self.get_request()
        if request.GET.get('modal') == '1':
            return super().get(request, *args, **kwargs)
        return redirect(reverse('requests:list', args=[self.project.pk]))


class RequestActionView(RequestMixin, FormView):
    template_name = 'inventory/request_form.html'
    form_class = RequestActionForm
    action = 'reserve'

    def get_form_class(self):
        return {'reserve': RequestActionForm, 'reduce': RequestReductionForm, 'deliver': DeliveryForm,
                'edit': RequestEditForm}[self.action]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        request = self.get_request()
        if self.action == 'deliver':
            kwargs['operation'] = StockRecord.Operation.DELIVERY
            kwargs['initial'].update(quantity=request.reserved_quantity, occurred_on=timezone.localdate())
        elif self.action in ('reduce', 'edit'):
            kwargs['initial']['pending_quantity'] = request.pending_quantity
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(action=self.action, modal=self.request.GET.get('modal') == '1', **kwargs)

    def get_template_names(self):
        if self.request.GET.get('modal') == '1':
            return ['inventory/request_action_modal.html']
        return [self.template_name]

    def form_valid(self, form):
        request = self.get_request()
        try:
            {'reserve': reserve_more, 'reduce': reduce_request, 'deliver': deliver_request,
             'edit': edit_request}[self.action](request, form.cleaned_data)
        except ValidationError as error:
            add_service_error(form, error)
            return self.form_invalid(form)
        if self.request.GET.get('modal') == '1':
            return JsonResponse({'ok': True})
        return redirect(reverse('requests:list', args=[self.project.pk]))
