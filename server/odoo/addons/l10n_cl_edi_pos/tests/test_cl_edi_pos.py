from freezegun import freeze_time

from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_cl_edi.tests.common import TestL10nClEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCL(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('cl')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.name = 'Company CL'


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestCLEdiPos(TestL10nClEdiCommon, TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.cl').id,
        })
        cls.config = cls.basic_config

    def test_cl_pos_refund_reference_date(self):
        with freeze_time('2024-01-10 12:00:00'):
            self.open_new_session(0.0)
            product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
            order_data = self.create_ui_order_data([(product1, 1)], customer=self.partner_sii, is_invoiced=True)
            result = self.env['pos.order'].sync_from_ui([order_data])
            order = self.env['pos.order'].browse(result['pos.order'][0]['id'])

        with freeze_time('2024-01-17 12:00:00'):
            refund_order = order._refund()
            credit_note = refund_order._create_invoice(refund_order._prepare_invoice_vals())

        self.assertEqual(credit_note.l10n_cl_reference_ids.date, order.account_move.invoice_date)
