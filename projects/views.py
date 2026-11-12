from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, ListView, TemplateView

from inventory.models import StockRecord

from .forms import ProjectForm
from .models import Project
from .tables import TableViewMixin


class HomeView(TemplateView):
    template_name = 'projects/home.html'


class ProjectListView(ListView):
    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'


class ProjectCreateView(SuccessMessageMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'
    success_message = 'Proyecto creado correctamente.'


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
        ('worker', 'Trabajador: A–Z', ('worker_full_name', 'pk')),
        ('quantity', 'Cantidad: menor a mayor', ('quantity', 'pk')),
        ('-quantity', 'Cantidad: mayor a menor', ('-quantity', '-pk')),
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
