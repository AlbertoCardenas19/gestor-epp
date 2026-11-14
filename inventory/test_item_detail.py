from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from catalog.models import Item
from projects.models import Project
from .availability import available_quantity
from .common import receive_common_stock
from .models import StockRecord
from .request_forms import RequestForm
from .request_services import create_request, deliver_request, reduce_request
from .services import cancel_delivery, open_stock, deliver_stock
from .test_requests import data


class IterationRequestAndDetailTests(TestCase):
    def setUp(self):
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.item = Item.objects.create(name='Casco <seguro>', item_type='epp', description='Descripción existente')
        receive_common_stock(self.item, data(20))

    def inventory_row(self):
        return self.client.get(reverse('stock:data')).json()['data'][0]

    def test_required_twenty_five_example_with_real_delivery_and_cancellation(self):
        self.assertEqual((self.inventory_row()['quantity'], self.inventory_row()['delivered']), ('20', '0'))
        request = create_request(self.north, self.item, data(5))
        row = self.client.get(reverse('requests:data', args=[self.north.pk])).json()['data'][0]
        self.assertEqual((row['quantity'], row['delivered'], row['pending'], row['state']), ('5', '0', True, 'En proceso'))
        self.assertEqual(self.inventory_row()['quantity'], '15')
        self.assertEqual(self.inventory_row()['delivered'], '0')
        payload = data(5, worker_full_name='Ana Pérez')
        record = deliver_request(request, payload)
        self.assertEqual(deliver_request(request, payload).pk, record.pk)
        row = self.client.get(reverse('requests:data', args=[self.north.pk])).json()['data'][0]
        self.assertEqual((row['quantity'], row['delivered'], row['pending'], row['state']), ('5', '5', False, 'Entregado'))
        self.assertEqual((self.inventory_row()['quantity'], self.inventory_row()['delivered']), ('15', '5'))
        cancel_delivery(self.north, record.pk, 'Entrega equivocada')
        row = self.client.get(reverse('requests:data', args=[self.north.pk])).json()['data'][0]
        self.assertEqual((row['delivered'], row['pending'], row['state']), ('0', True, 'En proceso'))
        self.assertEqual((self.inventory_row()['quantity'], self.inventory_row()['delivered']), ('15', '0'))

    @override_settings(TIME_ZONE='America/Santiago')
    def test_request_date_is_server_local_and_timestamp_is_never_overwritten(self):
        moment = datetime(2026, 11, 14, 1, 30, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=moment):
            request = create_request(self.north, self.item, {**data(5), 'occurred_on': '1900-01-01'})
        self.assertEqual(request.occurred_on.isoformat(), '2026-11-13')
        self.assertEqual(request.created_at, moment)
        reduce_request(request, data(pending_quantity=4, reason='Reducir'))
        request.refresh_from_db()
        self.assertEqual(request.created_at, moment)
        self.assertEqual(request.occurred_on.isoformat(), '2026-11-13')
        self.assertNotIn('occurred_on', RequestForm().fields)
        response = self.client.get(reverse('requests:create', args=[self.north.pk]))
        self.assertNotContains(response, 'name="occurred_on"')
        self.assertContains(self.client.get(request.get_absolute_url()), 'Registro de solicitud')

    def test_server_ignores_posted_date_and_rechecks_stock_after_picker_load(self):
        url = reverse('requests:create', args=[self.north.pk])
        self.client.get(url, {'item': self.item.pk})
        create_request(self.south, self.item, data(19))
        response = self.client.post(url, {**data(5), 'item': self.item.pk, 'occurred_on': '1900-01-01'})
        self.assertEqual(response.status_code, 302)
        request = self.north.stock_requests.get()
        self.assertEqual((request.allocated_quantity, request.purchase_quantity), (1, 4))
        self.assertEqual(request.occurred_on, timezone.localdate())
        self.assertEqual(available_quantity(self.item.pk), 0)

    def test_picker_search_all_pages_and_selected_item_outside_results(self):
        items = [Item.objects.create(name=f'Elemento {i:02d}', item_type='epp') for i in range(13)]
        url = reverse('requests:items', args=[self.north.pk])
        response = self.client.get(url)
        self.assertEqual(len(response.context['selector_page']), 6)
        response = self.client.get(url, {'q': 'Elemento 12'})
        self.assertContains(response, f'data-item-choice="{items[-1].pk}"')
        self.assertEqual(response.context['selector_page'].paginator.count, 1)
        self.assertContains(response, 'Stock disponible: 0')
        response = self.client.get(reverse('requests:create', args=[self.north.pk]), {'q': 'No coincide', 'item': items[-1].pk})
        self.assertContains(response, 'Seleccionado: Elemento 12')
        self.assertEqual(response.context['selected_item'].pk, items[-1].pk)
        self.assertContains(self.client.get(url, {'q': 'No coincide'}), 'No hay elementos')
        self.assertEqual(self.client.get(reverse('requests:items', args=[999999])).status_code, 404)

    def test_invalid_form_preserves_hidden_selection_and_does_not_create_request(self):
        response = self.client.post(reverse('requests:create', args=[self.north.pk]), {**data(0), 'item': self.item.pk})
        self.assertContains(response, 'Seleccionado: Casco &lt;seguro&gt;')
        self.assertIn('quantity', response.context['form'].errors)
        self.assertFalse(self.north.stock_requests.exists())
        response = self.client.post(reverse('requests:create', args=[self.north.pk]), data(1))
        self.assertContains(response, 'id_item_errors')
        self.assertFalse(self.north.stock_requests.exists())

    def test_detail_projects_and_movement_filter_separate_legacy_and_requested(self):
        request = create_request(self.north, self.item, data(5))
        deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        open_stock(self.south, self.item, data(3))
        legacy = deliver_stock(self.south, self.item, data(1, worker_full_name='Luis Soto'))
        response = self.client.get(self.item.get_absolute_url())
        self.assertContains(response, 'Descripción existente')
        self.assertContains(response, 'data-datatable-filter="project"')
        for tab_id, label, selected in [
            ('item-info-tab', 'Información', 'true'),
            ('item-history-tab', 'Historial de movimientos', 'false'),
            ('item-projects-tab', 'Proyectos', 'false'),
        ]:
            self.assertContains(response, f'id="{tab_id}"')
            self.assertContains(response, f'aria-selected="{selected}">{label}</button>')
        self.assertContains(response, 'data-coreui-toggle="tab"', count=3)
        rows = self.client.get(reverse('stock:item-projects-data', args=[self.item.pk])).json()['data']
        self.assertEqual([(r['name'], r['requested'], r['delivered']) for r in rows], [('Norte', '5', '2'), ('Sur', '0', '1')])
        url = reverse('stock:history-data', args=[self.item.pk])
        north = self.client.get(url, {'project': self.north.pk}).json()
        self.assertEqual((north['recordsTotal'], north['data'][0]['origin']), (1, 'Norte'))
        south = self.client.get(url, {'project': self.south.pk}).json()
        self.assertEqual(south['recordsTotal'], 2)
        self.assertTrue(all(row['origin'] == 'Sur' for row in south['data']))
        self.assertEqual(self.client.get(url, {'project': 'company'}).json()['recordsTotal'], 1)
        self.assertEqual(self.client.get(url, {'project': 'invalid'}).json()['recordsTotal'], 0)
        legacy.refresh_from_db()
        self.assertIsNone(legacy.stock_request_id)
        self.assertEqual(StockRecord.objects.filter(stock_request__isnull=False).count(), 1)
        self.assertEqual(self.inventory_row()['item_url'], self.item.get_absolute_url())

    def test_inventory_and_request_order_use_real_deliveries_not_allocations(self):
        request = create_request(self.north, self.item, data(15))
        other = Item.objects.create(name='Guantes', item_type='epp')
        receive_common_stock(other, data(10))
        other_request = create_request(self.north, other, data(3))
        deliver_request(other_request, data(3, worker_full_name='Ana Pérez'))
        rows = self.client.get(reverse('stock:data'), {'order[0][column]': 3, 'order[0][dir]': 'desc'}).json()['data']
        self.assertEqual([(row['name'], row['delivered']) for row in rows], [('Guantes', '3'), ('Casco <seguro>', '0')])
        rows = self.client.get(reverse('requests:data', args=[self.north.pk]),
            {'order[0][column]': 3, 'order[0][dir]': 'desc'}).json()['data']
        self.assertEqual([(row['item'], row['delivered']) for row in rows], [('Guantes', '3'), ('Casco <seguro>', '0')])
        self.assertEqual(request.reserved_quantity, 15)
