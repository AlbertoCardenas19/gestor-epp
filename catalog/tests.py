from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from projects.models import Project

from .models import Category, Item


class CatalogFlowTests(TestCase):
    def test_database_is_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_old_catalog_url_redirects_to_inventory(self):
        self.assertRedirects(self.client.get(reverse('catalog:list')), reverse('stock:list'))
        self.assertContains(self.client.get(reverse('catalog:list'), follow=True), 'Agregar elemento')

    def test_create_list_and_consult_categories(self):
        for name, label in [
            ('Casco de seguridad', 'EPP'),
            ('Salida de emergencia', 'Señaléticas'),
        ]:
            with self.subTest(category=label):
                category = Category.objects.get(name=label)
                response = self.client.post(reverse('catalog:create'), {
                    'name': name, 'categories': [category.pk], 'description': 'Primera línea.\nSegunda línea.',
                })
                item = Item.objects.get(name=name)
                self.assertRedirects(response, item.get_absolute_url())
                client = Client()
                self.assertIn(name, [row['name'] for row in client.get(reverse('stock:data')).json()['data']])
                detail = client.get(item.get_absolute_url())
                self.assertContains(detail, name)
                self.assertContains(detail, label)
                self.assertContains(detail, 'Primera línea.<br>Segunda línea.', html=True)
                item.refresh_from_db()
                self.assertEqual(list(item.categories.all()), [category])

    def test_description_is_optional(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Guantes', 'categories': Category.objects.get(name='EPP').pk})
        item = Item.objects.get()
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(item.description, '')
        self.assertContains(self.client.get(item.get_absolute_url()), 'Este elemento aún no tiene descripción.')

    def test_empty_and_whitespace_name_are_rejected_without_losing_other_fields(self):
        category = Category.objects.get(name='Señaléticas')
        for name in ['', '   ']:
            with self.subTest(name=name):
                response = self.client.post(reverse('catalog:create'), {
                    'name': name, 'categories': [category.pk], 'description': 'Conservar texto',
                })
                self.assertFormError(response.context['form'], 'name', 'Escribe el nombre del elemento.')
                self.assertContains(response, 'Conservar texto')
                self.assertContains(response, f'value="{category.pk}" selected')
                self.assertContains(response, 'aria-invalid="true"')
        self.assertFalse(Item.objects.exists())

    def test_multiple_categories_and_inventory_filter(self):
        category_name = 'Herramientas'
        self.assertEqual(self.client.post(reverse('catalog:category-create'), {'name': category_name}).status_code, 302)
        category = Category.objects.get(name=category_name)
        epp = Category.objects.get(name='EPP')
        self.client.post(reverse('catalog:create'), {'name': 'Linterna', 'categories': [epp.pk, category.pk]})
        Item.objects.create(name='Otro elemento')
        item = Item.objects.get(name='Linterna')
        self.assertEqual(set(item.categories.all()), {epp, category})
        response = self.client.get(reverse('stock:data'), {'category': category.pk}).json()
        self.assertEqual([row['name'] for row in response['data']], ['Linterna'])
        self.assertContains(self.client.get(item.get_absolute_url()), category_name)
        response = self.client.post(reverse('catalog:update', args=[item.pk]), {'name': item.name, 'categories': [category.pk]})
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(list(item.categories.all()), [category])

    def test_at_least_one_category_is_required(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Elemento'})
        self.assertFormError(response.context['form'], 'categories', 'Selecciona al menos una categoría.')
        self.assertFalse(Item.objects.exists())

    def test_unknown_category_is_rejected(self):
        response = self.client.post(reverse('catalog:create'), {'name': 'Elemento', 'categories': [99999]})
        self.assertIn('categories', response.context['form'].errors)
        self.assertFalse(Item.objects.exists())

    def test_catalog_is_shared_when_navigating_between_projects(self):
        item = Item.objects.create(name='Casco común')
        for name in ['Proyecto norte', 'Proyecto sur']:
            project = Project.objects.create(name=name)
            self.assertEqual(self.client.get(project.get_absolute_url()).status_code, 200)
            self.assertIn(item.name, [row['name'] for row in self.client.get(reverse('stock:data')).json()['data']])
        self.assertEqual(Item.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 2)

    def test_item_not_found_returns_404(self):
        self.assertEqual(self.client.get(reverse('catalog:detail', args=[999])).status_code, 404)

    def test_user_text_is_escaped(self):
        item = Item.objects.create(name='<script>alert(1)</script>',
                                   description='<img src=x onerror=alert(1)>')
        for url in [item.get_absolute_url()]:
            response = self.client.get(url, follow=True)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '&lt;script&gt;')
            self.assertNotContains(response, '<img src=x')

    def test_create_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse('catalog:create'), {
            'name': 'Sin token',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Item.objects.exists())

    def test_navigation_marks_current_section(self):
        for route in ('stock:list', 'projects:list', 'catalog:categories',
                      'purchases:list', 'purchases:suppliers', 'projects:home'):
            url = reverse(route)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f'href="{url}"')
            self.assertContains(response, 'aria-current="page"', count=1)
        response = self.client.get(reverse('catalog:category-create'))
        self.assertContains(response, 'aria-current="location"', count=1)

    def test_category_management_separates_listing_and_creation(self):
        listing = reverse('catalog:categories')
        create = reverse('catalog:category-create')
        self.assertContains(self.client.get(listing), 'Agregar categoría')
        self.assertNotContains(self.client.get(reverse('stock:list')), f'href="{create}"')
        self.assertNotContains(self.client.get(reverse('stock:list')), f'href="{create}"')
        self.assertContains(self.client.get(create), f'href="{listing}">Cancelar')
        empty = self.client.post(create, {'name': '  '})
        self.assertFormError(empty.context['form'], 'name', 'Escribe el nombre de la categoría.')
        duplicate = self.client.post(create, {'name': 'EPP'})
        self.assertFormError(duplicate.context['form'], 'name', 'Ya existe una categoría con ese nombre.')
        self.assertRedirects(self.client.post(create, {'name': 'Herramientas'}), listing)
        result = self.client.get(reverse('catalog:category-data'), {'search[value]': 'Herram'}).json()
        self.assertEqual(result['data'], [{'name': 'Herramientas'}])


class InventoryCatalogReplacementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Item.objects.bulk_create([Item(name=f'Casco {i:02d}') for i in range(12)])
        epp = Category.objects.get(name='EPP')
        for item in Item.objects.all():
            item.categories.add(epp)
        Item.objects.create(name='Salida', description='Evacuación').categories.add(
            Category.objects.get(name='Señaléticas'))

    def data(self, **parameters):
        response = self.client.get(reverse('stock:data'), parameters)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_inventory_paginates_and_searches_all_items_and_descriptions(self):
        result = self.data(draw=1)
        self.assertEqual(result['recordsTotal'], 13)
        self.assertEqual(len(result['data']), 10)
        result = self.data(**{'search[value]': 'Casco', 'order[0][column]': 0,
                              'order[0][dir]': 'desc', 'start': 10})
        self.assertEqual([item['name'] for item in result['data']], ['Casco 01', 'Casco 00'])
        for query in ['Señalética', 'Evacuación', 'Salida']:
            self.assertEqual([item['name'] for item in self.data(**{'search[value]': query})['data']], ['Salida'])
        self.assertEqual(self.data(**{'search[value]': 'Salida'})['data'][0]['description'], 'Evacuación')

    def test_old_endpoint_is_removed_and_inventory_is_read_only(self):
        self.assertEqual(self.client.get('/catalogo/datos/').status_code, 404)
        self.assertEqual(self.client.post(reverse('stock:data'), {}).status_code, 405)
        response = self.client.get(reverse('stock:list'))
        for asset in ['dataTables.min.js', 'dataTables.responsive.min.js', 'responsive.bootstrap5.min.css']:
            self.assertContains(response, asset, count=1)


class InventoryElementCreationTests(TestCase):
    def test_initial_quantity_is_optional_or_recorded_once_with_its_date(self):
        from inventory.models import StockPosition, StockRecord
        category = Category.objects.get(name='EPP')
        response = self.client.post(reverse('stock:create'), {'name': 'Sin existencias', 'categories': category.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockPosition.common_balance(Item.objects.get().pk), 0)
        self.assertFalse(StockRecord.objects.exists())
        response = self.client.post(reverse('stock:create'), {
            'name': 'Con existencias', 'categories': category.pk, 'initial_quantity': 4, 'initial_date': '2026-11-12',
        })
        item = Item.objects.get(name='Con existencias')
        self.assertRedirects(response, item.get_absolute_url())
        record = StockRecord.objects.get()
        self.assertEqual(record.operation, 'opening')
        self.assertEqual(record.quantity, 4)
        self.assertIsNone(record.position.project_id)
        self.assertEqual(StockPosition.common_balance(item.pk), 4)

    def test_invalid_initial_quantity_does_not_save_the_element(self):
        response = self.client.post(reverse('stock:create'), {'name': 'Inválido', 'initial_quantity': -1})
        self.assertIn('initial_quantity', response.context['form'].errors)
        self.assertFalse(Item.objects.exists())


class CategoryMigrationTests(TransactionTestCase):
    def test_legacy_types_and_fields_are_preserved(self):
        current = MigrationExecutor(connection).loader.graph.leaf_nodes()
        old = [('catalog', '0001_initial')]
        MigrationExecutor(connection).migrate(old)
        try:
            old_item = MigrationExecutor(connection).loader.project_state(old).apps.get_model('catalog', 'Item')
            helmet = old_item.objects.create(name='Casco', item_type='epp', description='Con visera')
            sign = old_item.objects.create(name='Salida', item_type='signage')
            MigrationExecutor(connection).migrate(current)
            self.assertEqual(list(Item.objects.get(pk=helmet.pk).categories.values_list('name', flat=True)), ['EPP'])
            self.assertEqual(list(Item.objects.get(pk=sign.pk).categories.values_list('name', flat=True)), ['Señaléticas'])
            self.assertEqual(Item.objects.get(pk=helmet.pk).description, 'Con visera')
            self.assertTrue(Category.objects.filter(name='Otros').exists())
        finally:
            MigrationExecutor(connection).migrate(current)
