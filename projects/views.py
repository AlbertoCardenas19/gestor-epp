from datetime import datetime

from django.db.models import Case, CharField, Exists, F, OuterRef, Value, When, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
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
    default_sort = 'date'

    def get_paginate_by(self, queryset):
        return 6

    sort_options = (
        ('date', 'Más recientes primero', (F('created_on').desc(nulls_last=True), '-pk')),
        ('date_asc', 'Más antiguos primero', (F('created_on').asc(nulls_last=True), 'pk')),
        ('name', 'Nombre: A–Z', ('name', 'pk')),
        ('name_desc', 'Nombre: Z–A', ('-name', '-pk')),
    )

    def get_queryset(self):
        return self.filter_cards(super().get_queryset())


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'


class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'


class ProjectInfoView(DetailView):
    model = Project
    template_name = 'projects/info.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            info_actions=[{'label': 'Editar proyecto', 'url': reverse('projects:update', args=[self.object.pk])}],
            action_key=f'project-{self.object.pk}', action_label=self.object.name, **kwargs,
        )


class DeliveryQuerysetMixin:
    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def delivery_state(self):
        state = self.request.GET.get('state', 'all')
        return state if state in ['active', 'all', 'cancelled', 'replaced'] else 'all'

    def get_queryset(self):
        records = StockRecord.objects.filter(Q(position__project=self.project) | Q(stock_request__project=self.project), operation=StockRecord.Operation.DELIVERY).select_related(
            'position__item', 'position__project', 'stock_request__project',
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

    def delivery_state(self):
        # A stale URL parameter must not leave an invisible filter active in the page.
        return 'all'

    def get_context_data(self, **kwargs):
        return super().get_context_data(project=self.project, **kwargs)


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
