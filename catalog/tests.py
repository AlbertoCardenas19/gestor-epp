from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.urls import reverse

from projects.models import Project

from .models import Item


class CatalogFlowTests(TestCase):
    def test_database_is_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_empty_catalog_offers_first_item(self):
        self.assertContains(self.client.get(reverse('catalog:list')), 'Crear primer elemento')

    def test_create_list_and_consult_each_type(self):
        for item_type, name, label in [
            (Item.Type.EPP, 'Casco de seguridad', 'EPP'),
            (Item.Type.SIGNAGE, 'Salida de emergencia', 'Señalética'),
        ]:
            with self.subTest(item_type=item_type):
                response = self.client.post(reverse('catalog:create'), {
                    'name': name, 'item_type': item_type, 'description': 'Primera línea.\nSegunda línea.',
                })
                item = Item.objects.get(name=name)
                self.assertRedirects(response, item.get_absolute_url())
                client = Client()
                self.assertContains(client.get(reverse('catalog:list')), name)
                detail = client.get(item.get_absolute_url())
                self.assertContains(detail, name)
                self.assertContains(detail, label)
                self.assertContains(detail, 'Primera línea.<br>Segunda línea.', html=True)
                item.refresh_from_db()
                self.assertEqual(item.item_type, item_type)

    def test_description_is_optional(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Guantes', 'item_type': Item.Type.EPP})
        item = Item.objects.get()
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(item.description, '')
        self.assertContains(self.client.get(item.get_absolute_url()), 'Este elemento aún no tiene descripción.')

    def test_empty_and_whitespace_name_are_rejected_without_losing_other_fields(self):
        for name in ['', '   ']:
            with self.subTest(name=name):
                response = self.client.post(reverse('catalog:create'), {
                    'name': name, 'item_type': Item.Type.SIGNAGE, 'description': 'Conservar texto',
                })
                self.assertFormError(response.context['form'], 'name', 'Escribe el nombre del elemento.')
                self.assertContains(response, 'Conservar texto')
                self.assertContains(response, 'value="signage" selected')
                self.assertContains(response, 'aria-invalid="true"')
        self.assertFalse(Item.objects.exists())

    def test_type_is_required_and_has_no_default(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Elemento sin tipo'})
        self.assertFormError(response.context['form'], 'item_type', 'Selecciona el tipo de elemento.')
        self.assertContains(response, 'Elemento sin tipo')
        self.assertFalse(Item.objects.exists())

    def test_unknown_type_is_rejected(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Elemento', 'item_type': 'otro'})
        self.assertFormError(response.context['form'], 'item_type', 'Selecciona EPP o Señalética.')
        self.assertFalse(Item.objects.exists())

    def test_database_also_rejects_unknown_type(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Item.objects.create(name='Tipo inválido', item_type='otro')
        self.assertFalse(Item.objects.exists())

    def test_catalog_is_shared_when_navigating_between_projects(self):
        item = Item.objects.create(name='Casco común', item_type=Item.Type.EPP)
        for name in ['Proyecto norte', 'Proyecto sur']:
            project = Project.objects.create(name=name)
            self.assertEqual(self.client.get(project.get_absolute_url()).status_code, 200)
            self.assertContains(self.client.get(reverse('catalog:list')), item.name)
        self.assertEqual(Item.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 2)

    def test_item_not_found_returns_404(self):
        self.assertEqual(self.client.get(reverse('catalog:detail', args=[999])).status_code, 404)

    def test_user_text_is_escaped(self):
        item = Item.objects.create(name='<script>alert(1)</script>', item_type=Item.Type.EPP,
                                   description='<img src=x onerror=alert(1)>')
        for url in [reverse('catalog:list'), item.get_absolute_url()]:
            response = self.client.get(url)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '&lt;script&gt;')
            self.assertNotContains(response, '<img src=x')

    def test_create_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse('catalog:create'), {
            'name': 'Sin token', 'item_type': Item.Type.EPP,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Item.objects.exists())

    def test_navigation_marks_current_section(self):
        for namespace, label in [('catalog', 'Catálogo'), ('projects', 'Proyectos')]:
            response = self.client.get(reverse(f'{namespace}:list'))
            self.assertContains(response, f'aria-current="page" href="{reverse(f"{namespace}:list")}">{label}</a>')
            self.assertEqual(response.content.count(b'aria-current="page"'), 1)


class CatalogTableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Item.objects.bulk_create([Item(name=f'Casco {i:02d}', item_type=Item.Type.EPP) for i in range(12)])
        Item.objects.create(name='Salida', item_type=Item.Type.SIGNAGE, description='Evacuación')

    def data(self, **parameters):
        response = self.client.get(reverse('catalog:data'), parameters)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_pagination_and_search_by_name_type_and_description(self):
        result = self.data(draw=1)
        self.assertEqual(result['draw'], 1)
        self.assertEqual(result['recordsTotal'], 13)
        self.assertEqual(len(result['data']), 10)
        result = self.data(**{'search[value]': 'Casco', 'order[0][column]': 0, 'order[0][dir]': 'desc', 'start': 10})
        self.assertEqual([item['name'] for item in result['data']], ['Casco 01', 'Casco 00'])
        self.assertEqual(result['recordsFiltered'], 12)
        for query in ['Señalética', 'Evacuación', 'Salida']:
            result = self.data(**{'search[value]': query})
            self.assertEqual([item['name'] for item in result['data']], ['Salida'])
        result = self.data(**{'search[value]': 'Salida'})
        self.assertEqual(result['recordsFiltered'], 1)

    def test_invalid_parameters_are_bounded_and_actions_are_not_searched_or_ordered(self):
        result = self.data(**{'draw': '<script>', 'length': -1, 'start': -1, 'order[0][column]': 3,
                              'order[0][dir]': 'desc', 'columns[0][data]': 'untrusted__field'})
        self.assertEqual(result['draw'], 0)
        self.assertEqual(len(result['data']), 10)
        self.assertEqual(result['data'][0]['name'], 'Casco 00')
        for query in ['No existe', 'Ver elemento', '.*']:
            result = self.data(**{'search[value]': query, 'search[regex]': 'true'})
            self.assertEqual(result['recordsFiltered'], 0)
            self.assertEqual(result['data'], [])

    def test_descending_description_and_bootstrap_integration(self):
        result = self.data(**{'order[0][column]': 2, 'order[0][dir]': 'desc'})
        self.assertEqual(result['data'][0]['name'], 'Salida')
        self.assertIn('data-coreui-toggle="dropdown"', result['data'][0]['actions'])
        response = self.client.get(reverse('catalog:list'))
        for asset in ['dataTables.min.js', 'dataTables.bootstrap5.min.js', 'dataTables.bootstrap5.min.css',
                      'jquery.min.js', 'coreui.bundle.min.js']:
            self.assertContains(response, asset, count=1)
        self.assertNotContains(response, 'data-live-cards')
        self.assertNotContains(response, 'popovertarget')

    def test_each_data_column_sorts_both_ways(self):
        for column, key in [(0, 'name'), (1, 'type'), (2, 'description')]:
            for direction in ['asc', 'desc']:
                result = self.data(**{'length': 25, 'order[0][column]': column, 'order[0][dir]': direction})
                values = [item[key] for item in result['data']]
                # Empty descriptions are displayed as fallback text, so test the named field ordering separately.
                if column != 2:
                    self.assertEqual(values, sorted(values, reverse=direction == 'desc'))
                else:
                    self.assertEqual(result['data'][-1 if direction == 'asc' else 0]['name'], 'Salida')

    def test_empty_one_row_and_read_only_endpoint(self):
        Item.objects.all().delete()
        self.assertEqual(self.data()['data'], [])
        Item.objects.create(name='Único elemento', item_type=Item.Type.EPP)
        result = self.data()
        self.assertEqual(result['recordsTotal'], 1)
        self.assertEqual(result['recordsFiltered'], 1)
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(self.client.post(reverse('catalog:data'), {}).status_code, 405)
        self.assertEqual(Item.objects.count(), 1)
