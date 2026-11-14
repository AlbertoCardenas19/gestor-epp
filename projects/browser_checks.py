"""Optional UI regression suite: manage.py test projects.browser_checks.

Uses Django's isolated PostgreSQL test database, never application records.
Install requirements-dev.txt and a Playwright Chromium (or BROWSER_EXECUTABLE).
"""
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from django.db import connections

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright

from catalog.models import Item
from inventory.common import receive_common_stock
from inventory.models import StockRecord, StockPosition, StockRequest
from inventory.services import cancel_delivery, correct_record, deliver_stock, open_stock
from .models import Project


def data(quantity, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class LibraryBrowserChecks(StaticLiveServerTestCase):
    def setUp(self):
        self.playwright = sync_playwright().start()
        options = {'headless': True}
        if os.environ.get('BROWSER_EXECUTABLE'):
            options['executable_path'] = os.environ['BROWSER_EXECUTABLE']
        self.browser = self.playwright.chromium.launch(**options)
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='es-CL')
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)

    def tearDown(self):
        try:
            self.capture(self._testMethodName)
        finally:
            self.context.close()
            self.browser.close()
            self.playwright.stop()
        self.assertEqual(self.errors, [])

    def capture(self, name):
        # Sidebar narrows via CoreUI after each navigation; wait for its CSS transition.
        self.page.wait_for_timeout(300)
        if os.environ.get('UI_ARTIFACT_DIR'):
            directory = Path(os.environ['UI_ARTIFACT_DIR'])
            directory.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(directory / f'{name}.png'), full_page=True)

    def db(self, operation):
        # Playwright's sync API runs a loop on this thread. Keep Django ORM calls
        # on a separate synchronous thread, without disabling Django's safeguards.
        def execute():
            try:
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as worker:
            return worker.submit(execute).result()

    def visit_table(self, path):
        self.page.goto(self.live_server_url + path)
        self.page.wait_for_function('window.DataTable && DataTable.tables({api:true}).ajax.json() !== undefined')

    def table_action(self, action):
        with self.page.expect_response(lambda response: '/datos/' in response.url) as pending:
            action()
        payload = pending.value.json()
        self.page.wait_for_function('(draw) => DataTable.tables({api:true}).ajax.json().draw === draw', arg=payload['draw'])
        return payload

    def rows(self):
        return self.page.locator('.dt-scroll-body tbody tr')

    @staticmethod
    def pagination_style(locator):
        return locator.evaluate('(e) => { const s=getComputedStyle(e); return {height:s.minHeight, radius:s.borderRadius, border:s.borderColor, padding:s.padding}; }')

    def wait_for_table_alignment(self, scope='body'):
        self.page.wait_for_timeout(300)
        metrics = self.page.evaluate('''(scope) => {
          const root = document.querySelector(scope);
          const headers = [...root.querySelectorAll('.dt-scroll-head th[data-dt-column]')];
          const cells = [...root.querySelectorAll('.dt-scroll-body tbody tr:first-child td')];
          return {headers: headers.map(e=>e.getBoundingClientRect().width), cells: cells.map(e=>e.getBoundingClientRect().width)};
        }''', arg=scope)
        self.assertEqual(len(metrics['headers']), len(metrics['cells']), metrics)
        self.assertTrue(all(abs(header - metrics['cells'][index]) < 2 for index, header in enumerate(metrics['headers'])), metrics)

    def search(self, query):
        return self.table_action(lambda: self.page.locator('.dt-search input').fill(query))

    def order(self, column):
        return self.table_action(lambda: self.page.locator(f'.dt-scroll-head th[data-column="{column}"] .dt-column-order').click())

    def test_catalog_empty_one_many_search_sort_and_reload_actions(self):
        self.visit_table(reverse('catalog:list'))
        expect(self.page.locator('.dt-empty')).to_have_text('No hay registros disponibles.')
        item = self.db(lambda: Item.objects.create(name='Único casco', item_type=Item.Type.EPP))
        self.visit_table(reverse('catalog:list'))
        expect(self.rows()).to_have_count(1)
        self.db(lambda: Item.objects.bulk_create([Item(name=f'Elemento {i:02d}', item_type=Item.Type.EPP) for i in range(40)]))
        self.visit_table(reverse('catalog:list'))
        expect(self.rows()).to_have_count(10)
        self.assertNotIn('Elemento 39', self.rows().all_text_contents())
        payload = self.search('Elemento 39')
        self.assertEqual(payload['recordsFiltered'], 1)
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.dt-search input')).to_be_focused()
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        expect(self.page.locator('.dropdown-menu.show')).to_be_visible()
        self.page.keyboard.press('ArrowDown')
        expect(self.page.locator('.dropdown-menu.show a').first).to_be_focused()
        self.page.keyboard.press('Escape')
        expect(self.page.locator('.dropdown-menu.show')).to_have_count(0)
        self.search('Elemento')
        self.table_action(lambda: self.page.locator('.dt-paging .next').click())
        expect(self.rows()).to_have_count(10)
        payload = self.order('name')
        self.assertEqual(payload['data'][0]['name'], 'Elemento 39')
        self.table_action(lambda: self.page.locator('.dt-length select').select_option('25'))
        expect(self.rows()).to_have_count(25)
        self.page.evaluate('EppTables.init(); EppTables.init(); EppComponents.init()')
        expect(self.page.locator('.dt-search')).to_have_count(1)
        expect(self.page.locator('.dt-length')).to_have_count(1)
        expect(self.page.locator('.dt-info')).to_have_count(1)
        self.assertTrue(self.page.evaluate('DataTable.tables({api:true}).page.info().serverSide'))
        self.rows().first.get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Ver elemento', exact=True).click()
        expect(self.page.get_by_role('heading', level=1)).to_have_text('Elemento 39')
        # A user-entered HTML name is rendered as text, never executed.
        item.name = '<img src=x onerror="window.uiInjected=true">'
        self.db(item.save)
        self.visit_table(reverse('catalog:list'))
        self.search('onerror')
        expect(self.rows()).to_contain_text(item.name)
        expect(self.page.locator('.dt-scroll-body tbody img')).to_have_count(0)
        self.assertIsNone(self.page.evaluate('window.uiInjected'))

    def test_delivery_dates_quantities_states_and_inventory_actions(self):
        project, item, replacement, balance, count = self.db(self.seed_deliveries)
        self.visit_table(project.get_absolute_url())
        self.assertEqual(self.page.evaluate('DataTable.tables({api:true}).page.info().recordsTotal'), count - 1)
        self.assertEqual(self.search('Otro proyecto')['recordsFiltered'], 0)
        self.search('')
        self.assertEqual(self.order('quantity')['data'][0]['quantity'], '1')
        self.assertEqual(self.order('quantity')['data'][0]['quantity'], '19')
        self.assertEqual(self.order('date')['data'][0]['date'], '2026-01-20')
        result = self.table_action(lambda: self.page.get_by_label('Estado', exact=True).select_option('cancelled'))
        self.assertEqual(result['recordsTotal'], 1)
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        expect(self.page.locator('.dropdown-menu.show').get_by_role('link')).to_have_count(1)
        self.page.keyboard.press('Escape')
        self.table_action(lambda: self.page.get_by_label('Estado', exact=True).select_option('active'))
        self.search('Persona corregida')
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Corregir', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('7')
        self.page.get_by_label('Motivo de la corrección', exact=False).fill('Cantidad correcta')
        self.page.get_by_role('button', name='Guardar corrección', exact=True).click()
        expect(self.page.get_by_test_id('balance')).to_have_text(str(balance - 2))
        self.visit_table(project.get_absolute_url())
        self.search('Persona corregida')
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Anular', exact=True).click()
        self.page.get_by_label('Motivo de la anulación', exact=False).fill('La entrega no ocurrió')
        self.page.get_by_role('button', name='Confirmar anulación', exact=True).click()
        expect(self.page.get_by_test_id('balance')).to_have_text(str(balance + 5))
        expect(self.page.get_by_text('Anulado', exact=True).last).to_be_visible()
        self.db(replacement.refresh_from_db)
        self.assertIsNotNone(replacement.voided_at)

    @staticmethod
    def seed_deliveries():
        project = Project.objects.create(name='Obra Norte')
        other = Project.objects.create(name='Obra Sur')
        item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        opening = open_stock(project, item, data(1000))
        records = [deliver_stock(project, item, data(quantity, worker_full_name=f'Persona {i:02d}',
                   occurred_on=date(2025, 12, 31) + timedelta(days=i * 10)))
                   for i, quantity in enumerate([2, 10, 1] + list(range(3, 20)))]
        cancel_delivery(project, records[0].pk, 'Registro de prueba equivocado')
        replacement = correct_record(project, records[1].pk, data(5, worker_full_name='Persona corregida',
            reason='Cantidad equivocada', destination_project=project, destination_item=item))
        open_stock(other, item, data(50))
        deliver_stock(other, item, data(1, worker_full_name='Otro proyecto'))
        balance = StockPosition.common_balance(item.pk)
        return project, item, replacement, balance, len(records)

    @staticmethod
    def seed_common_stock():
        north = Project.objects.create(name='Norte')
        south = Project.objects.create(name='Sur')
        helmet = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        Item.objects.create(name='Guantes', item_type=Item.Type.EPP)
        open_stock(north, helmet, data(10))
        open_stock(south, helmet, data(7))
        delivery = deliver_stock(north, helmet, data(3, worker_full_name='Ana Pérez'))
        return north, helmet, delivery

    def test_common_stock_receipt_correction_and_legacy_traceability(self):
        north, item, delivery = self.db(self.seed_common_stock)
        self.visit_table(reverse('stock:list'))
        expect(self.rows().nth(1).locator('td').nth(1)).to_have_text('EPP')
        expect(self.rows().nth(1).locator('td').nth(2)).to_have_text('0')
        result = self.search('Casco')
        self.assertEqual(result['data'][0]['quantity'], '14')
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Registrar entrada', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('5')
        self.page.get_by_label('Fecha del conteo o recepción', exact=False).fill('2026-11-12')
        self.page.get_by_label('Observación', exact=False).fill('Entrada de empresa')
        self.page.get_by_role('button', name='Guardar entrada', exact=True).click()
        expect(self.page.get_by_test_id('common-balance')).to_have_text('19')
        original_url = self.page.url
        self.page.get_by_role('link', name='Corregir entrada', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('3')
        self.page.get_by_label('Motivo de la corrección', exact=False).fill('Cantidad revisada')
        self.page.get_by_role('button', name='Guardar corrección', exact=True).click()
        expect(self.page.get_by_test_id('common-balance')).to_have_text('17')
        replacement_url = self.page.url
        self.page.get_by_role('link', name='Ver registro anterior', exact=True).click()
        self.assertEqual(self.page.url, original_url)
        expect(self.page.get_by_text('Cantidad revisada', exact=False)).to_be_visible()
        expect(self.page.get_by_role('link', name='Corregir entrada', exact=True)).to_have_count(0)
        self.page.get_by_role('link', name='Ver reemplazo', exact=True).click()
        self.assertEqual(self.page.url, replacement_url)
        self.visit_table(reverse('stock:history', args=[item.pk]))
        result = self.search('Empresa')
        self.assertEqual(result['recordsFiltered'], 2)
        expect(self.page.get_by_test_id('common-balance')).to_have_text('17')
        # Historical deliveries keep their original URL and contribute once to the common total.
        self.page.goto(self.live_server_url + reverse('stock:record', args=[item.pk, delivery.pk]))
        self.page.get_by_role('link', name='Ver historial del proyecto', exact=True).click()
        self.page.locator(f'#registro-{delivery.pk}').get_by_role('link', name=re.compile('^Anular entrega')).click()
        self.page.get_by_label('Motivo de la anulación', exact=False).fill('Entrega histórica duplicada')
        self.page.get_by_role('button', name='Confirmar anulación', exact=True).click()
        self.visit_table(reverse('stock:history', args=[item.pk]))
        expect(self.page.get_by_test_id('common-balance')).to_have_text('20')
        for width in [320, 390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.visit_table(reverse('stock:list'))
            if self.page.locator('.sidebar-toggle').get_attribute('aria-expanded') == 'true':
                self.page.locator('.sidebar-toggle').click()
                self.page.wait_for_timeout(300)
            self.wait_for_table_alignment()
            self.rows().first.get_by_role('button', name=re.compile('^Acciones de')).click()
            menu = self.page.locator('.dropdown-menu.show')
            expect(menu).to_be_visible()
            hit = menu.locator('a').first.evaluate('(e)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}')
            self.assertTrue(hit)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'common-stock-{width}')
            self.page.keyboard.press('Escape')

    @staticmethod
    def seed_request_flow():
        north = Project.objects.create(name='Norte')
        item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        receive_common_stock(item, data(2))
        return north, item

    def inventory_counts(self, available, delivered):
        self.visit_table(reverse('stock:list'))
        self.search('Casco')
        expect(self.rows().first.locator('td').nth(2)).to_have_text(str(available))
        expect(self.rows().first.locator('td').nth(3)).to_have_text(str(delivered))

    def test_unified_inventory_reserve_confirm_purchase_reduce_and_clear_search(self):
        north, item = self.db(self.seed_request_flow)
        self.page.goto(self.live_server_url + reverse('requests:list', args=[north.pk]))
        self.page.get_by_role('link', name='Solicitar elemento', exact=True).click()
        self.page.locator(f'[data-item-choice="{item.pk}"]').click()
        self.page.get_by_label('Cantidad solicitada', exact=False).fill('5')
        self.page.get_by_role('button', name='Guardar solicitud', exact=True).click()
        request = self.db(lambda: StockRequest.objects.get())
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('0')
        expect(self.page.get_by_test_id('request-purchase')).to_have_text('3')
        self.page.get_by_role('link', name='Confirmar entrega', exact=True).click()
        self.page.get_by_label('Nombre completo del trabajador', exact=False).fill('Ana Pérez')
        self.page.get_by_role('button', name='Confirmar entrega', exact=True).click()
        self.page.goto(self.live_server_url + reverse('requests:deliver', args=[north.pk, request.pk]))
        self.page.get_by_label('Nombre completo del trabajador', exact=False).fill('Intento sin reserva')
        self.page.get_by_label('Cantidad', exact=False).fill('1')
        self.page.get_by_role('button', name='Confirmar entrega', exact=True).click()
        expect(self.page.locator('#id_quantity_errors')).to_contain_text('unidades reservadas')
        expect(self.page.locator('#id_quantity')).to_have_attribute('aria-invalid', 'true')
        self.inventory_counts(0, 2)
        expect(self.page.locator('nav[aria-label="Principal"]').get_by_role('link', name='Catálogo', exact=True)).to_have_count(0)
        expect(self.page.locator('.dt-scroll-head th[data-column="description"]')).to_have_count(0)
        self.table_action(lambda: self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click())
        expect(self.page.locator('.dt-search input')).to_have_value('')
        expect(self.page.locator('.dt-search input')).to_be_focused()
        # Clear before DataTables' delayed search executes: the old term must not return.
        self.page.locator('.dt-search input').fill('No existe')
        self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click()
        self.page.wait_for_timeout(500)
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.dt-search input')).to_have_value('')
        self.rows().first.get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Registrar entrada', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('3')
        self.page.get_by_label('Fecha del conteo o recepción', exact=False).fill('2026-11-12')
        self.page.get_by_role('button', name='Guardar entrada', exact=True).click()
        self.inventory_counts(3, 2)
        self.page.goto(self.live_server_url + request.get_absolute_url())
        self.page.get_by_role('link', name='Reservar disponibles', exact=True).click()
        self.page.get_by_role('button', name='Reservar disponibles', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('2')
        expect(self.page.get_by_test_id('request-purchase')).to_have_text('0')
        self.page.get_by_role('link', name='Confirmar entrega', exact=True).click()
        self.page.get_by_label('Nombre completo del trabajador', exact=False).fill('Luis Soto')
        self.page.get_by_label('Cantidad', exact=False).fill('1')
        self.page.get_by_role('button', name='Confirmar entrega', exact=True).click()
        record = self.db(lambda: StockRecord.objects.select_related('position').get(worker_full_name='Luis Soto'))
        self.page.goto(self.live_server_url + record.get_absolute_url())
        self.page.get_by_role('link', name='Corregir entrega', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('2')
        self.page.get_by_label('Motivo de la corrección', exact=False).fill('Cantidad correcta')
        self.page.get_by_role('button', name='Guardar corrección', exact=True).click()
        self.inventory_counts(0, 4)
        original = self.db(lambda: StockRecord.objects.select_related('position').get(worker_full_name='Ana Pérez'))
        self.page.goto(self.live_server_url + original.get_absolute_url())
        self.page.get_by_role('link', name='Anular entrega', exact=True).click()
        self.page.get_by_label('Motivo de la anulación', exact=False).fill('Entrega equivocada')
        self.page.get_by_role('button', name='Confirmar anulación', exact=True).click()
        self.inventory_counts(0, 2)
        self.page.goto(self.live_server_url + request.get_absolute_url())
        self.page.get_by_role('link', name='Reducir o cancelar pendiente', exact=True).click()
        self.page.get_by_label('Cantidad pendiente que conservar', exact=False).fill('0')
        self.page.get_by_label('Motivo de la reducción o cancelación', exact=False).fill('Ya no se necesita el resto')
        self.page.get_by_role('button', name='Guardar cambio', exact=True).click()
        self.inventory_counts(3, 2)
        for width in [320, 390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.visit_table(reverse('requests:list', args=[north.pk]))
            if self.page.locator('.sidebar-toggle').get_attribute('aria-expanded') == 'true':
                self.page.locator('.sidebar-toggle').click()
                self.page.wait_for_timeout(300)
            self.rows().first.get_by_role('button', name=re.compile('^Acciones de')).click()
            expect(self.page.locator('.dropdown-menu.show')).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'project-requests-{width}')
            self.page.keyboard.press('Escape')

    def test_mobile_menu_clipping_sidebar_and_project_cards(self):
        projects = self.db(lambda: [Project.objects.create(name=f'Obra {i:02d}') for i in range(14)])
        self.db(lambda: Item.objects.bulk_create([Item(name=f'Elemento {i:02d}', item_type=Item.Type.EPP) for i in range(14)]))
        for width in [320, 390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.visit_table(reverse('catalog:list'))
            sidebar = self.page.locator('#sidebar')
            button = self.page.locator('.sidebar-toggle')
            if width < 768:
                expect(sidebar).to_have_class(re.compile('sidebar-narrow'))
            before = button.bounding_box()['y']
            self.assertNotEqual(sidebar.evaluate('(e)=>getComputedStyle(e).transitionDuration'), '0s')
            button.focus()
            self.page.keyboard.press('Enter')
            self.page.wait_for_timeout(300)
            self.assertAlmostEqual(button.bounding_box()['y'], before, delta=1)
            if 'sidebar-narrow' not in sidebar.get_attribute('class'):
                button.click()
                self.page.wait_for_timeout(300)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            header = self.page.locator('.dt-scroll-head th').first
            self.assertEqual(header.evaluate('(e)=>getComputedStyle(e).backgroundColor'), 'rgb(51, 65, 85)')
            self.assertEqual(header.evaluate('(e)=>getComputedStyle(e).color'), 'rgb(255, 255, 255)')
            stripe = self.rows().first.locator('td').first.evaluate('(e)=>getComputedStyle(e).boxShadow')
            self.assertIn('226, 232, 240', stripe)
            datatable_page_style = self.pagination_style(self.page.locator('.dt-paging .page-item.active .page-link').first)
            action_header = self.page.locator('.dt-scroll-head th[data-actions]')
            expect(action_header).to_have_class(re.compile('table-actions'))
            self.assertLess(action_header.bounding_box()['width'], self.page.locator('.dt-scroll-head table').bounding_box()['width'] * .3)

            self.rows().last.get_by_role('button', name=re.compile('^Acciones de')).click()
            menu = self.page.locator('.dropdown-menu.show')
            expect(menu).to_be_visible()
            rectangle = menu.bounding_box()
            self.assertGreaterEqual(rectangle['x'], 0)
            self.assertLessEqual(rectangle['x'] + rectangle['width'], width)
            # Actual hit test: not merely within viewport but outside table clipping too.
            hit = menu.locator('a').first.evaluate('(e)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}')
            self.assertTrue(hit)
            self.capture(f'menu-{width}')
            self.page.keyboard.press('Escape')
            self.page.goto(self.live_server_url + reverse('projects:list'))
            expect(self.page.locator('.project-card')).to_have_count(6)
            expect(self.page.locator('[data-datatable]')).to_have_count(0)
            self.assertEqual(self.pagination_style(self.page.locator('.pagination .page-item.active .page-link').first), datatable_page_style)
            self.page.get_by_role('link', name='Siguiente', exact=True).click()
            expect(self.page.locator('.project-card')).to_have_count(6)
            self.page.get_by_label('Buscar', exact=True).fill('Obra 13')
            expect(self.page.locator('.project-card')).to_have_count(1)
            self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click()
            expect(self.page.locator('.project-card')).to_have_count(6)
            self.page.get_by_label('Buscar', exact=True).fill('Obra 13')
            expect(self.page.locator('.project-card')).to_have_count(1)
            self.page.get_by_role('link', name=re.compile('^Ver proyecto')).click()
            expect(self.page.get_by_role('heading', level=1)).to_have_text(projects[-1].name)
            self.page.reload()
            expect(self.page.locator('#sidebar')).to_have_class(re.compile('sidebar-narrow'))
            self.page.goto(self.live_server_url + reverse('requests:create', args=[projects[0].pk]))
            self.assertEqual(self.pagination_style(self.page.locator('[data-picker-results] .page-item.active .page-link').first), datatable_page_style)
        self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(self.page.locator('#sidebar').evaluate('(e)=>getComputedStyle(e).transitionDuration'), '0s')
        self.assertEqual(self.db(StockRecord.objects.count), 0)

    def test_picker_persistence_actual_delivery_and_element_detail(self):
        def seed():
            north = Project.objects.create(name='Norte')
            Item.objects.bulk_create([Item(name=f'Elemento {i:02d}', item_type='epp') for i in range(14)])
            item = Item.objects.create(name='Zeta Casco', item_type='epp', description='Detalle del casco')
            receive_common_stock(item, data(20))
            return north, item
        north, item = self.db(seed)
        self.page.goto(self.live_server_url + reverse('requests:create', args=[north.pk]))
        expect(self.page.locator('[data-item-choice]')).to_have_count(6)
        expect(self.page.locator('[name="occurred_on"]')).to_have_count(0)
        search = self.page.get_by_label('Buscar elemento', exact=True)
        search.fill('Zeta')
        choice = self.page.locator(f'[data-item-choice="{item.pk}"]')
        expect(choice).to_contain_text('Stock disponible: 20')
        choice.click()
        search.fill('Elemento')
        expect(self.page.locator('[data-item-choice]')).to_have_count(6)
        expect(self.page.locator('[data-picker-selected]')).to_have_text('Seleccionado: Zeta Casco')
        self.page.get_by_role('button', name='Siguiente', exact=True).click()
        expect(self.page.locator('[data-picker-page="1"]')).to_be_visible()
        expect(self.page.locator('[name="item"]')).to_have_value(str(item.pk))
        search.fill('Zeta')
        expect(choice).to_have_attribute('aria-pressed', 'true')
        self.page.set_viewport_size({'width': 390, 'height': 844})
        if self.page.locator('.sidebar-toggle').get_attribute('aria-expanded') == 'true':
            self.page.locator('.sidebar-toggle').click()
        self.capture('picker-selected-mobile')
        self.page.get_by_label('Cantidad solicitada', exact=False).fill('5')
        self.page.get_by_role('button', name='Guardar solicitud', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('0')
        expect(self.page.get_by_label('Pendiente de entrega', exact=True)).to_be_visible()
        self.inventory_counts(15, 0)
        self.visit_table(reverse('requests:list', args=[north.pk]))
        expect(self.rows().first.locator('td').nth(2)).to_have_text('5')
        delivered_cell = self.rows().first.locator('td').nth(3)
        expect(delivered_cell).to_have_text('! 0')
        expect(delivered_cell.get_by_label('Pendiente de entrega', exact=True)).to_be_visible()
        self.rows().first.get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Confirmar entrega', exact=True).click()
        self.page.get_by_label('Nombre completo del trabajador', exact=False).fill('Ana Pérez')
        self.page.get_by_role('button', name='Confirmar entrega', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('5')
        expect(self.page.get_by_label('Pendiente de entrega', exact=True)).to_have_count(0)
        self.visit_table(reverse('requests:list', args=[north.pk]))
        expect(self.rows().first.locator('td').nth(3)).to_have_text('5')
        expect(self.rows().first.get_by_label('Pendiente de entrega', exact=True)).to_have_count(0)
        self.inventory_counts(15, 5)
        self.rows().first.get_by_role('link', name='Zeta Casco', exact=True).click()
        self.page.wait_for_function('window.DataTable && DataTable.tables().length === 2 && DataTable.settings.every(settings => settings.json !== undefined)')
        expect(self.page.get_by_text('Detalle del casco', exact=True)).to_be_visible()
        expect(self.page.get_by_role('tab', name='Información', exact=True)).to_have_attribute('aria-selected', 'true')
        projects_tab = self.page.get_by_role('tab', name='Proyectos', exact=True)
        projects_tab.focus()
        expect(projects_tab).to_be_focused()
        self.page.keyboard.press('Enter')
        expect(projects_tab).to_have_attribute('aria-selected', 'true')
        projects = self.page.locator('#item-projects [data-datatable-panel]')
        expect(projects).to_be_visible()
        self.wait_for_table_alignment('#item-projects')
        expect(projects.locator('tbody tr').first).to_contain_text('Norte')
        expect(projects.locator('tbody tr').first.locator('td').nth(1)).to_have_text('5')
        expect(projects.locator('tbody tr').first.locator('td').nth(2)).to_have_text('5')
        self.page.get_by_role('tab', name='Historial de movimientos', exact=True).click()
        movements = self.page.locator('#item-history [data-datatable-panel]')
        expect(movements).to_be_visible()
        self.wait_for_table_alignment('#item-history')
        self.page.get_by_label('Proyecto', exact=True).select_option('company')
        expect(movements.locator('tbody tr')).to_have_count(1)
        expect(movements.locator('tbody tr').first).to_contain_text('Empresa')
        self.page.get_by_label('Proyecto', exact=True).select_option(str(north.pk))
        expect(movements.locator('tbody tr').first).to_contain_text('Norte')
        for width in [390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'element-detail-{width}')

    def test_shared_loading_initial_update_empty_and_error_states(self):
        self.db(lambda: Item.objects.create(name='Casco', item_type='epp'))
        pending = []
        self.page.route('**/inventario/datos/**', lambda route: pending.append(route))
        self.page.goto(self.live_server_url + reverse('stock:list'))
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        expect(self.page.locator('.datatable-shell')).to_be_visible()
        self.assertNotIn('Loading', self.page.locator('body').inner_text())
        self.assertEqual(len(pending), 1)
        self.page.wait_for_timeout(100)
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        pending.pop().continue_()
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        # A perceptibly slow initial response does reveal the delayed skeleton.
        self.page.reload()
        self.assertEqual(len(pending), 1)
        self.page.wait_for_timeout(200)
        expect(self.page.locator('.list-skeleton')).to_be_visible()
        expect(self.page.locator('.datatable-shell')).to_be_hidden()
        pending.pop().continue_()
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        self.page.locator('.dt-search input').fill('Sin resultados')
        self.assertEqual(self.page.locator('.list-feedback').text_content(), '')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        expect(self.rows().first).to_contain_text('Casco')
        pending.pop().continue_()
        expect(self.page.locator('.dt-empty')).to_have_text('No se encontraron resultados.')
        self.page.locator('.dt-search input').fill('Casco')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        pending.pop().continue_()
        expect(self.rows().first).to_contain_text('Casco')
        self.page.locator('.dt-search input').fill('fallará')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        pending.pop().fulfill(status=503, body='Fallo simulado')
        expect(self.page.locator('.list-feedback')).to_contain_text('No se pudo cargar la tabla')
        expect(self.page.locator('[data-datatable-panel]')).to_have_attribute('aria-busy', 'false')
        expect(self.rows().first).to_contain_text('Casco')
        self.page.locator('.dt-search input').fill('Casco')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        pending.pop().continue_()
        expect(self.page.locator('.list-feedback')).to_have_text('')
        # This response error is intentional; unrelated browser/JS errors still fail tearDown.
        self.errors = [error for error in self.errors if 'status of 503' not in error]
        self.page.unroute('**/inventario/datos/**')
        self.capture('loading-recovered')
        # A failed initial load is an error, not an empty result, and leaves search usable.
        pending = []
        self.page.route('**/inventario/datos/**', lambda route: pending.append(route))
        self.page.reload()
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        self.page.wait_for_timeout(200)
        expect(self.page.locator('.list-skeleton')).to_be_visible()
        pending.pop().fulfill(status=503, body='Fallo inicial simulado')
        expect(self.page.locator('.list-feedback')).to_contain_text('No se pudo cargar la tabla')
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        expect(self.page.locator('.dt-empty')).to_be_hidden()
        self.page.locator('.dt-search input').fill('Casco')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-skeleton')).to_be_visible()
        pending.pop().continue_()
        expect(self.rows().first).to_contain_text('Casco')
        self.errors = [error for error in self.errors if 'status of 503' not in error]

    def test_cards_and_picker_update_failures_keep_content_and_selection(self):
        def seed():
            project = Project.objects.create(name='Proyecto prueba')
            item = Item.objects.create(name='Casco', item_type='epp')
            return project, item
        project, item = self.db(seed)
        self.page.goto(self.live_server_url + reverse('projects:list'))
        pending = []
        pattern = re.compile(r'/proyectos/\?')
        self.page.route(pattern, lambda route: pending.append(route))
        self.page.get_by_label('Buscar', exact=True).fill('Fallará')
        expect(self.page.locator('[data-cards-feedback]')).to_have_text('')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('[data-cards-feedback]')).to_contain_text('Actualizando')
        expect(self.page.locator('.project-card')).to_contain_text('Proyecto prueba')
        pending.pop().fulfill(status=503, body='Fallo simulado de tarjetas')
        expect(self.page.locator('[data-cards-feedback]')).to_contain_text('No se pudo actualizar')
        expect(self.page.locator('.project-card')).to_contain_text('Proyecto prueba')
        self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click()
        self.page.wait_for_timeout(200)
        expect(self.page.locator('[data-cards-feedback]')).to_contain_text('Actualizando')
        pending.pop().continue_()
        expect(self.page.locator('[data-cards-feedback]')).to_have_text('')
        self.page.unroute(pattern)
        self.page.goto(self.live_server_url + reverse('requests:create', args=[project.pk]))
        self.page.locator(f'[data-item-choice="{item.pk}"]').click()
        pending = []
        self.page.route('**/nueva/elementos/**', lambda route: pending.append(route))
        self.page.get_by_label('Buscar elemento', exact=True).fill('Fallará')
        expect(self.page.locator('.list-feedback')).to_have_text('')
        self.page.wait_for_timeout(500)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        expect(self.page.locator('[data-item-choice]')).to_contain_text('Casco')
        pending.pop().fulfill(status=503, body='Fallo simulado de selector')
        expect(self.page.locator('.list-feedback')).to_contain_text('No se pudieron actualizar')
        expect(self.page.locator('[name="item"]')).to_have_value(str(item.pk))
        expect(self.page.locator('[data-item-choice]')).to_have_attribute('aria-pressed', 'true')
        self.page.get_by_role('button', name='Limpiar búsqueda de elementos', exact=True).click()
        self.page.wait_for_timeout(200)
        expect(self.page.locator('.list-feedback')).to_contain_text('Actualizando')
        pending.pop().continue_()
        expect(self.page.locator('.list-feedback')).to_have_text('')
        expect(self.page.locator('[data-item-choice]')).to_have_attribute('aria-pressed', 'true')
        self.errors = [error for error in self.errors if 'status of 503' not in error]
