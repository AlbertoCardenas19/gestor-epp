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

    def test_pagination_and_search_by_name_type_and_description(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertEqual(response.context['paginator'].count, 13)
        self.assertEqual(len(response.context['items']), 10)
        self.assertContains(response, '<table', count=1)
        response = self.client.get(reverse('catalog:list'), {'q': 'Casco', 'sort': '-name', 'page': 2})
        self.assertEqual([item.name for item in response.context['items']], ['Casco 01', 'Casco 00'])
        self.assertContains(response, 'q=Casco')
        for query in ['Señalética', 'Evacuación', 'Salida']:
            response = self.client.get(reverse('catalog:list'), {'q': query})
            self.assertEqual([item.name for item in response.context['items']], ['Salida'])

    def test_invalid_parameters_and_empty_search(self):
        response = self.client.get(reverse('catalog:list'), {'sort': 'invalid', 'per_page': '99999', 'page': '-1'})
        self.assertEqual(response.context['sort'], 'name')
        self.assertEqual(response.context['paginator'].per_page, 10)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('catalog:list'), {'q': 'No existe'})
        self.assertEqual(response.context['paginator'].count, 0)
        self.assertContains(response, 'No hay elementos para esta consulta.')
