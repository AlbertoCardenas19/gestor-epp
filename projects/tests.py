from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from .models import Project


class ProjectFlowTests(TestCase):
    def test_database_is_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_home_offers_projects_and_catalog(self):
        response = self.client.get('/')
        self.assertContains(response, 'Ir a proyectos')
        self.assertContains(response, 'Ir al inventario')
        self.assertContains(response, reverse('projects:list'))
        self.assertContains(response, reverse('stock:list'))

    def test_empty_list_offers_first_project(self):
        self.assertContains(self.client.get(reverse('projects:list')), 'Crear primer proyecto')

    def test_create_list_and_consult_persisted_project(self):
        response = self.client.post(reverse('projects:create'), {
            'name': 'Obra Los Aromos', 'description': 'Proyecto de prueba.\nSegunda línea.',
        })
        project = Project.objects.get()
        self.assertRedirects(response, project.get_absolute_url())
        # Una nueva sesión debe poder recuperar los datos guardados.
        client = Client()
        self.assertContains(client.get(reverse('projects:list')), project.name)
        detail = client.get(project.get_absolute_url())
        self.assertContains(detail, project.name)
        self.assertContains(detail, 'Entregas')
        project.refresh_from_db()
        self.assertEqual(project.description, 'Proyecto de prueba.\nSegunda línea.')

    def test_description_is_optional(self):
        response = self.client.post(reverse('projects:create'), {'name': 'Obra sin descripción'})
        project = Project.objects.get()
        self.assertEqual(project.description, '')
        self.assertRedirects(response, project.get_absolute_url())
        self.assertContains(self.client.get(project.get_absolute_url()), 'No hay entregas para esta consulta.')

    def test_empty_or_whitespace_name_is_rejected_without_losing_description(self):
        for name in ['', '   ']:
            with self.subTest(name=name):
                response = self.client.post(reverse('projects:create'), {
                    'name': name, 'description': 'Conservar este texto',
                })
                self.assertFormError(response.context['form'], 'name', 'Escribe el nombre del proyecto.')
                self.assertContains(response, 'Conservar este texto')
                self.assertContains(response, 'aria-invalid="true"')
        self.assertFalse(Project.objects.exists())

    def test_names_do_not_have_an_unapproved_uniqueness_rule(self):
        for _ in range(2):
            self.client.post(reverse('projects:create'), {'name': 'Mismo nombre'})
        self.assertEqual(Project.objects.count(), 2)

    def test_missing_project_is_404(self):
        self.assertEqual(self.client.get(reverse('projects:detail', args=[999])).status_code, 404)

    def test_user_text_is_escaped_in_list_and_detail(self):
        project = Project.objects.create(name='<script>alert(1)</script>', description='<img src=x onerror=alert(1)>')
        for url in [reverse('projects:list'), project.get_absolute_url()]:
            response = self.client.get(url)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '&lt;script&gt;')
            self.assertNotContains(response, '<img src=x')

    def test_create_requires_csrf_token(self):
        response = Client(enforce_csrf_checks=True).post(reverse('projects:create'), {'name': 'Sin token'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Project.objects.exists())


class DeliveryTableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from datetime import date
        from django.utils import timezone
        from catalog.models import Item
        from inventory.models import StockPosition, StockRecord
        cls.project = Project.objects.create(name='Obra Norte')
        other = Project.objects.create(name='Obra Sur')
        item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        cls.position = StockPosition.objects.create(project=cls.project, item=item)
        other_position = StockPosition.objects.create(project=other, item=item)
        StockRecord.objects.create(position=cls.position, operation='opening', quantity=100, occurred_on=date.today())
        cls.deliveries = [StockRecord.objects.create(position=cls.position, operation='delivery', quantity=i+1,
                            occurred_on=date.today(), worker_full_name=f'Persona {i:02d}') for i in range(12)]
        cls.original = StockRecord.objects.create(position=cls.position, operation='delivery', quantity=2,
            occurred_on=date.today(), worker_full_name='Original sustituido', voided_at=timezone.now(), void_reason='Error')
        cls.replacement = StockRecord.objects.create(position=cls.position, operation='delivery', quantity=1,
            occurred_on=date.today(), worker_full_name='Reemplazo vigente', replaces=cls.original)
        cls.cancelled = StockRecord.objects.create(position=cls.position, operation='delivery', quantity=3,
            occurred_on=date.today(), worker_full_name='Entrega anulada', voided_at=timezone.now(), void_reason='Duplicado')
        StockRecord.objects.create(position=other_position, operation='delivery', quantity=1,
            occurred_on=date.today(), worker_full_name='Otro proyecto')

    def test_default_only_active_deliveries_with_pagination(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.context['paginator'].count, 13)
        self.assertEqual(len(response.context['deliveries']), 10)
        self.assertNotContains(response, 'Otro proyecto')
        self.assertNotContains(response, 'Original sustituido')
        self.assertNotContains(response, 'Entrega anulada')
        self.assertContains(response, self.replacement.get_absolute_url())
        self.assertContains(response, reverse('inventory:correct', args=[self.project.pk, self.position.item_id, self.replacement.pk]))
        self.assertContains(response, 'Siguiente')

    def test_states_do_not_offer_mutations_for_invalid_records(self):
        for state, record in [('cancelled', self.cancelled), ('replaced', self.original)]:
            response = self.client.get(self.project.get_absolute_url(), {'state': state})
            self.assertEqual(list(response.context['deliveries']), [record])
            self.assertContains(response, record.get_absolute_url())
            for action in ['cancel', 'correct']:
                self.assertNotContains(response, reverse(f'inventory:{action}', args=[self.project.pk, self.position.item_id, record.pk]))
        response = self.client.get(self.project.get_absolute_url(), {'state': 'all', 'per_page': '25'})
        self.assertEqual(response.context['paginator'].count, 15)
        self.assertNotContains(response, 'Otro proyecto')

    def data(self, **parameters):
        response = self.client.get(reverse('projects:delivery-data', args=[self.project.pk]), parameters)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_delivery_sorting_states_and_workers(self):
        result = self.data(**{'state': 'all', 'order[0][column]': 4, 'order[0][dir]': 'asc', 'length': 25})
        self.assertEqual([row['state'] for row in result['data'][:2]], ['Anulado', 'Sustituido'])
        for direction, state, expected in [('asc', 'replaced', 'Original sustituido'), ('desc', 'active', 'Reemplazo vigente')]:
            result = self.data(**{'state': state, 'order[0][column]': 2, 'order[0][dir]': direction})
            self.assertEqual(result['data'][0]['worker'], expected)

    def test_search_order_and_page_parameters_do_not_change_balances(self):
        balance = self.position.balance
        result = self.data(**{'search[value]': 'Persona', 'order[0][column]': 3, 'order[0][dir]': 'asc', 'start': 10})
        self.assertEqual([record['quantity'] for record in result['data']], ['11', '12'])
        result = self.data(**{'order[0][column]': 'invalid', 'state': 'invalid', 'length': '0', 'start': 'bad'})
        self.assertEqual(result['recordsTotal'], 13)
        self.assertEqual(len(result['data']), 10)
        self.assertEqual(self.position.balance, balance)

    def test_all_record_search_and_project_state_scoping(self):
        result = self.data(**{'search[value]': 'Persona 00'})
        self.assertEqual(result['recordsTotal'], 13)
        self.assertEqual(result['recordsFiltered'], 1)
        self.assertEqual(result['data'][0]['worker'], 'Persona 00')
        self.assertEqual(self.data(**{'search[value]': 'Otro proyecto', 'state': 'all'})['data'], [])
        for state, worker in [('cancelled', 'Entrega anulada'), ('replaced', 'Original sustituido')]:
            result = self.data(state=state)
            self.assertEqual(result['recordsTotal'], 1)
            self.assertEqual(result['data'][0]['worker'], worker)
            self.assertNotIn('>Corregir<', result['data'][0]['actions'])
            self.assertNotIn('>Anular<', result['data'][0]['actions'])
        self.assertEqual(self.data(state='all')['recordsTotal'], 15)

    def test_dates_and_quantities_are_ordered_as_database_types(self):
        from datetime import date
        self.deliveries[0].occurred_on = date(2025, 12, 31)
        self.deliveries[0].save()
        self.deliveries[1].occurred_on = date(2026, 2, 1)
        self.deliveries[1].save()
        result = self.data(**{'search[value]': 'Persona', 'order[0][column]': 0, 'order[0][dir]': 'asc'})
        self.assertEqual([row['date'] for row in result['data'][:2]], ['2025-12-31', '2026-02-01'])
        result = self.data(**{'search[value]': '01/02/2026'})
        self.assertEqual([row['worker'] for row in result['data']], ['Persona 01'])
        result = self.data(**{'search[value]': 'Persona', 'order[0][column]': 3, 'order[0][dir]': 'desc'})
        self.assertEqual([row['quantity'] for row in result['data'][:3]], ['12', '11', '10'])

    def test_large_quantity_is_not_rounded_by_json_or_javascript(self):
        from inventory.models import StockRecord
        StockRecord.objects.filter(position=self.position, operation='opening').update(quantity=9223372036854775807)
        self.deliveries[0].quantity = 9007199254740993
        self.deliveries[0].save()
        result = self.data(**{'search[value]': 'Persona 00'})
        self.assertEqual(result['data'][0]['quantity'], '9007199254740993')

    def test_actions_order_parameter_is_ignored_and_endpoint_is_read_only(self):
        before = self.position.balance
        result = self.data(**{'order[0][column]': 5, 'order[0][dir]': 'asc'})
        self.assertEqual(result['data'], self.data()['data'])
        self.assertEqual(self.client.post(reverse('projects:delivery-data', args=[self.project.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('projects:delivery-data', args=[999999])).status_code, 404)
        self.assertEqual(self.position.balance, before)


class ProjectCardsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Project.objects.bulk_create([Project(name=f'Obra {i:02d}', description=f'Descripción {11-i:02d}') for i in range(12)])

    def test_cards_preserve_search_pagination_and_order_parameters(self):
        response = self.client.get(reverse('projects:list'))
        self.assertEqual(response.context['paginator'].count, 12)
        self.assertEqual(len(response.context['projects']), 10)
        self.assertContains(response, 'project-card', count=10)
        self.assertNotContains(response, '<table')
        self.assertNotContains(response, 'Ordenar por')
        for sort, expected in [('name', 'Obra 00'), ('-name', 'Obra 11'), ('description', 'Obra 11'), ('-description', 'Obra 00')]:
            response = self.client.get(reverse('projects:list'), {'sort': sort, 'q': 'Obra', 'page': 1})
            self.assertEqual(response.context['projects'][0].name, expected)
            self.assertContains(response, 'q=Obra')
        response = self.client.get(reverse('projects:list'), {'q': 'Obra 01'})
        self.assertEqual(response.context['paginator'].count, 1)
        self.assertEqual(response.context['projects'][0].name, 'Obra 01')

    def test_no_creation_notification_is_enqueued(self):
        response = self.client.post(reverse('projects:create'), {'name': 'Proyecto nuevo'}, follow=True)
        self.assertNotContains(response, 'Proyecto creado correctamente')
        self.assertFalse(list(response.context['messages']))
