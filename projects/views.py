from datetime import datetime

from django.db.models import Case, CharField, Exists, OuterRef, Value, When
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, ListView, TemplateView
from django.template.loader import render_to_string

from inventory.models import StockRecord

from .forms import ProjectForm
from .models import Project
from .cards import CardsViewMixin
from .datatables import DataTableView


class HomeView(TemplateView):
    template_name = 'projects/home.html'


class ProjectListView(CardsViewMixin, ListView):
    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'
    search_fields = ('name', 'description')
    default_sort = 'name'
    sort_options = (
        ('name', 'Nombre: A–Z', ('name', 'pk')),
        ('-name', 'Nombre: Z–A', ('-name', '-pk')),
        ('description', 'Descripción: A–Z', ('description', 'pk')),
        ('-description', 'Descripción: Z–A', ('-description', '-pk')),
    )

    def get_queryset(self):
        return self.filter_cards(super().get_queryset())


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'


class DeliveryQuerysetMixin:
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def delivery_state(self):
        state = self.request.GET.get('state', 'active')
        return state if state in ['active', 'all', 'cancelled', 'replaced'] else 'active'

    def get_queryset(self):
        records = StockRecord.objects.filter(position__project=self.project, operation=StockRecord.Operation.DELIVERY).select_related(
            'position__item', 'position__project',
        ).annotate(has_replacement=Exists(StockRecord.objects.filter(replaces_id=OuterRef('pk'))))
        records = records.annotate(state_label=Case(
            When(voided_at__isnull=True, then=Value('Vigente')),
            When(has_replacement=True, then=Value('Sustituido')),
            default=Value('Anulado'), output_field=CharField(),
        ))
        state = self.delivery_state()
        if state == 'active':
            records = records.filter(voided_at__isnull=True)
        elif state == 'cancelled':
            records = records.filter(voided_at__isnull=False, has_replacement=False)
        elif state == 'replaced':
            records = records.filter(voided_at__isnull=False, has_replacement=True)
        return records.order_by('-occurred_on', '-pk')


class ProjectDetailView(DeliveryQuerysetMixin, ListView):
    template_name = 'projects/detail.html'
    context_object_name = 'deliveries'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        return super().get_context_data(project=self.project, state=self.delivery_state(), **kwargs)


class DeliveryDataView(DeliveryQuerysetMixin, DataTableView):
    order_columns = ('occurred_on', 'position__item__name', 'worker_full_name', 'quantity', 'state_label', None)
    search_fields = ('occurred_on', 'position__item__name', 'worker_full_name', 'quantity', 'state_label', 'observation')
    default_order = ('-occurred_on', '-pk')

    def normalize_search(self, query):
        try:
            return datetime.strptime(query, '%d/%m/%Y').date().isoformat()
        except ValueError:
            return query

    def serialize_record(self, record):
        return {
            'date': record.occurred_on.isoformat(), 'item': record.position.item.name,
            'worker': record.worker_full_name, 'quantity': str(record.quantity), 'state': record.state_label,
            'actions': render_to_string('projects/row_actions.html', {
                'project': self.project, 'record': record, 'action_id': record.pk,
                'action_label': record.worker_full_name, 'detail_url': record.get_absolute_url(), 'detail_label': 'Ver historial',
            }),
        }
