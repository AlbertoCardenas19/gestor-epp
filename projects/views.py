from django.db.models import Case, CharField, Exists, OuterRef, Value, When
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, ListView, TemplateView

from inventory.models import StockRecord

from .forms import ProjectForm
from .models import Project
from .tables import TableViewMixin


class HomeView(TemplateView):
    template_name = 'projects/home.html'


class ProjectListView(TableViewMixin, ListView):
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
    table_columns = (('Nombre', 'name', '-name'), ('Descripción', 'description', '-description'))

    def get_queryset(self):
        return self.filter_table(super().get_queryset())


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'


class ProjectDetailView(TableViewMixin, ListView):
    model = StockRecord
    template_name = 'projects/detail.html'
    context_object_name = 'deliveries'
    search_fields = ('position__item__name', 'worker_full_name', 'observation')
    default_sort = 'newest'
    sort_options = (
        ('newest', 'Fecha: más recientes', ('-occurred_on', '-pk')),
        ('oldest', 'Fecha: más antiguas', ('occurred_on', 'pk')),
        ('item', 'Elemento: A–Z', ('position__item__name', 'pk')),
        ('-item', 'Elemento: Z–A', ('-position__item__name', '-pk')),
        ('-worker', 'Trabajador: Z–A', ('-worker_full_name', '-pk')),
        ('state', 'Estado: A–Z', ('state_label', 'pk')),
        ('-state', 'Estado: Z–A', ('-state_label', '-pk')),
        ('worker', 'Trabajador: A–Z', ('worker_full_name', 'pk')),
        ('quantity', 'Cantidad: menor a mayor', ('quantity', 'pk')),
        ('-quantity', 'Cantidad: mayor a menor', ('-quantity', '-pk')),
    )

    table_columns = (
        ('Fecha', 'oldest', 'newest'), ('Elemento', 'item', '-item'),
        ('Trabajador', 'worker', '-worker'), ('Cantidad', 'quantity', '-quantity'),
        ('Estado', 'state', '-state'),
    )

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
        return self.filter_table(records)

    def get_context_data(self, **kwargs):
        return super().get_context_data(project=self.project, state=self.delivery_state(), **kwargs)
