import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project

from .models import StockPosition, StockRecord
from .services import correct_record, open_stock, receive_stock


def record_data(quantity=10, **overrides):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12),
            'observation': '', 'submission_key': uuid.uuid4(), **overrides}


class InventoryFlowTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Obra Norte')
        self.other = Project.objects.create(name='Obra Sur')
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)

    def url(self, name, *extra, project=None, item=None):
        args = [(project or self.project).pk]
        if name != 'list':
            args.append((item or self.item).pk)
        return reverse(f'inventory:{name}', args=[*args, *extra])

    def test_postgresql_and_project_inventory_link(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.assertContains(self.client.get(self.project.get_absolute_url()), reverse('requests:list', args=[self.project.pk]))

    def test_project_inventory_no_longer_requires_a_project_opening(self):
        response = self.client.get(self.url('list'))
        self.assertContains(response, 'Solicitar elemento')
        self.assertNotContains(response, 'Sin registro inicial')
        self.assertEqual(self.client.get(reverse('stock:data')).json()['data'][0]['quantity'], '0')
        self.assertFalse(StockRecord.objects.exists())

    def test_initial_and_receipt_for_two_projects_remain_independent(self):
        for project, initial, receipt, total in [(self.project, 10, 5, 15), (self.other, 4, 2, 6)]:
            opening = open_stock(project, self.item, record_data(initial))
            receive_stock(project, self.item, record_data(receipt))
            self.assertEqual(opening.position.balance, total)
        self.assertEqual(Item.objects.count(), 1)
        self.assertEqual(StockPosition.objects.count(), 2)

    def test_duplicate_opening_is_rejected(self):
        open_stock(self.project, self.item, record_data())
        with self.assertRaisesMessage(ValidationError, 'ya tiene una apertura'):
            open_stock(self.project, self.item, record_data(20))
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_receipt_requires_initial_count(self):
        with self.assertRaisesMessage(ValidationError, 'Registra primero'):
            receive_stock(self.project, self.item, record_data(5))
        self.assertFalse(StockPosition.objects.exists())
        response = self.client.post(self.url('receive'), record_data(5))
        self.assertContains(response, 'Registra primero la existencia inicial')
        self.assertFalse(StockRecord.objects.exists())

    def test_open_and_receive_through_forms_and_reload(self):
        for operation, quantity in [('open', 10), ('receive', 5)]:
            response = self.client.post(self.url(operation), record_data(quantity))
            self.assertEqual(response.status_code, 302)
            self.assertContains(self.client.get(response.url), 'Stock disponible')
        history = Client().get(self.url('history'))
        self.assertContains(history, 'data-testid="balance">15</p>')
        self.assertNotContains(history, 'Registrado por:')
        self.assertContains(history, 'Fecha de registro:')

    def test_insufficient_balance_error_belongs_to_quantity_and_rolls_back(self):
        opening = open_stock(self.project, self.item, record_data(10))
        response = self.client.post(self.url('deliver'), record_data(11, worker_full_name='Ana Pérez'))
        self.assertFormError(response.context['form'], 'quantity', 'La cantidad supera el saldo disponible del proyecto. No se registró la entrega.')
        self.assertEqual(response.context['form'].non_field_errors(), [])
        self.assertEqual(response.context['form'].fields['quantity'].widget.attrs['aria-describedby'], 'id_quantity_errors')
        self.assertContains(response, 'class="invalid-feedback" id="id_quantity_errors"')
        self.assertNotContains(response, 'alert-danger')
        self.assertNotContains(response, 'Registrado por:')
        self.assertEqual(opening.position.balance, 10)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_zero_opening_and_positive_receipt(self):
        self.assertEqual(self.client.post(self.url('open'), record_data(0)).status_code, 302)
        self.assertEqual(self.client.post(self.url('receive'), record_data(1)).status_code, 302)
        self.assertEqual(StockPosition.objects.get().balance, 1)

    def test_invalid_initial_quantities_do_not_create_positions(self):
        for quantity in [-1, '1.5', '', 'abc', 9223372036854775808]:
            with self.subTest(quantity=quantity):
                response = self.client.post(self.url('open'), record_data(quantity, observation='Conservar'))
                self.assertEqual(response.status_code, 200)
                self.assertIn('quantity', response.context['form'].errors)
                self.assertContains(response, 'Conservar')
        self.assertFalse(StockPosition.objects.exists())

    def test_receipt_zero_and_negative_are_rejected(self):
        open_stock(self.project, self.item, record_data(0))
        for quantity in [0, -1, '2.5']:
            response = self.client.post(self.url('receive'), record_data(quantity))
            self.assertIn('quantity', response.context['form'].errors)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_date_is_required_and_valid(self):
        for value in ['', '2026-02-30', 'ayer']:
            response = self.client.post(self.url('open'), record_data(occurred_on=value))
            self.assertIn('occurred_on', response.context['form'].errors)
        self.assertFalse(StockPosition.objects.exists())

    def test_correction_of_opening_keeps_original_and_existing_receipt(self):
        original = open_stock(self.project, self.item, record_data(10, observation='Conteo original'))
        receive_stock(self.project, self.item, record_data(5))
        corrected = correct_record(self.project, original.pk, record_data(8, reason='Error al contar'))
        original.refresh_from_db()
        self.assertEqual(original.quantity, 10)
        self.assertEqual(original.observation, 'Conteo original')
        self.assertIsNotNone(original.voided_at)
        self.assertEqual(original.void_reason, 'Error al contar')
        self.assertEqual(corrected.replaces_id, original.pk)
        self.assertEqual(corrected.operation, StockRecord.Operation.OPENING)
        self.assertEqual(original.position.balance, 13)
        history = self.client.get(self.url('history'))
        for text in ['Anulado', 'Error al contar', 'Ver reemplazo', 'registro anterior']:
            self.assertContains(history, text)

    def test_correction_of_receipt_through_form(self):
        open_stock(self.project, self.item, record_data(10))
        original = receive_stock(self.project, self.item, record_data(5))
        response = self.client.post(self.url('correct', original.pk), record_data(2, reason='Recepción contada mal'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(original.position.balance, 12)
        self.assertEqual(StockRecord.objects.get(replaces=original).quantity, 2)

    def test_correction_requires_reason_and_preserves_values(self):
        original = open_stock(self.project, self.item, record_data())
        response = self.client.post(self.url('correct', original.pk), record_data(8, reason='   ', observation='Conservar'))
        self.assertIn('reason', response.context['form'].errors)
        self.assertContains(response, 'Conservar')
        original.refresh_from_db()
        self.assertIsNone(original.voided_at)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_failed_correction_rolls_back_annulment(self):
        original = open_stock(self.project, self.item, record_data())
        with self.assertRaises(ValidationError):
            correct_record(self.project, original.pk, record_data(-1, reason='Error'))
        original.refresh_from_db()
        self.assertIsNone(original.voided_at)
        self.assertEqual(original.void_reason, '')
        self.assertEqual(StockRecord.objects.count(), 1)
        self.assertEqual(original.position.balance, 10)

    def test_repeated_corrections_form_a_chain(self):
        original = open_stock(self.project, self.item, record_data(10))
        first = correct_record(self.project, original.pk, record_data(8, reason='Primer conteo'))
        last = correct_record(self.project, first.pk, record_data(7, reason='Revisión'))
        self.assertEqual(last.replaces_id, first.pk)
        self.assertEqual(last.position.balance, 7)
        self.assertEqual(last.position.records.filter(voided_at__isnull=True).count(), 1)
        with self.assertRaisesMessage(ValidationError, 'ya fue corregido'):
            correct_record(self.project, original.pk, record_data(4, reason='Formulario antiguo'))

    def test_double_submissions_do_not_duplicate_records(self):
        initial_data = record_data(10)
        opening = open_stock(self.project, self.item, initial_data)
        self.assertEqual(open_stock(self.project, self.item, initial_data).pk, opening.pk)
        receipt_data = record_data(5)
        receipt = receive_stock(self.project, self.item, receipt_data)
        self.assertEqual(receive_stock(self.project, self.item, receipt_data).pk, receipt.pk)
        correction_data = record_data(2, reason='Corrección')
        replacement = correct_record(self.project, receipt.pk, correction_data)
        self.assertEqual(correct_record(self.project, receipt.pk, correction_data).pk, replacement.pk)
        self.assertEqual(StockRecord.objects.count(), 3)
        self.assertEqual(opening.position.balance, 12)

    def test_submission_key_cannot_be_reused_for_different_data(self):
        data = record_data(10)
        opening = open_stock(self.project, self.item, data)
        with self.assertRaises(ValidationError):
            receive_stock(self.project, self.item, {**data, 'quantity': 3})
        self.assertEqual(opening.position.balance, 10)

    def test_missing_submission_key_does_not_write(self):
        data = record_data()
        data.pop('submission_key')
        response = self.client.post(self.url('open'), data)
        self.assertIn('submission_key', response.context['form'].errors)
        self.assertFalse(StockPosition.objects.exists())

    def test_reused_correction_form_does_not_silently_change_reason(self):
        original = open_stock(self.project, self.item, record_data(10))
        data = record_data(8, reason='Motivo original')
        correct_record(self.project, original.pk, data)
        with self.assertRaises(ValidationError):
            correct_record(self.project, original.pk, {**data, 'reason': 'Otro motivo'})
        original.refresh_from_db()
        self.assertEqual(original.void_reason, 'Motivo original')
        self.assertEqual(StockRecord.objects.count(), 2)

    def test_record_cannot_be_corrected_from_another_project_or_item(self):
        original = open_stock(self.project, self.item, record_data())
        other_item = Item.objects.create(name='Señal', item_type=Item.Type.SIGNAGE)
        for url in [self.url('correct', original.pk, project=self.other), self.url('correct', original.pk, item=other_item)]:
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, record_data(2, reason='Error')).status_code, 404)
        self.assertEqual(original.position.balance, 10)

    def test_unknown_project_and_item_are_404(self):
        for url in [reverse('inventory:list', args=[99999]), reverse('inventory:history', args=[self.project.pk, 99999])]:
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_csrf_required_for_all_writes(self):
        original = open_stock(self.project, self.item, record_data())
        client = Client(enforce_csrf_checks=True)
        for url in [self.url('open'), self.url('receive'), self.url('correct', original.pk)]:
            self.assertEqual(client.post(url, record_data(reason='Error')).status_code, 403)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_history_escapes_observations_and_reasons(self):
        original = open_stock(self.project, self.item, record_data(observation='<script>alert(1)</script>'))
        correct_record(self.project, original.pk, record_data(8, reason='<img src=x onerror=alert(1)>'))
        response = self.client.get(self.url('history'))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, '<img src=x')
        self.assertContains(response, '&lt;script&gt;')

    def test_database_constraints_reject_invalid_quantities_and_duplicate_opening(self):
        opening = open_stock(self.project, self.item, record_data())
        for operation, quantity in [('opening', -1), ('receipt', 0), ('other', 3), ('opening', 5)]:
            with self.subTest(operation=operation, quantity=quantity):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    StockRecord.objects.create(position=opening.position, operation=operation,
                                               quantity=quantity, occurred_on=date.today())


class InventoryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Proyecto concurrente')
        self.item = Item.objects.create(name='Casco compartido', item_type=Item.Type.EPP)

    def run_concurrently(self, actions):
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action().pk
                except ValidationError:
                    return 'rejected'
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_two_openings_create_only_one_initial_count(self):
        results = self.run_concurrently([
            lambda: open_stock(self.project, self.item, record_data(10)),
            lambda: open_stock(self.project, self.item, record_data(20)),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(StockPosition.objects.count(), 1)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_parallel_receipts_do_not_lose_quantities(self):
        opening = open_stock(self.project, self.item, record_data(10))
        self.run_concurrently([
            lambda: receive_stock(self.project, self.item, record_data(5)),
            lambda: receive_stock(self.project, self.item, record_data(2)),
        ])
        self.assertEqual(opening.position.balance, 17)

    def test_two_corrections_cannot_replace_the_same_record_twice(self):
        original = open_stock(self.project, self.item, record_data(10))
        results = self.run_concurrently([
            lambda: correct_record(self.project, original.pk, record_data(8, reason='Primera')),
            lambda: correct_record(self.project, original.pk, record_data(7, reason='Segunda')),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(StockRecord.objects.filter(replaces=original).count(), 1)
        self.assertEqual(StockRecord.objects.filter(voided_at__isnull=True).count(), 1)
