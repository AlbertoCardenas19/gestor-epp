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
        self.assertContains(response, 'Ir al catálogo')
        self.assertContains(response, reverse('projects:list'))
        self.assertContains(response, reverse('catalog:list'))

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

    def test_delivery_header_order_and_sorting_states_and_workers(self):
        response = self.client.get(self.project.get_absolute_url(), {'state': 'all', 'sort': 'state', 'per_page': 25})
        records = list(response.context['deliveries'])
        self.assertEqual(records[0].pk, self.cancelled.pk)
        self.assertEqual(records[1].pk, self.original.pk)
        self.assertEqual(response.context['columns'][0]['label'], 'Fecha')
        for sort, expected in [('worker', 'Original sustituido'), ('-worker', 'Reemplazo vigente')]:
            response = self.client.get(self.project.get_absolute_url(), {'state': 'replaced' if sort == 'worker' else 'active', 'sort': sort})
            self.assertEqual(response.context['deliveries'][0].worker_full_name, expected)

    def test_search_order_and_page_parameters_do_not_change_balances(self):
        balance = self.position.balance
        response = self.client.get(self.project.get_absolute_url(), {'q': 'Persona', 'sort': 'quantity', 'page': 2})
        self.assertEqual([record.quantity for record in response.context['deliveries']], [11, 12])
        response = self.client.get(self.project.get_absolute_url(), {'sort': 'invalid', 'state': 'invalid', 'per_page': '0', 'page': 'bad'})
        self.assertEqual(response.context['sort'], 'newest')
        self.assertEqual(response.context['state'], 'active')
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(response.context['paginator'].per_page, 10)
        self.assertEqual(self.position.balance, balance)


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
