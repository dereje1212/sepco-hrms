from odoo import fields

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

class TestEsAccountReportsCommon(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        cls.spanish_partner = cls.env['res.partner'].create({
            'name': "Bernardo Ganador",
            'street': "Avenida de los Informes Financieros, 42",
            'zip': 4242,
            'city': "Madrid",
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_m').id,
            'vat': "ESA12345674",
        })

        cls.mod349_partner = cls.env['res.partner'].create({
            'name': 'Test',
            'company_id': cls.company_data['company'].id,
            'company_type': 'company',
            'country_id': cls.env['res.country'].search([('code', '=', 'BE')]).id,
            'vat': 'BE0477472701',
        })

        base_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_01_balance')
        )._get_matching_tags()
        base_refund_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_14_aeat_mod_303_14_sale_balance')
        )._get_matching_tags()
        tax_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_03_balance')
        )._get_matching_tags()
        tax_refund_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_15_balance')
        )._get_matching_tags()

        cls.spanish_test_tax = cls.env['account.tax'].create({
            'name': "Test ES BOE tax",
            'amount_type': 'percent',
            'amount': 42,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': base_tags.ids,
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': tax_tags.ids,
                })
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': base_refund_tags.ids,
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': tax_refund_tags.ids,
                })
            ],
        })

        cls.env.company.vat = "ESA12345674"

    def _check_boe_export(self, report, options, modelo_number, additional_context=None):
        wizard_model = self.env[report.custom_handler_model_name]
        if additional_context:
            wizard_model = wizard_model.with_context(**additional_context)
        wizard_action = wizard_model.open_boe_wizard(options, modelo_number)
        self.assertEqual(f'l10n_es_reports.aeat.boe.mod{modelo_number}.export.wizard', wizard_action['res_model'], "Wrong BOE export wizard returned")
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id
        self.assertTrue(self.env[report.custom_handler_model_name].export_boe(options), "Empty BOE")

    def _reverse_mod349_move(self, move, amount, date):
        reversal = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=move.ids).create({
            'reason': 'rectification',
            'date': date,
            'journal_id': move.journal_id.id,
        }).reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        reversed_move.invoice_line_ids.price_unit = amount
        # The credit note is given the key of the rectified operation
        reversed_move.l10n_es_reports_mod349_invoice_type = move.l10n_es_reports_mod349_invoice_type
        reversed_move.action_post()
        return reversed_move

    def _get_mod349_boe(self, date_from, date_to):
        report = self.env.ref('l10n_es_reports.mod_349')
        options = self._generate_options(report, fields.Date.from_string(date_from), fields.Date.from_string(date_to))
        wizard_action = self.env['l10n_es.mod349.tax.report.handler'].open_boe_wizard(options, '349')
        options['l10n_es_reports_boe_wizard_id'] = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({}).id
        return self.env['l10n_es.mod349.tax.report.handler'].export_boe(options)['file_content'].decode('utf-8')

    def _extract_mod349_boe_records(self, content):
        """ Extract the type 2 records of a mod 349 BOE file, as a set of:
            - (name, key, amount) for an operator
            - (name, key, rectified period, rectified amount, previously declared amount) for a rectification
        """
        records = set()
        for record in content.split('\r\n')[1:]:
            if not record.strip():
                continue
            name, key = record[92:132].strip(), record[132]
            if record[146:178].strip():
                records.add((name, key, record[146:152], int(record[152:165]) / 100, int(record[165:178]) / 100))
            else:
                records.add((name, key, int(record[133:146]) / 100))
        return records
