# -*- coding: utf-8 -*-

from freezegun import freeze_time

from odoo.addons.l10n_es_reports.tests.common import TestEsAccountReportsCommon
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.tools import file_open


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBOEGeneration(TestEsAccountReportsCommon):
    """ Basic tests checking the generation of BOE files is still possible.
    """

    def _check_boe_111_to_303(self, modelo_number):
        self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today(), taxes=self.spanish_test_tax, post=True)
        report = self.env.ref('l10n_es.mod_%s' % modelo_number)
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, modelo_number)

    @freeze_time('2020-12-22')
    def test_boe_mod_111(self):
        self._check_boe_111_to_303('111')

    @freeze_time('2020-12-22')
    def test_boe_mod_115(self):
        self._check_boe_111_to_303('115')

    @freeze_time('2020-12-22')
    def test_boe_mod_130(self):
        self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today(), taxes=self.spanish_test_tax, post=True)
        report = self.env.ref('l10n_es.mod_130')
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 130)

        boe_file = self.env[report.custom_handler_model_name].export_boe(options)
        with file_open('l10n_es_reports/tests/data/mod_130_boe.txt', 'rb') as f:
            expected_content = f.read().replace(b'\n', b'')
        self.assertEqual(expected_content, boe_file['file_content'])

    @freeze_time('2020-12-22')
    def test_boe_mod_115_no_company_write_access_required(self):
        """
        Generating a mod 115 BOE file should not require write access on res.company.
        """
        self._create_invoice(
            partner_id=self.spanish_partner,
            invoice_date=fields.Date.today(),
            invoice_line_ids=[self._prepare_invoice_line(price_unit=10000, tax_ids=self.spanish_test_tax)],
            post=True,
        )
        report = self.env.ref('l10n_es.mod_115')
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))

        accountant = new_test_user(self.env, login='accountant_no_settings_access', groups='account.group_account_user')
        self.assertFalse(accountant.has_group('base.group_erp_manager'), "Test user should not have write access on res.company")

        wizard_model = self.env[report.custom_handler_model_name].with_user(accountant)
        wizard_action = wizard_model.open_boe_wizard(options, 115)
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).with_user(accountant).create({
            # Mimics the value the web client sends back on save, since the field is
            # present (albeit invisible) in the wizard view.
            'company_partner_id': self.env.company.partner_id.id,
        })
        options['l10n_es_reports_boe_wizard_id'] = wizard.id
        self.assertTrue(wizard_model.export_boe(options), "Empty BOE")

    @freeze_time('2020-12-22')
    def test_boe_mod_303(self):
        self._check_boe_111_to_303('303')

    @freeze_time('2020-12-22')
    def test_boe_mod_347(self):
        invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        invoice._post()
        spanish_partner_2 = self.env['res.partner'].create({
            # ES Partner with vat not starting with 'ES', should still be included in 347
            'name': 'Partner 2',
            'street': "Avenida de los Informes Financieros, 43",
            'zip': 4242,
            'city': "Madrid",
            'country_id': self.env.ref('base.es').id,
            'state_id': self.env.ref('base.state_es_m').id,
            'vat': '74280274A',
        })
        invoice_2 = self.init_invoice('out_invoice', partner=spanish_partner_2, amounts=[5000], invoice_date=fields.Date.today())
        invoice_2.action_post()
        invoice_3 = self.init_invoice('out_invoice', partner=spanish_partner_2, amounts=[4000], invoice_date=fields.Date.today())
        invoice_3.l10n_es_reports_mod347_invoice_type = 'insurance'
        invoice_3._post()
        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 347)

        # Check file content
        report._get_lines(options)
        handler = self.env[report.custom_handler_model_name]
        vals = handler.export_boe(options)
        expected = [
            # For information about data position, see page 7 & 16 of
            # https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_300_399/archivos/347.pdf
            # 1,347,year,company vat
            "13472020A12345674COMPANY_1_DATA                          T         BECAUSE I AM ACCOUNTMAN!                3470000000002  0000000000000000000002 000000001900000000000000 000000000000000                                                                                                                                                                                                                                                                                                                           ",
            # 2,347,year,company vat,partner vat
            "23472020A1234567474280274A         PARTNER 2                               D28   B 000000000400000X 000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000400000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
            "23472020A12345674A12345674         BERNARDO GANADOR                        D28   B 000000001000000  000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000001000000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
            "23472020A1234567474280274A         PARTNER 2                               D28   B 000000000500000  000000000000000 0000000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000000000 000000000500000 000000000000000                     000000000000000000000                                                                                                                                                                                                   ",
        ]
        for generated_line, expected_line in zip(vals['file_content'].decode('utf-8').splitlines(), expected):
            self.assertEqual(generated_line, expected_line)

        handler._retrieve_boe_manual_wizard(options, 347).write({
            'complementary_declaration': True,
            'substitutive_declaration': True,
        })
        vals = handler.export_boe(options)
        header_line = vals['file_content'].decode('utf-8').splitlines()[0]
        self.assertEqual('C', header_line[120], "Complementary declaration should use 'C'")
        self.assertEqual('S', header_line[121], "Substitutive declaration should use 'S'")

    @freeze_time('2020-12-22')
    def test_boe_mod_349(self):
        self.partner_a.write({
            'country_id': self.env.ref('base.be').id,
            'vat': "BE0477472701",
        })
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod349_invoice_type = 'E'
        invoice._post()
        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 349)

    @freeze_time('2020-12-22')
    def test_boe_mod_390(self):
        report = self.env.ref('l10n_es.mod_390')
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        self._check_boe_export(report, options, 390, additional_context={
            'default_physical_person_name': "Bernard Gagnant",
            'default_principal_activity': "Selling",
            'default_principal_iae_epigrafe': "EAAA",
            'default_principal_code_activity': "AAA",
            'default_judicial_person_name': "Bebert",
            'default_judicial_person_nif': "123",
            'default_judicial_person_procuration_date': '2020-01-01',
            'default_judicial_person_notary': "Maître Gagnant",
        })

    @freeze_time('2020-12-22')
    def test_boe_mod_347_with_cash_payment(self):
        cash_journal = self.env['account.journal'].create({
            'name': 'Cash Journal Test',
            'type': 'cash',
            'company_id': self.company_data['company'].id,
            'code': 'CASHBOE',
        })
        invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[1000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        invoice._post()
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 1000,
            'payment_date': invoice.date,
            'journal_id': cash_journal.id,
        })._create_payments()

        other_spanish_partner = self.env['res.partner'].create({
            'name': "Other Partner",
            'state_id': self.env.ref('base.state_es_m').id,
            'country_id': self.env.ref('base.es').id,
            'vat': "ESA12345674",
        })
        other_invoice = self.init_invoice('out_invoice', partner=other_spanish_partner, amounts=[4000], invoice_date=fields.Date.today())
        other_invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        other_invoice._post()
        self.env['account.payment.register'].with_context(active_ids=other_invoice.ids, active_model='account.move').create({
            'amount': 4000,
            'payment_date': other_invoice.date,
            'journal_id': cash_journal.id,
        })._create_payments()

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        wizard_model = self.env[report.custom_handler_model_name]
        wizard_action = wizard_model.open_boe_wizard(options, 347)
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_result = self.env[report.custom_handler_model_name].export_boe(options)
        self.assertTrue(self.spanish_partner.name.upper() not in boe_result['file_content'].decode())
        # Only the other partner is above the 3 005,06 € threshold must be reported
        self.assertIn(other_spanish_partner.name.upper(), boe_result['file_content'].decode())

    @freeze_time('2025-05-15')
    def test_boe_includes_null_lines_mod_349(self):
        """
        Test that the mod 349 boe report contains the rectification lines even when the total rectification sum to 0
        """
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-15')
        invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice.id,
            'active_id': invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',  # 'reason' can still be used to indicate purpose
            'journal_id': invoice.journal_id.id,
        })
        credit_note_wizard.modify_moves()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)

        # This string represents a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period,
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098
        self.assertIn('20250300000000000000000000100000', boe_file['file_content'].decode('utf-8'))
        # The header counts the rectification, of 0.00
        self.assertEqual(boe_file['file_content'].decode('utf-8')[137:185], '000000000000000000000000000000001000000000000000')

    @freeze_time('2025-05-15')
    def test_only_include_credit_note_in_rectification_mod_349(self):
        """
        Test that in model 349 only the credit notes are included in the computation of the rectification line
        """
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-15')
        invoice.action_post()

        reversal_wizard = self.env['account.move.reversal'].with_context({
            'active_ids': invoice.id,
            'active_id': invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'refund',
            'journal_id': invoice.journal_id.id,
        })
        reversal = reversal_wizard.reverse_moves()
        refund = self.env['account.move'].browse(reversal.get('res_id'))
        refund.line_ids.write({'price_unit': 500.0})
        refund.action_post()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 250.0,
        })._create_payments()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)

        # Those strings represent a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period,
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098

        # Here the new value should be 500 and not 250 because the payment should not count in the rectification line
        self.assertIn('20250300000000500000000000100000', boe_file['file_content'].decode('utf-8'))
        self.assertNotIn('20250300000000250000000000100000', boe_file['file_content'].decode('utf-8'))

    @freeze_time('2025-05-15')
    def test_mod349_rectification_header_unaffected_by_payment(self):
        """ Test that fully paying/reconciling the original invoice does not change the mod 349 rectification header
        """
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-15', post=True)
        self._reverse_mod349_move(invoice, 200.0, '2025-05-15')
        # Fully pay the remaining balance of the original invoice (residual becomes 0)
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 800.0,
        })._create_payments()

        boe = self._get_mod349_boe('2025-05-01', '2025-05-31')
        # Header: 1 rectification of 800.00
        # Content: 1000.00 declared in March, rectified to 800.00
        self.assertEqual(boe[137:185], '000000000000000000000000000000001000000000080000')
        self.assertIn('20250300000000800000000000100000', boe)

    @freeze_time('2025-05-20')
    def test_mod349_rectification_successive_credit_notes(self):
        """ Test that an invoice credited again in a later period is rectified from the amount last declared for its
            period, i.e. by the rectification of the intermediate period
        """
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-10', post=True)
        self._reverse_mod349_move(invoice, 500.0, '2025-04-10')
        self._reverse_mod349_move(invoice, 250.0, '2025-05-10')

        for date_from, date_to, expected_statistics, expected_record in (
            # 1000.00 declared in March, 500.00 after the credit note of April
            ('2025-04-01', '2025-04-30', '000000000000000000000000000000001000000000050000', '20250300000000500000000000100000'),
            # 250.00 after the credit note of May, from the 500.00 declared by the rectification of April
            ('2025-05-01', '2025-05-31', '000000000000000000000000000000001000000000025000', '20250300000000250000000000050000'),
        ):
            content = self._get_mod349_boe(date_from, date_to)
            self.assertEqual(content[137:185], expected_statistics)
            self.assertIn(expected_record, content)

    @freeze_time('2025-05-20')
    def test_mod349_rectification_credit_note_in_rectified_period(self):
        """ Test that the credit notes of the rectified period itself are part of the amount declared for it
        """
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-10', post=True)
        self._reverse_mod349_move(invoice, 200.0, '2025-03-20')
        self._reverse_mod349_move(invoice, 100.0, '2025-05-10')

        # 800.00 declared in March, 700.00 after the credit note of May
        content = self._get_mod349_boe('2025-05-01', '2025-05-31')
        self.assertEqual(content[137:185], '000000000000000000000000000000001000000000070000')
        self.assertIn('20250300000000700000000000080000', content)

    @freeze_time('2025-05-20')
    def test_mod349_rectification_credit_notes_on_other_invoices(self):
        """ Test that a period is rectified with all its operations when its invoices are credited in different
            periods, while the intermediate period itself is not rectified
        """
        invoice_1 = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[500], invoice_date='2025-03-10', post=True)
        invoice_2 = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-20', post=True)
        self._reverse_mod349_move(invoice_1, 250.0, '2025-04-10')
        self._reverse_mod349_move(invoice_2, 400.0, '2025-05-10')

        # Only March is rectified in May: 1250.00 declared by the rectification of April, 850.00 after the credit note of May
        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        self.assertEqual(self.env['l10n_es.mod349.tax.report.handler']._get_modelo349_rectifications(options), {
            'E': {self.mod349_partner.id: {'032025': {'old_balance': 1250.0, 'new_balance': 850.0}}},
        })

        content = self._get_mod349_boe('2025-05-01', '2025-05-31')
        self.assertEqual(content[137:185], '000000000000000000000000000000001000000000085000')
        self.assertIn('20250300000000850000000000125000', content)
        self.assertNotIn('E' + ' ' * 13 + '202504', content)

    @freeze_time('2025-05-20')
    def test_mod349_credit_notes_same_and_previous_period(self):
        """ Test that the credit notes of invoices of the same period are netted with the operations of the period,
            and that only the ones of invoices of a previous period correct the amounts declared before
        """
        # Entirely refunded in the same period: nothing to declare
        invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-05-05', post=True)
        self._reverse_mod349_move(invoice, 1000.0, '2025-05-10')
        # Partially refunded in the same period: the remaining 200.00 is declared as an operation
        partially_refunded_partner = self.mod349_partner.copy({'name': 'Test 2'})
        invoice = self.init_invoice('out_invoice', partner=partially_refunded_partner, amounts=[1000], invoice_date='2025-05-05', post=True)
        self._reverse_mod349_move(invoice, 800.0, '2025-05-10')
        # Refunded in a later period: the 500.00 declared in March is rectified to 400.00
        rectified_partner = self.mod349_partner.copy({'name': 'Test 3'})
        invoice = self.init_invoice('out_invoice', partner=rectified_partner, amounts=[500], invoice_date='2025-03-10', post=True)
        self._reverse_mod349_move(invoice, 100.0, '2025-05-10')

        content = self._get_mod349_boe('2025-05-01', '2025-05-31')
        self.assertEqual(self._extract_mod349_boe_records(content), {
            ('TEST 2', 'E', 200.0),
            ('TEST 3', 'E', '202503', 400.0, 500.0),
        })
        # Header: 1 operator for 200.00, 1 rectification of 400.00
        self.assertEqual(content[137:185], '000000001000000000020000000000001000000000040000')

    @freeze_time('2025-06-20')
    def test_mod349_rectifications_per_operator_and_key(self):
        """ Test that the rectifications restate each operator, key and period separately, even when the
            operations of other operators, keys or periods are dated in between
        """
        other_partner = self.mod349_partner.copy({'name': 'Test 2'})

        # March
        invoice_a = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-05', post=True)
        invoice_b = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[500], invoice_date='2025-03-10', post=True)
        invoice_services = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[300], invoice_date='2025-03-15')
        invoice_services.l10n_es_reports_mod349_invoice_type = 'S'
        invoice_services.action_post()
        self.init_invoice('out_invoice', partner=other_partner, amounts=[700], invoice_date='2025-03-20', post=True)
        bill = self.init_invoice('in_invoice', partner=self.mod349_partner, amounts=[400], invoice_date='2025-03-25', post=True)
        # April
        self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[200], invoice_date='2025-04-05', post=True)
        invoice_other_services = self.init_invoice('out_invoice', partner=other_partner, amounts=[600], invoice_date='2025-04-10')
        invoice_other_services.l10n_es_reports_mod349_invoice_type = 'S'
        invoice_other_services.action_post()
        self._reverse_mod349_move(invoice_a, 100.0, '2025-04-15')
        # May
        self._reverse_mod349_move(invoice_services, 50.0, '2025-05-05')
        self._reverse_mod349_move(invoice_other_services, 200.0, '2025-05-10')
        self._reverse_mod349_move(bill, 100.0, '2025-05-15')
        # June
        self._reverse_mod349_move(invoice_b, 50.0, '2025-06-05')

        for date_from, date_to, expected_statistics, expected_records in (
            # Operations of April, March E of the partner rectified by the credit note of April
            ('2025-04-01', '2025-04-30', '000000002000000000080000000000001000000000140000', {
                ('TEST', 'E', 200.0),
                ('TEST 2', 'S', 600.0),
                ('TEST', 'E', '202503', 1400.0, 1500.0),
            }),
            # No operation in May, rectifications of March S and A of the partner and April S of the other partner
            ('2025-05-01', '2025-05-31', '000000000000000000000000000000003000000000095000', {
                ('TEST', 'S', '202503', 250.0, 300.0),
                ('TEST', 'A', '202503', 300.0, 400.0),
                ('TEST 2', 'S', '202504', 400.0, 600.0),
            }),
            # March E of the partner rectified again by the credit note of June, from the 1400.00 declared in April
            ('2025-06-01', '2025-06-30', '000000000000000000000000000000001000000000135000', {
                ('TEST', 'E', '202503', 1350.0, 1400.0),
            }),
        ):
            with self.subTest(date_from=date_from):
                content = self._get_mod349_boe(date_from, date_to)
                self.assertEqual(self._extract_mod349_boe_records(content), expected_records)
                self.assertEqual(content[137:185], expected_statistics)

    @freeze_time('2025-05-15')
    def test_boe_excludes_current_period_rectification_lines(self):
        """
        Test that moves from the current period are not included as rectification lines in the boe report
        """
        previous_period_invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-03-15')
        previous_period_invoice.action_post()

        credit_note_wizard_previous = self.env['account.move.reversal'].with_context({
            'active_ids': previous_period_invoice.id,
            'active_id': previous_period_invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',
            'journal_id': previous_period_invoice.journal_id.id,
        })
        credit_note_wizard_previous.reverse_moves()

        current_period_invoice = self.init_invoice('out_invoice', partner=self.mod349_partner, amounts=[1000], invoice_date='2025-05-15')
        current_period_invoice.action_post()

        credit_note_wizard_current = self.env['account.move.reversal'].with_context({
            'active_ids': current_period_invoice.id,
            'active_id': current_period_invoice.id,
            'active_model': 'account.move',
        }).create({
            'reason': 'modify',
            'journal_id': current_period_invoice.journal_id.id,
        })
        credit_note_wizard_current.reverse_moves()

        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string('2025-05-01'), fields.Date.from_string('2025-05-31'))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id

        boe_file = self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)
        # This string represents a rectification record included in the BOE export.
        # It contains:
        # - the year (2025),
        # - the period (here 5 which is the current period),
        # - the rectified tax base (0.00),
        # - and the previously declared tax base (1000.00).
        # Under REGISTRO DE RECTIFICACIONES https://www.boe.es/buscar/doc.php?id=BOE-A-2010-5098
        self.assertNotIn('20250500000000000000000000100000', boe_file['file_content'].decode('utf-8'))

    @freeze_time('2020-12-22')
    def test_boe_button_branch_allowed(self):
        """
        Test when a parent company has branches with different VATs and not all
        branches are in the company selector
        """
        parent_company = self.company_data['company']
        self.env['res.company'].create({
            'name': 'ES Branch',
            'parent_id': parent_company.id,
            'vat': 'B88431804',
            'country_id': self.env.ref('base.es').id,
        })
        report = self.env.ref('l10n_es.mod_390').with_context(
            allowed_company_ids=parent_company.ids,
        )
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        boe_button = next(b for b in options['buttons'] if b.get('action_param') == 390)
        action = boe_button.get('error_action') or boe_button['action']
        wizard_action = report.dispatch_report_action(options, action, boe_button['action_param'])
        self.assertEqual(
            'l10n_es_reports.aeat.boe.mod390.export.wizard',
            wizard_action['res_model'],
        )
