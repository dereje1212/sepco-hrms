import base64

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('sepa', 'SEPA'), ('iso20022_ch', 'Swiss ISO20022')], default='sepa', ondelete={'sepa': 'set csv', 'iso20022_ch': 'set csv'})
    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def _create_sepa_binary(self):
        # Map the necessary data
        payments_data = []
        latest_payslip_date = None
        batch_id = None
        for slip in self.payslip_ids.filtered(lambda p: p.state == "validated" and p.net_wage > 0):
            payments_data.extend(slip._get_payments_vals(self.journal_id, self.effective_date))
            batch_id = slip.id
            if latest_payslip_date is None or slip.date > latest_payslip_date:
                latest_payslip_date = slip.date
        payment_method_code = self.env.context.get('payment_method') or 'sepa_ct'

        # Generate XML File
        xml_doc = self.journal_id.sudo().with_context(
            sepa_payroll_sala=True,
            l10n_be_hr_payroll_sepa_salary_payment=self.journal_id.company_id.account_fiscal_country_id.code == "BE"
        ).create_iso20022_credit_transfer(payments=payments_data, payment_method_code=payment_method_code, batch_booking=True)
        if self.payslip_run_id:
            batch_id = self.payslip_run_id.id
        if not latest_payslip_date:
            latest_payslip_date = fields.Date.today()
        latest_payslip_date_str = latest_payslip_date.strftime('%Y_%m_%d')
        return base64.encodebytes(xml_doc), f"{latest_payslip_date_str}_{batch_id}"

    def _perform_checks(self):
        super()._perform_checks()
        if self.export_format in ['sepa', 'iso20022_ch']:
            if self.effective_date < fields.Date.today():
                raise ValidationError(_("The payment date cannot be in the past."))
            employees = self.payslip_ids.employee_id.filtered(lambda e: not e.work_contact_id)
            if employees:
                raise UserError(_("Some employees (%s) don't have a work contact.", employees.mapped('name')))
            employees = self.payslip_ids.employee_id.filtered(lambda e: e.work_contact_id and not e.work_contact_id.name)
            if employees:
                raise UserError(_(
                    "Some employees (%s) don't have a valid name on the work contact.",
                    employees.mapped('name')))
            if self.journal_id.bank_account_id.acc_type != 'iban':
                raise UserError(_(
                    "The journal '%s' requires a proper IBAN account to pay via SEPA. "
                    "Please configure it first.",
                    self.journal_id.name))

    def generate_payment_report(self):
        super().generate_payment_report()
        if self.export_format in ['sepa', 'iso20022_ch']:
            if self.export_format == 'sepa':
                payment_report, filename = self.with_context(payment_method='sepa_ct')._create_sepa_binary()
            elif self.export_format == 'iso20022_ch':
                payment_report, filename = self.with_context(payment_method='iso20022_ch')._create_sepa_binary()
            self._write_file(payment_report, '.xml', filename)
