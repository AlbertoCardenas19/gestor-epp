import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project
from .common import receive_common_stock
from .models import StockPosition, StockRecord
from .services import cancel_delivery, correct_record, deliver_stock, open_stock


def data(quantity=5, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class CommonStockTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        self.other = Item.objects.create(name='Guantes', item_type=Item.Type.EPP)
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')

    def test_empty_and_zero_do_not_create_fake_positions_or_records(self):
        self.assertEqual(StockPosition.common_balance(self.item.pk), 0)
        result = self.client.get(reverse('stock:data')).json()
        self.assertEqual(result['recordsTotal'], 2)
        self.assertEqual([row['quantity'] for row in result['data']], ['0', '0'])
        self.assertFalse(StockPosition.objects.exists())
        self.assertFalse(StockRecord.objects.exists())

    def test_legacy_balances_and_corrections_are_counted_once_without_copying(self):
        north_opening = open_stock(self.north, self.item, data(10))
        open_stock(self.south, self.item, data(7))
        delivery = deliver_stock(self.north, self.item, data(3, worker_full_name='Ana Pérez'))
        self.assertEqual(StockPosition.common_balance(self.item.pk), 14)
        replacement = correct_record(self.north, delivery.pk, data(2, worker_full_name='Ana Pérez',
            reason='Proyecto equivocado', destination_project=self.south, destination_item=self.item))
        self.assertEqual(StockPosition.common_balance(self.item.pk), 15)
        cancel_delivery(self.south, replacement.pk, 'No ocurrió')
        self.assertEqual(StockPosition.common_balance(self.item.pk), 17)
        before = list(StockRecord.objects.order_by('pk').values())
        result = self.client.get(reverse('stock:data')).json()
        self.assertEqual(result['data'][0]['quantity'], '17')
        history = self.client.get(reverse('stock:history-data', args=[self.item.pk])).json()
        self.assertEqual(history['recordsTotal'], 4)
        self.assertEqual(list(StockRecord.objects.order_by('pk').values()), before)
        self.assertEqual(north_opening.position.balance, 10)

    def test_common_receipt_does_not_require_project_opening_and_is_idempotent(self):
        request = data(5)
        record = receive_common_stock(self.item, request)
        self.assertEqual(receive_common_stock(self.item, request).pk, record.pk)
        self.assertIsNone(record.position.project_id)
        self.assertEqual(record.position.balance, 5)
        self.assertEqual(StockRecord.objects.count(), 1)
        self.assertEqual(StockPosition.objects.count(), 1)
        self.assertEqual(StockPosition.common_balance(self.other.pk), 0)
        self.assertEqual(record.get_absolute_url(), reverse('stock:record', args=[self.item.pk, record.pk]))

    def test_one_common_position_per_item_is_enforced_by_postgresql(self):
        StockPosition.objects.create(project=None, item=self.item)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockPosition.objects.create(project=None, item=self.item)
        StockPosition.objects.create(project=self.north, item=self.item)
        StockPosition.objects.create(project=self.south, item=self.item)
        self.assertEqual(StockPosition.objects.count(), 3)

    def test_create_consult_correct_and_retry_from_forms(self):
        response = self.client.post(reverse('stock:receive', args=[self.item.pk]), data(5))
        record = StockRecord.objects.get()
        self.assertRedirects(response, record.get_absolute_url())
        self.assertContains(self.client.get(response.url), 'data-testid="common-balance">5</span>')
        correction = data(3, reason='Cantidad correcta', observation='Conteo revisado')
        url = reverse('stock:correct', args=[self.item.pk, record.pk])
        response = self.client.post(url, correction)
        replacement = StockRecord.objects.get(replaces=record)
        self.assertRedirects(response, replacement.get_absolute_url())
        self.assertRedirects(self.client.post(url, correction), replacement.get_absolute_url())
        record.refresh_from_db()
        self.assertEqual(record.quantity, 5)
        self.assertIsNotNone(record.voided_at)
        self.assertEqual(record.void_reason, correction['reason'])
        self.assertEqual(StockRecord.objects.count(), 2)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 3)
        self.assertContains(self.client.get(record.get_absolute_url()), replacement.get_absolute_url())
        self.assertContains(self.client.get(replacement.get_absolute_url()), record.get_absolute_url())

    def test_invalid_entries_preserve_input_and_do_not_create_positions(self):
        for quantity in [0, -1, '1.5', '', 9223372036854775808]:
            response = self.client.post(reverse('stock:receive', args=[self.item.pk]), data(quantity, observation='Conservar'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('quantity', response.context['form'].errors)
            self.assertContains(response, 'Conservar')
        self.assertFalse(StockRecord.objects.exists())
        self.assertFalse(StockPosition.objects.exists())

    def test_failed_correction_rolls_back_original_and_balance(self):
        record = receive_common_stock(self.item, data(5))
        with self.assertRaises(ValidationError):
            correct_record(None, record.pk, data(-1, reason='Cantidad inválida'))
        record.refresh_from_db()
        self.assertIsNone(record.voided_at)
        self.assertEqual(record.void_reason, '')
        self.assertEqual(StockRecord.objects.count(), 1)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 5)
        response = self.client.post(reverse('stock:correct', args=[self.item.pk, record.pk]), data(3, reason=''))
        self.assertIn('reason', response.context['form'].errors)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 5)

    def test_common_receipt_form_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse('stock:receive', args=[self.item.pk]), data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(StockRecord.objects.exists())

    def test_common_record_cannot_cross_items_or_edit_legacy_record_from_common_route(self):
        record = open_stock(self.north, self.item, data(10))
        self.assertEqual(self.client.get(reverse('stock:record', args=[self.other.pk, record.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('stock:correct', args=[self.item.pk, record.pk])).status_code, 404)
        self.assertContains(self.client.get(reverse('stock:record', args=[self.item.pk, record.pk])), record.get_absolute_url())

    def test_common_datatables_search_sort_full_query_and_actions(self):
        Item.objects.bulk_create([Item(name=f'Elemento {i:02d}', item_type=Item.Type.EPP) for i in range(15)])
        receive_common_stock(self.other, data(20))
        receive_common_stock(self.item, data(3))
        result = self.client.get(reverse('stock:data'), {'search[value]': 'Elemento 14'}).json()
        self.assertEqual(result['recordsTotal'], 17)
        self.assertEqual(result['recordsFiltered'], 1)
        self.assertEqual(result['data'][0]['name'], 'Elemento 14')
        result = self.client.get(reverse('stock:data'), {'order[0][column]': 2, 'order[0][dir]': 'desc'}).json()
        self.assertEqual([row['quantity'] for row in result['data'][:2]], ['20', '3'])
        self.assertIn(reverse('stock:receive', args=[self.other.pk]), result['data'][0]['actions'])
        self.assertIn('data-coreui-toggle="dropdown"', result['data'][0]['actions'])
        self.assertEqual(self.client.post(reverse('stock:data'), {}).status_code, 405)


class CommonStockConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)

    def test_concurrent_receipts_create_one_position_and_keep_both_quantities(self):
        barrier = Barrier(2)
        item_id = self.item.pk
        def receive(quantity):
            close_old_connections()
            try:
                item = Item.objects.get(pk=item_id)
                barrier.wait(timeout=10)
                return receive_common_stock(item, data(quantity)).pk
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = list(executor.map(receive, [3, 5]))
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual(StockPosition.objects.filter(project=None, item=self.item).count(), 1)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 8)

    def test_concurrent_retry_does_not_duplicate_stock(self):
        barrier = Barrier(2)
        item_id, request = self.item.pk, data(5)
        def receive(_):
            close_old_connections()
            try:
                item = Item.objects.get(pk=item_id)
                barrier.wait(timeout=10)
                return receive_common_stock(item, request).pk
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = list(executor.map(receive, range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(StockRecord.objects.count(), 1)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 5)


class CommonStockMigrationTests(TransactionTestCase):
    def test_schema_transition_preserves_previous_ledger_and_totals(self):
        previous = [('inventory', '0002_remove_stockrecord_inventory_valid_operation_quantity_and_more')]
        current = [('inventory', '0003_alter_stockposition_project_and_more')]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            ProjectModel = apps.get_model('projects', 'Project')
            ItemModel = apps.get_model('catalog', 'Item')
            Position = apps.get_model('inventory', 'StockPosition')
            Record = apps.get_model('inventory', 'StockRecord')
            item = ItemModel.objects.create(name='Casco anterior', item_type='epp')
            for name, quantity in [('Norte', 10), ('Sur', 7)]:
                project = ProjectModel.objects.create(name=name)
                position = Position.objects.create(project=project, item=item)
                Record.objects.create(position=position, operation='opening', quantity=quantity,
                                      occurred_on=date(2026, 11, 12))
            before = list(Record.objects.order_by('pk').values())
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            self.assertEqual(list(StockRecord.objects.order_by('pk').values()), before)
            self.assertEqual(StockPosition.common_balance(item.pk), 17)
            self.assertEqual(StockPosition.objects.count(), 2)
        finally:
            MigrationExecutor(connection).migrate(current)
