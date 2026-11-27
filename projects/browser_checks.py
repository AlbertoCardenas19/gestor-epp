"""Optional UI regression suite: manage.py test projects.browser_checks.

Uses Django's isolated PostgreSQL test database, never application records.
Install requirements-dev.txt and a Playwright Chromium (or BROWSER_EXECUTABLE).
"""
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from django.db import connections

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright

from catalog.models import Category, Item
from inventory.common import receive_common_stock
from inventory.models import StockRecord, StockPosition, StockRequest
from inventory.services import cancel_delivery, correct_record, deliver_stock, open_stock
from purchases.models import Supplier
from .models import Project


def data(quantity, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class LibraryBrowserChecks(StaticLiveServerTestCase):
    def test_responsive_row_expansion_search_order_and_pagination(self):
        self.db(lambda: Item.objects.bulk_create([
            Item(name=f'Casco {index:02d}', description='Descripción larga ' * 12)
            for index in range(15)]))
        self.page.set_viewport_size({'width': 320, 'height': 850})
        self.visit_table(reverse('stock:list'))
        self.assertTrue(self.page.locator('table.dataTable').evaluate('e => e.classList.contains("collapsed")'))
        control = self.rows().first.get_by_role('button', name='Mostrar columnas adicionales')
        control.focus()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('table.dataTable tbody tr.child')).to_have_count(1)
        expect(self.rows().first.locator('.row-expand')).to_have_attribute('aria-expanded', 'true')
        expect(self.page.locator('table.dataTable tbody tr.child')).to_contain_text('Descripción')
        details = self.page.locator('table.dataTable tbody tr.child .dtr-details')
        self.assertEqual(details.evaluate('e => getComputedStyle(e).fontSize'), '14.56px')
        self.assertEqual(details.locator('li').last.locator('.dtr-title').inner_text(), 'Descripción')
        self.assertEqual(self.page.url, self.live_server_url + reverse('stock:list'))
        self.search('Casco 14')
        expect(self.rows()).to_have_count(1)
        self.search('')
        expect(self.rows()).to_have_count(10)
        self.page.wait_for_timeout(350)
        self.table_action(lambda: self.page.locator('.dt-paging .next').click())
        self.assertEqual(self.rows().count(), 5, self.page.evaluate('DataTable.tables({api:true}).page.info()'))
        self.order('name')
        expect(self.rows()).to_have_count(10)
        self.assertEqual(self.page.url, self.live_server_url + reverse('stock:list'))

    def test_shared_table_expands_after_resize_sidebar_and_tabs(self):
        item = self.db(lambda: Item.objects.create(name='Casco para prueba de ancho'))
        self.page.set_viewport_size({'width': 390, 'height': 850})
        self.visit_table(reverse('stock:list'))
        self.assertRegex(self.page.locator('script[src*="projects/datatables.js"]').get_attribute('src'),
                         r'/static/projects/datatables\.js\?v=[0-9a-f]{12}$')
        self.assertRegex(self.page.locator('script[src*="projects/components.js"]').get_attribute('src'),
                         r'/static/projects/components\.js\?v=[0-9a-f]{12}$')

        def check_width():
            self.page.wait_for_timeout(350)
            widths = self.page.locator('.dt-container').first.evaluate('''container => {
              const width = selector => container.querySelector(selector).getBoundingClientRect().width;
              return {container: container.getBoundingClientRect().width,
                header: width('table.dataTable'), body: width('table.dataTable')};
            }''')
            self.assertGreaterEqual(widths['header'] + 2, widths['container'], widths)
            self.assertAlmostEqual(widths['header'], widths['body'], delta=2)

        for width in (700, 1440, 700, 1440):
            self.page.set_viewport_size({'width': width, 'height': 850})
            if width == 1440:
                check_width()
        toggle = self.page.locator('.sidebar-toggle')
        for _ in range(2):
            self.assertTrue(toggle.is_visible())
            button = toggle.evaluate('''element => {
              const bounds = element.getBoundingClientRect();
              const center = {x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2};
              return {top: bounds.top, height: bounds.height,
                hit: document.elementFromPoint(center.x, center.y) === element,
                sidebarEdge: document.querySelector('.app-sidebar').getBoundingClientRect().right,
                buttonCenter: center.x};
            }''')
            self.assertTrue(button['hit'], button)
            self.assertAlmostEqual(button['buttonCenter'], button['sidebarEdge'], delta=2)
            self.assertAlmostEqual(button['top'] + button['height'] / 2, 425, delta=2)
            toggle.click()
            check_width()
        self.visit_table(item.get_absolute_url())
        for tab_id, panel_id in (('item-history-tab', 'item-history'),
                                 ('item-projects-tab', 'item-projects')):
            self.page.locator(f'#{tab_id}').click()
            self.page.wait_for_timeout(350)
            widths = self.page.locator(f'#{panel_id} .dt-container').evaluate('''container => ({
              available: container.getBoundingClientRect().width,
              table: container.querySelector('table.dataTable').getBoundingClientRect().width
            })''')
            self.assertGreaterEqual(widths['table'] + 2, widths['available'], widths)

    def test_iteration_inventory_layout_and_navigation(self):
        item, project, request = self.db(lambda: self._iteration_records())
        self.visit_table(reverse('stock:list'))
        for width in (320, 390, 1440):
            self.page.set_viewport_size({'width': width, 'height': 800})
            self.page.wait_for_timeout(350)
            toggle = self.page.locator('.sidebar-toggle')
            expect(toggle).to_be_visible()
            self.assertFalse(self.page.locator('#sidebar').evaluate('(e) => e.classList.contains("hide")'))
            before = toggle.get_attribute('aria-expanded')
            toggle.click()
            expect(toggle).to_have_attribute('aria-expanded', 'false' if before == 'true' else 'true')
            toggle.click()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'iteration-inventory-{width}')
        self.page.set_viewport_size({'width': 1440, 'height': 800})
        self.page.wait_for_timeout(350)
        self.assertEqual(self.page.locator('section[data-datatable-panel] > .list-controls').count(), 0)
        for width in (390, 1440, 320, 1440):
            self.page.set_viewport_size({'width': width, 'height': 800})
            self.page.wait_for_timeout(350)
            self.wait_for_table_alignment()
            if width == 1440:
                metrics = self.page.locator('.dt-container').evaluate('''container => ({
                    table: container.querySelector('table.dataTable').getBoundingClientRect().width,
                    space: container.getBoundingClientRect().width
                })''')
                self.assertGreaterEqual(metrics['table'] + 2, metrics['space'], metrics)
        self.page.set_viewport_size({'width': 1440, 'height': 800})
        self.assertEqual(self.page.locator('table.dataTable thead th[data-column]').count(), 5)
        self.assertEqual(self.page.locator('table.dataTable tbody tr').count(), 1)
        self.assertEqual(self.page.locator('table.dataTable tbody tr a[href="%s"]' % item.get_absolute_url()).count(), 1)
        self.page.locator('table.dataTable tbody tr td').nth(2).click()
        expect(self.page.get_by_role('heading', name=item.name)).to_be_visible()
        self.visit_table(reverse('requests:list', args=[project.pk]))
        expect(self.page.locator('table.dataTable .pending-delivery')).to_have_text('Pendiente')
        self.assertEqual(self.page.locator('table.dataTable thead th[data-column]').count(), 6)
        self.page.locator('table.dataTable tbody tr td').nth(2).click()
        expect(self.page.get_by_role('heading', name=item.name)).to_be_visible()
        self.assertEqual(self.page.url.split('?')[0], self.live_server_url + request.get_absolute_url())

    @staticmethod
    def _iteration_records():
        item = Item.objects.create(name='Casco de prueba')
        project = Project.objects.create(name='Obra de prueba')
        request = StockRequest.objects.create(item=item, project=project, quantity=3, occurred_on=date(2026, 11, 26))
        return item, project, request

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
        return self.page.locator('table.dataTable tbody tr:not(.child)')

    @staticmethod
    def pagination_style(locator):
        return locator.evaluate('(e) => { const s=getComputedStyle(e); return {height:s.minHeight, radius:s.borderRadius, border:s.borderColor, padding:s.padding}; }')

    def wait_for_table_alignment(self, scope='body'):
        self.page.wait_for_timeout(300)
        metrics = self.page.evaluate('''(scope) => {
          const root = document.querySelector(scope);
          const headers = [...root.querySelectorAll('table.dataTable thead th[data-dt-column]')];
          const cells = [...root.querySelectorAll('table.dataTable tbody tr:first-child td')];
          return {headers: headers.map(e=>e.getBoundingClientRect().width), cells: cells.map(e=>e.getBoundingClientRect().width)};
        }''', arg=scope)
        self.assertEqual(len(metrics['headers']), len(metrics['cells']), metrics)
        self.assertTrue(all(abs(header - metrics['cells'][index]) < 2 for index, header in enumerate(metrics['headers'])), metrics)

    def search(self, query):
        return self.table_action(lambda: self.page.locator('.dt-search input').fill(query))

    def order(self, column):
        return self.table_action(lambda: self.page.locator(f'table.dataTable thead th[data-column="{column}"] .dt-column-order').click())

    def test_catalog_empty_one_many_search_sort_and_reload_actions(self):
        self.visit_table(reverse('stock:list'))
        expect(self.page.locator('.dt-empty')).to_have_text('No hay registros disponibles.')
        item = self.db(lambda: Item.objects.create(name='Único casco'))
        self.visit_table(reverse('stock:list'))
        expect(self.rows()).to_have_count(1)
        self.db(lambda: Item.objects.bulk_create([Item(name=f'Elemento {i:02d}') for i in range(40)]))
        self.visit_table(reverse('stock:list'))
        expect(self.rows()).to_have_count(10)
        self.assertNotIn('Elemento 39', self.rows().all_text_contents())
        payload = self.search('Elemento 39')
        self.assertEqual(payload['recordsFiltered'], 1)
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.dt-search input')).to_be_focused()
        self.search('Elemento')
        self.table_action(lambda: self.page.locator('.dt-paging .next').click())
        expect(self.rows()).to_have_count(10)
        payload = self.order('name')
        self.assertEqual(payload['data'][0]['name'], 'Elemento 39')
        self.assertEqual(self.page.locator('thead th[data-column="name"]').evaluate('(e) => getComputedStyle(e).backgroundColor'), 'rgb(234, 244, 251)')
        self.table_action(lambda: self.page.locator('.dt-length select').select_option('25'))
        expect(self.rows()).to_have_count(25)
        self.page.evaluate('EppTables.init(); EppTables.init(); EppComponents.init()')
        expect(self.page.locator('.dt-search')).to_have_count(1)
        expect(self.page.locator('.dt-length')).to_have_count(1)
        expect(self.page.locator('.dt-info')).to_have_count(1)
        self.assertTrue(self.page.evaluate('DataTable.tables({api:true}).page.info().serverSide'))
        self.rows().first.get_by_role('link', name='Elemento 39', exact=True).click()
        expect(self.page.get_by_role('heading', level=1)).to_have_text('Elemento 39')
        # A user-entered HTML name is rendered as text, never executed.
        item.name = '<img src=x onerror="window.uiInjected=true">'
        self.db(item.save)
        self.visit_table(reverse('stock:list'))
        self.search('onerror')
        expect(self.rows()).to_contain_text(item.name)
        expect(self.page.locator('table.dataTable tbody img')).to_have_count(0)
        self.assertIsNone(self.page.evaluate('window.uiInjected'))

    def test_home_actions_and_shared_table_layout(self):
        self.page.goto(self.live_server_url + reverse('projects:home'))
        cards = self.page.locator('.home-panel')
        expect(cards).to_have_count(3)
        expect(cards.nth(2)).to_have_attribute('href', reverse('purchases:list'))
        self.assertEqual(cards.locator('.home-panel-actions').count(), 3)
        cards.nth(0).locator('p').evaluate('(p) => p.textContent += " Descripción extensa para comprobar la alineación de las acciones en una misma fila."')
        actions = cards.locator('.home-panel-actions')
        self.assertAlmostEqual(actions.nth(0).bounding_box()['y'], actions.nth(1).bounding_box()['y'], delta=2)
        cards.nth(2).click()
        expect(self.page).to_have_url(self.live_server_url + reverse('purchases:list'))

        self.db(lambda: Item.objects.create(name='Casco de diseño'))
        self.visit_table(reverse('stock:list'))
        self.assertEqual(self.page.locator('[data-datatable-filter], [data-datatable-state], .table-search-row').count(), 0)
        search = self.page.get_by_label('Buscar', exact=True)
        expect(search).to_have_attribute('placeholder', 'Nombre, categoría, descripción')
        self.assertEqual(self.page.locator('.dt-search').count(), 1)
        input_widths = {}
        for width in (1440, 1000, 800, 700, 500, 470, 460, 390, 320, 1440):
            self.page.set_viewport_size({'width': width, 'height': 850})
            self.page.wait_for_timeout(350)
            metrics = self.page.locator('.dt-container').evaluate('''container => {
              const tableRow = container.querySelector('.dt-layout-table');
              const before = tableRow.previousElementSibling;
              const after = tableRow.nextElementSibling;
              const length = container.querySelector('.dt-length').getBoundingClientRect();
              const search = container.querySelector('.dt-search').getBoundingClientRect();
              const input = container.querySelector('.dt-search input').getBoundingClientRect();
              const table = container.querySelector('table.dataTable').getBoundingClientRect();
              return {topGap: tableRow.getBoundingClientRect().top - before.getBoundingClientRect().bottom,
                bottomGap: after.getBoundingClientRect().top - tableRow.getBoundingClientRect().bottom,
                sameRow: Math.abs(length.top - search.top) < 4,
                rowGap: search.top - length.bottom, searchX: search.left, lengthX: length.left,
                inputWidth: input.width, searchEnd: search.right, containerEnd: container.getBoundingClientRect().right,
                tableWidth: table.width, available: container.getBoundingClientRect().width,
                header: getComputedStyle(container.querySelector('thead th')).backgroundColor,
                headerSize: getComputedStyle(container.querySelector('thead th')).fontSize,
                cellSize: getComputedStyle(container.querySelector('tbody td')).fontSize,
                label: container.querySelector('.dt-search label').textContent.trim()};
            }''')
            self.assertGreaterEqual(metrics['topGap'], 10, metrics)
            self.assertGreaterEqual(metrics['bottomGap'], 10, metrics)
            self.assertGreaterEqual(metrics['tableWidth'] + 2, metrics['available'], metrics)
            self.assertEqual(metrics['header'], 'rgb(234, 244, 251)')
            self.assertEqual(metrics['headerSize'], '13.44px')
            self.assertEqual(metrics['cellSize'], '14.56px')
            self.assertEqual(metrics['label'], 'Buscar')
            self.assertLessEqual(metrics['searchEnd'], metrics['containerEnd'] + 2, metrics)
            input_widths[width] = metrics['inputWidth']
            if width >= 470:
                self.assertTrue(metrics['sameRow'], metrics)
            else:
                self.assertFalse(metrics['sameRow'], metrics)
                self.assertGreaterEqual(metrics['rowGap'], 11, metrics)
                self.assertAlmostEqual(metrics['searchX'], metrics['lengthX'], delta=2, msg=metrics)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.assertGreater(input_widths[1440], input_widths[1000])
        self.assertGreater(input_widths[500], input_widths[470])
        self.visit_table(reverse('stock:list') + '?category=999999')
        self.assertEqual(self.page.evaluate('DataTable.tables({api:true}).page.info().recordsTotal'), 1)

    def test_delivery_dates_quantities_states_and_inventory_actions(self):
        project, item, replacement, balance, count = self.db(self.seed_deliveries)
        self.visit_table(project.get_absolute_url())
        self.assertEqual(self.page.evaluate('DataTable.tables({api:true}).page.info().recordsTotal'), count + 1)
        self.assertEqual(self.search('Otro proyecto')['recordsFiltered'], 0)
        self.search('')
        self.assertEqual(self.order('quantity')['data'][0]['quantity'], '1')
        self.assertEqual(self.order('quantity')['data'][0]['quantity'], '19')
        self.assertEqual(self.order('date')['data'][0]['date'], '2025-12-31')
        self.assertEqual(self.page.locator('[data-datatable-state]').count(), 0)
        result = self.search('Anulado')
        self.assertEqual(result['recordsFiltered'], 1)
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        expect(self.page.locator('.dropdown-menu.show').get_by_role('link')).to_have_count(1)
        self.page.keyboard.press('Escape')
        self.search('')
        self.search('Persona corregida')
        self.rows().get_by_role('button', name=re.compile('^Acciones de')).click()
        self.page.locator('.dropdown-menu.show').get_by_role('link', name='Corregir', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('7')
        self.page.get_by_label('Motivo de la corrección', exact=False).fill('Cantidad correcta')
        self.page.get_by_role('button', name='Guardar corrección', exact=True).click()
        expect(self.page.get_by_test_id('balance')).to_have_text(str(balance - 2))
        self.visit_table(project.get_absolute_url())
        self.search('Persona corregida')
        self.rows().filter(has_text='Vigente').get_by_role('button', name=re.compile('^Acciones de')).click()
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
        item = Item.objects.create(name='Casco')
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
        helmet = Item.objects.create(name='Casco')
        gloves = Item.objects.create(name='Guantes')
        epp, _ = Category.objects.get_or_create(name='EPP')
        gloves.categories.add(epp)
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
        self.rows().get_by_role('link', name='Casco', exact=True).click()
        self.page.get_by_role('link', name='Registrar entrada', exact=True).click()
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
            expect(self.rows().first.get_by_role('link', name='Casco', exact=True)).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'common-stock-{width}')

    @staticmethod
    def seed_request_flow():
        north = Project.objects.create(name='Norte')
        item = Item.objects.create(name='Casco')
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
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('0 Pendiente')
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
        expect(self.page.locator('table.dataTable thead th[data-column="description"]')).to_have_count(1)
        self.assertEqual(self.page.locator('table.dataTable thead th[data-column]').evaluate_all(
            'headers => headers.map(header => header.dataset.column)'),
            ['name', 'type', 'quantity', 'delivered', 'description'])
        self.assertNotIn('data-column="description"', self.page.request.get(
            self.live_server_url + reverse('requests:list', args=[north.pk])).text())
        self.table_action(lambda: self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click())
        expect(self.page.locator('.dt-search input')).to_have_value('')
        expect(self.page.locator('.dt-search input')).to_be_focused()
        # Clear before DataTables' delayed search executes: the old term must not return.
        self.page.locator('.dt-search input').fill('No existe')
        self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click()
        self.page.wait_for_timeout(500)
        expect(self.rows()).to_have_count(1)
        expect(self.page.locator('.dt-search input')).to_have_value('')
        self.rows().first.get_by_role('link', name='Casco', exact=True).click()
        self.page.get_by_role('link', name='Registrar entrada', exact=True).click()
        self.page.get_by_label('Cantidad', exact=False).fill('3')
        self.page.get_by_label('Fecha del conteo o recepción', exact=False).fill('2026-11-12')
        self.page.get_by_role('button', name='Guardar entrada', exact=True).click()
        self.inventory_counts(3, 2)
        self.page.goto(self.live_server_url + request.get_absolute_url())
        self.page.get_by_role('link', name='Reservar disponibles', exact=True).click()
        self.page.get_by_role('button', name='Reservar disponibles', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('2 Pendiente')
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
            expect(self.rows().first.get_by_role('link', name='Casco', exact=True)).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'project-requests-{width}')

    def test_mobile_menu_clipping_sidebar_and_project_cards(self):
        projects = self.db(lambda: [Project.objects.create(name=f'Obra {i:02d}') for i in range(14)])
        self.db(lambda: Item.objects.bulk_create([Item(name=f'Elemento {i:02d}') for i in range(14)]))
        self.db(lambda: Supplier.objects.create(name='Proveedor de prueba', rut='1-9'))
        for width in [320, 390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.visit_table(reverse('stock:list'))
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
            header = self.page.locator('table.dataTable thead th').first
            self.assertEqual(header.evaluate('(e)=>getComputedStyle(e).backgroundColor'), 'rgb(234, 244, 251)')
            self.assertEqual(header.evaluate('(e)=>getComputedStyle(e).color'), 'rgb(15, 23, 42)')
            self.page.mouse.move(0, 0)
            cell = self.rows().first.locator('td').first
            self.assertEqual(cell.evaluate('(e)=>getComputedStyle(e).backgroundColor'), 'rgb(255, 255, 255)')
            cell.hover()
            self.assertEqual(cell.evaluate('(e)=>getComputedStyle(e).backgroundColor'), 'rgb(237, 242, 247)')
            datatable_page_style = self.pagination_style(self.page.locator('.dt-paging .page-item.active .page-link').first)
            self.visit_table(reverse('purchases:suppliers'))
            action_header = self.page.locator('table.dataTable thead th[data-actions]')
            expect(action_header).to_have_class(re.compile('table-actions'))
            if width >= 768:
                self.assertLess(action_header.bounding_box()['width'], self.page.locator('table.dataTable').bounding_box()['width'] * .3)

            action_row = self.rows().last
            if action_row.locator('.row-expand').is_visible():
                action_row.locator('.row-expand').click()
                action_row = self.page.locator('table.dataTable tbody tr.child').last
            action_row.get_by_role('button', name=re.compile('^Acciones de')).click()
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
            self.page.get_by_label('Buscar proyectos', exact=True).fill('Obra 13')
            expect(self.page.locator('.project-card')).to_have_count(1)
            self.page.get_by_role('button', name='Limpiar búsqueda', exact=True).click()
            expect(self.page.locator('.project-card')).to_have_count(6)
            self.page.get_by_label('Buscar proyectos', exact=True).fill('Obra 13')
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
            Item.objects.bulk_create([Item(name=f'Elemento {i:02d}') for i in range(14)])
            item = Item.objects.create(name='Zeta Casco', description='Detalle del casco')
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
        expect(self.page.locator('#sidebar')).to_have_class(re.compile('sidebar-narrow'))
        self.capture('picker-selected-mobile')
        self.page.get_by_label('Cantidad solicitada', exact=False).fill('5')
        self.page.get_by_role('button', name='Guardar solicitud', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('0 Pendiente')
        expect(self.page.get_by_text('Pendiente', exact=True)).to_be_visible()
        self.inventory_counts(15, 0)
        self.visit_table(reverse('requests:list', args=[north.pk]))
        expect(self.rows().first.locator('td').nth(2)).to_have_text('5')
        delivered_cell = self.rows().first.locator('td').nth(3)
        expect(delivered_cell).to_have_text('Pendiente 0')
        self.rows().first.locator('.row-expand').click()
        expect(self.page.locator('table.dataTable tbody tr.child').get_by_text('Pendiente', exact=True)).to_be_visible()
        self.rows().first.get_by_role('link', name='Zeta Casco', exact=True).click()
        self.page.get_by_role('link', name='Confirmar entrega', exact=True).click()
        self.page.get_by_label('Nombre completo del trabajador', exact=False).fill('Ana Pérez')
        self.page.get_by_role('button', name='Confirmar entrega', exact=True).click()
        expect(self.page.get_by_test_id('request-delivered')).to_have_text('5')
        expect(self.page.get_by_text('Pendiente', exact=True)).to_have_count(0)
        self.visit_table(reverse('requests:list', args=[north.pk]))
        expect(self.rows().first.locator('td').nth(3)).to_have_text('5')
        expect(self.rows().first.get_by_text('Pendiente', exact=True)).to_have_count(0)
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
        self.assertEqual(movements.locator('[data-datatable-filter]').count(), 0)
        self.table_action(lambda: movements.locator('.dt-search input').fill('Empresa'))
        expect(movements.locator('tbody tr')).to_have_count(1)
        expect(movements.locator('tbody tr').first).to_contain_text('Empresa')
        self.table_action(lambda: movements.locator('.dt-search input').fill('Norte'))
        expect(movements.locator('tbody tr').first).to_contain_text('Norte')
        for width in [390, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            self.capture(f'element-detail-{width}')

    def test_shared_loading_initial_update_empty_and_error_states(self):
        self.db(lambda: Item.objects.create(name='Casco'))
        pending = []
        self.page.route('**/inventario/datos/**', lambda route: pending.append(route))
        now = datetime.now(timezone.utc)
        self.page.clock.install(time=now)
        self.page.clock.pause_at(now + timedelta(minutes=1))
        self.page.goto(self.live_server_url + reverse('stock:list'))
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        expect(self.page.locator('.datatable-shell')).to_be_visible()
        self.assertNotIn('Loading', self.page.locator('body').inner_text())
        self.assertEqual(len(pending), 1)
        self.page.clock.run_for(100)
        expect(self.page.locator('.list-skeleton')).to_be_hidden()
        pending.pop().continue_()
        self.page.clock.resume()
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
            item = Item.objects.create(name='Casco')
            return project, item
        project, item = self.db(seed)
        self.page.goto(self.live_server_url + reverse('projects:list'))
        pending = []
        pattern = re.compile(r'/proyectos/\?')
        self.page.route(pattern, lambda route: pending.append(route))
        self.page.get_by_label('Buscar proyectos', exact=True).fill('Fallará')
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

    def test_purchases_invoice_editor_receipt_and_history_on_desktop_and_mobile(self):
        from purchases.models import Invoice, Supplier

        def seed():
            Supplier.objects.bulk_create([Supplier(name=f'Proveedor {index}', rut=f'{index}-0') for index in range(8)])
            Supplier.objects.create(name='Zeta Seguridad', rut='9-9')
            Item.objects.bulk_create([Item(name=f'Elemento {index}') for index in range(8)])
            Item.objects.create(name='Zeta Casco')
            other, _ = Category.objects.get_or_create(name='Otros')
            return Project.objects.create(name='Norte'), Project.objects.create(name='Sur'), other

        north, south, other = self.db(seed)
        self.visit_table(reverse('purchases:list'))
        expect(self.rows().first).to_contain_text('No hay')
        self.page.get_by_role('link', name='Agregar factura').click()
        expect(self.page.locator('[data-item-picker][data-picker-ready]').first).to_be_visible()
        self.page.get_by_label('Buscar proveedor').fill('Zeta')
        self.page.get_by_role('button', name='Zeta Seguridad').click()
        self.page.locator('#id_number').fill('Z-100')
        self.page.locator('#id_issued_on').fill('2026-11-20')
        self.page.locator('#id_due_on').fill('2026-11-26')
        self.page.locator('#id_total').fill('12000')
        self.page.locator('#id_lines-0-item_query').fill('Zeta')
        self.page.get_by_role('button', name='Zeta Casco').click()
        self.page.locator('#id_lines-0-item_query').fill('Elemento')
        expect(self.page.get_by_role('button', name='Elemento 0')).to_be_visible()
        expect(self.page.get_by_text('Seleccionado: Zeta Casco')).to_be_visible()
        self.page.locator('#id_lines-0-quantity').fill('20')
        self.page.locator('#id_lines-0-unit_price').fill('500')
        first_line = self.page.locator('[data-form-row]').first
        first_line.get_by_text('Distribuir cantidades por proyecto').click()
        first_line.get_by_role('button', name='Agregar proyecto').click()
        self.page.locator('#id_lines-0-allocations-0-project').select_option(str(north.pk))
        self.page.locator('#id_lines-0-allocations-0-quantity').fill('12')
        first_line.get_by_role('button', name='Agregar proyecto').click()
        self.page.locator('#id_lines-0-allocations-1-project').select_option(str(south.pk))
        self.page.locator('#id_lines-0-allocations-1-quantity').fill('5')
        self.page.get_by_role('button', name='Agregar línea').click()
        self.page.locator('#id_lines-1-item_query').fill('Sin coincidencia')
        expect(self.page.get_by_text('No hay resultados para esta búsqueda.')).to_be_visible()
        self.page.get_by_text('Crear un elemento nuevo').last.click()
        self.page.locator('#id_lines-1-new-name').fill('Linterna de inspección')
        self.page.locator('#id_lines-1-new-categories').select_option(str(other.pk))
        self.page.locator('#id_lines-1-quantity').fill('2')
        self.page.locator('#id_lines-1-unit_price').fill('1000')
        for width in (320, 390, 1440):
            self.page.set_viewport_size({'width': width, 'height': 1000})
            self.page.wait_for_timeout(300)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.page.set_viewport_size({'width': 390, 'height': 900})
        expect(self.page.locator('#sidebar')).to_have_class(re.compile('sidebar-narrow'))
        self.page.get_by_role('button', name='Guardar factura').click()
        expect(self.page.get_by_role('heading', name='Factura Z-100')).to_be_visible()
        expect(self.page.get_by_text('Sin asignar · 3')).to_be_visible()
        expect(self.page.get_by_text('Linterna de inspección')).to_be_visible()
        expect(self.page.get_by_text('No hay entradas asociadas.')).to_be_visible()
        invoice = self.db(lambda: Invoice.objects.get(number='Z-100'))
        self.page.get_by_role('link', name='Confirmar recepción completa').click()
        self.page.get_by_role('button', name='Confirmar recepción completa').click()
        expect(self.page.get_by_role('link', name=re.compile('Zeta Casco · 20'))).to_be_visible()
        expect(self.page.get_by_text('Pendiente', exact=True)).to_be_visible()
        self.page.get_by_role('link', name='Marcar como pagada').click()
        self.page.get_by_label('Fecha de pago').fill('2026-11-26')
        self.page.get_by_role('button', name='Marcar factura como pagada').click()
        expect(self.page.get_by_text('Pagada · 26/11/2026', exact=True)).to_be_visible()
        self.assertEqual(self.db(lambda: StockRecord.objects.filter(invoice=invoice).count()), 2)
        self.page.get_by_role('link', name='Corregir').click()
        self.page.locator('#id_lines-0-unit_price').fill('550')
        self.page.get_by_label('Motivo de la corrección').fill('Ajustar el precio transcrito')
        self.page.get_by_role('button', name='Guardar factura').click()
        correction = self.page.get_by_text(re.compile('^Corrección ·'))
        correction.click()
        expect(correction.locator('..').get_by_text(re.compile('500 CLP por unidad sin IVA'))).to_be_visible()
        self.assertEqual(self.db(lambda: StockRecord.objects.filter(invoice=invoice).count()), 2)
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))

    def test_grouped_sidebar_and_category_pages_with_keyboard(self):
        self.page.goto(self.live_server_url + reverse('stock:list'))
        nav = self.page.get_by_role('navigation', name='Principal')
        expect(nav.get_by_role('heading')).to_have_text(['General', 'Elementos', 'Compras'])
        expected = [('Inicio', 'projects:home'), ('Proyectos', 'projects:list'),
                    ('Inventario', 'stock:list'), ('Categorías', 'catalog:categories'),
                    ('Facturas', 'purchases:list'), ('Proveedores', 'purchases:suppliers')]
        for label, route in expected:
            expect(nav.get_by_role('link', name=label, exact=True)).to_have_attribute('href', reverse(route))
        expect(nav.locator('[aria-current="page"]')).to_have_accessible_name('Inventario')
        toggle = self.page.locator('.sidebar-toggle')
        toggle.focus()
        self.page.keyboard.press('Enter')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        self.page.keyboard.press('Enter')
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        self.page.set_viewport_size({'width': 320, 'height': 760})
        self.page.wait_for_timeout(350)
        if toggle.get_attribute('aria-expanded') == 'false':
            toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        self.page.wait_for_timeout(350)
        nav.get_by_role('link', name='Categorías', exact=True).click()
        self.assertEqual(self.page.locator('#sidebar a[href="%s"]' % reverse('catalog:categories')).get_attribute('aria-current'), 'page')
        self.page.get_by_role('link', name='Agregar categoría').click()
        self.page.get_by_label('Nombre').fill('Herramientas de prueba')
        self.page.get_by_role('button', name='Guardar categoría').click()
        expect(self.rows().filter(has_text='Herramientas de prueba')).to_have_count(1)

    def test_sidebar_identity_font_and_title_alignment(self):
        expected_font = 'system-ui, -apple-system, "Segoe UI", sans-serif'
        for route in ('projects:home', 'projects:list', 'stock:list'):
            self.page.set_viewport_size({'width': 1440, 'height': 850})
            self.page.goto(self.live_server_url + reverse(route))
            button = self.page.locator('.sidebar-toggle')
            if button.get_attribute('aria-expanded') == 'false':
                button.click()
            self.page.wait_for_timeout(300)
            brand = self.page.locator('#sidebar .brand')
            expect(brand).to_have_accessible_name('Gestor EPP: inicio')
            expect(brand.locator('.brand-mark')).to_have_text('E')
            alignment = self.page.evaluate('''() => ({
              navigation: document.querySelector('.sidebar-group-title').getBoundingClientRect().top,
              title: document.querySelector('main h1').getBoundingClientRect().top,
              font: getComputedStyle(document.body).fontFamily,
              buttonFont: getComputedStyle(document.querySelector('.sidebar-toggle')).fontFamily,
              overflow: document.documentElement.scrollWidth > innerWidth
            })''')
            self.assertAlmostEqual(alignment['navigation'], alignment['title'], delta=3, msg=alignment)
            self.assertEqual(alignment['font'], expected_font)
            self.assertEqual(alignment['buttonFont'], expected_font)
            self.assertFalse(alignment['overflow'])
            if route == 'stock:list':
                for selector in ('input', 'select', 'table'):
                    self.assertEqual(self.page.locator(selector).first.evaluate('(e) => getComputedStyle(e).fontFamily'), expected_font)
            button.click()
            expect(self.page.locator('#sidebar')).to_have_class(re.compile('sidebar-narrow'))
            expect(brand).to_be_hidden()
            self.page.wait_for_timeout(300)
            self.assertEqual(self.page.locator('#sidebar').bounding_box()['width'], 28)

        self.page.set_viewport_size({'width': 390, 'height': 850})
        self.page.locator('.sidebar-toggle').click()
        expect(self.page.locator('#sidebar .brand')).to_be_visible()
        expect(self.page.get_by_role('navigation', name='Principal').get_by_role('link', name='Inventario')).to_be_visible()
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.page.set_viewport_size({'width': 320, 'height': 850})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.page.set_viewport_size({'width': 1440, 'height': 850})
        self.page.wait_for_timeout(300)
        self.assertAlmostEqual(self.page.locator('.sidebar-group-title').first.bounding_box()['y'],
                               self.page.locator('main h1').bounding_box()['y'], delta=3)

    def test_sidebar_edge_control_and_single_labels(self):
        labels = ['Inicio', 'Proyectos', 'Inventario', 'Categorías', 'Facturas', 'Proveedores']
        self.page.goto(self.live_server_url + reverse('projects:home'))
        sidebar = self.page.locator('#sidebar')
        nav = sidebar.get_by_role('navigation', name='Principal')
        toggle = self.page.locator('.sidebar-toggle')
        expect(toggle).to_have_count(1)
        expect(nav.get_by_role('link')).to_have_text(labels)
        self.assertRegex(self.page.locator('link[href*="projects/app.css"]').get_attribute('href'),
                         r'/static/projects/app\.css\?v=[0-9a-f]{12}$')

        def check_style(expanded):
            values = self.page.evaluate('''() => {
              const sidebar = document.querySelector('#sidebar');
              const button = document.querySelector('.sidebar-toggle');
              const heading = document.querySelector('.sidebar-group-title');
              const link = document.querySelector('#sidebar .nav-link');
              const circle = getComputedStyle(button, '::before');
              const group = document.querySelector('.sidebar-group + .sidebar-group');
              const center = button.getBoundingClientRect();
              return {background: getComputedStyle(sidebar).backgroundColor,
                border: getComputedStyle(group, '::before').borderTopColor,
                headingX: heading.getBoundingClientRect().x,
                linkX: link.querySelector('.sidebar-link-label').getBoundingClientRect().x,
                separatorX: group.getBoundingClientRect().x + 12,
                activeBackground: getComputedStyle(document.querySelector('#sidebar .nav-link.active')).backgroundColor,
                activeColor: getComputedStyle(document.querySelector('#sidebar .nav-link.active')).color,
                inactiveColor: getComputedStyle(document.querySelector('#sidebar .nav-link:not(.active)')).color,
                optionGap: getComputedStyle(document.querySelector('.sidebar-group .nav-item + .nav-item')).marginTop,
                heading: parseFloat(getComputedStyle(heading).fontSize),
                weight: getComputedStyle(heading).fontWeight,
                link: parseFloat(getComputedStyle(link).fontSize),
                icon: getComputedStyle(link, '::before').content,
                circle: circle.backgroundColor, radius: circle.borderRadius,
                circleWidth: circle.width, width: sidebar.getBoundingClientRect().width,
                hit: document.elementFromPoint(center.x + center.width / 2,
                  center.y + center.height / 2) === button};
            }''')
            self.assertEqual(values['background'], 'rgb(24, 52, 80)')
            self.assertEqual(values['border'], 'rgba(255, 255, 255, 0.4)')
            self.assertEqual(values['activeColor'], 'rgb(255, 255, 255)')
            self.assertEqual(values['inactiveColor'], 'rgb(255, 255, 255)')
            self.assertEqual(values['optionGap'], '4px')
            self.assertLess(values['heading'], values['link'])
            self.assertAlmostEqual(values['heading'], 11.2, delta=.1)
            self.assertEqual(values['weight'], '700')
            self.assertEqual(values['icon'], 'none')
            self.assertEqual(values['circle'], values['background'])
            self.assertEqual(values['radius'], '50%')
            self.assertEqual(values['circleWidth'], '30px')
            self.assertEqual(values['width'], 255 if expanded else 28)
            self.assertTrue(values['hit'])
            if expanded:
                self.assertEqual((values['headingX'], values['linkX'], values['separatorX']), (28, 28, 28))
                self.assertEqual(values['activeBackground'], 'rgb(48, 76, 107)')

        def check_edge():
            sidebar_box, button_box = sidebar.bounding_box(), toggle.bounding_box()
            self.assertAlmostEqual(button_box['x'] + button_box['width'] / 2,
                                   sidebar_box['x'] + sidebar_box['width'], delta=1)
            self.assertAlmostEqual(button_box['y'] + button_box['height'] / 2,
                                   sidebar_box['y'] + sidebar_box['height'] / 2, delta=1)
            self.assertEqual(button_box['width'], 44)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            if toggle.get_attribute('aria-expanded') == 'true':
                self.assertTrue(toggle.evaluate('''button => {
                const toggle = button.getBoundingClientRect();
                return Array.from(document.querySelectorAll('#sidebar nav a')).every(link =>
                    link.getBoundingClientRect().right <= toggle.left);
                }'''))
            self.assertEqual(sidebar.locator('nav .sidebar-group').evaluate_all('''groups => groups.map(group =>
                getComputedStyle(group, '::before').borderTopWidth)'''), ['0px', '1px', '1px'])

        for width in (1440, 320, 390):
            self.page.set_viewport_size({'width': width, 'height': 650})
            self.page.reload()
            if toggle.get_attribute('aria-expanded') == 'false':
                toggle.click()
            expect(toggle).to_have_accessible_name('Contraer menú')
            self.capture(f'sidebar-expanded-{width}')
            check_edge()
            check_style(True)
            expect(nav.locator('.sidebar-link-label:visible')).to_have_count(6)
            toggle.focus()
            self.page.keyboard.press('Space')
            expect(toggle).to_have_accessible_name('Expandir menú')
            self.capture(f'sidebar-narrow-{width}')
            check_edge()
            check_style(False)
            expect(nav.locator('.sidebar-link-label:visible')).to_have_count(0)

        sidebar.evaluate('element => coreui.Sidebar.getInstance(element).hide()')
        expect(toggle).to_be_in_viewport()
        expect(toggle).to_have_accessible_name('Expandir menú')
        toggle.click()
        expect(sidebar).not_to_have_class(re.compile(r'\bhide\b'))
