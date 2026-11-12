from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from .models import Project


class ProjectFlowTests(TestCase):
    def test_database_is_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_home_redirects_to_projects(self):
        self.assertRedirects(self.client.get('/'), reverse('projects:list'))

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
        self.assertContains(detail, 'Proyecto de prueba.<br>Segunda línea.', html=True)
        project.refresh_from_db()
        self.assertEqual(project.description, 'Proyecto de prueba.\nSegunda línea.')

    def test_description_is_optional(self):
        response = self.client.post(reverse('projects:create'), {'name': 'Obra sin descripción'})
        project = Project.objects.get()
        self.assertEqual(project.description, '')
        self.assertRedirects(response, project.get_absolute_url())
        self.assertContains(self.client.get(project.get_absolute_url()), 'Este proyecto aún no tiene descripción.')

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
