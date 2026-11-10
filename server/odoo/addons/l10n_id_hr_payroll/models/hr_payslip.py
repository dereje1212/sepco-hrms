# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import date, timedelta

KODE_PTKP_MAPPING = {
    'tk0': 'a',
    'tk1': 'a',
    'k0': 'a',
    'tk2': 'b',
    'tk3': 'b',
    'k1': 'b',
    'k2': 'b',
    'k3': 'c',
}


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_id_include_jkk_jkm = fields.Boolean(default=True)  # jkk jkm jht jp
    l10n_id_include_bpjs_kesehatan = fields.Boolean(default=True)  # bpjs kesehatan + its deduction
    l10n_id_include_pkp_ptkp = fields.Boolean(
        compute="_compute_l10n_id_include_pkp_ptkp", store=True, readonly=False)  # include the PTKP/PKP computation

    def _l10n_id_get_historical_payslips(self):
        """ Get the validated payslips of the employee within the year, before the current payslip"""
        date_start = date(self.date_to.year, 1, 1)
        return self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_to', '>=', date_start),
            ('date_to', '<', self.date_to),
            ('state', 'in', ['validated', 'paid'])
        ])

    def _l10n_id_get_historical_categorical_total(self, codes):
        """ Get the total amount of specific category among the contract's taxes history that has been validated
        within a certain year"""
        payslips = self._l10n_id_get_historical_payslips()
        vals = payslips._get_line_values(codes, compute_sum=True)
        return sum(vals[code]['sum']['total'] for code in codes)

    def _l10n_id_get_months_count(self):
        """ Get the number of months of the year with a payslip, including the current payslip"""
        payslips = self._l10n_id_get_historical_payslips()
        return len({slip.date_to.month for slip in payslips} | {self.date_to.month})

    def _l10n_id_get_pph21_amount(self, amount):
        """ Find the right percentage to apply depending on the GROSS amount of the payslip"""
        category_type = KODE_PTKP_MAPPING[self.employee_id.l10n_id_kode_ptkp]

        ranges = self._rule_parameter('l10n_id_pph21_percentage_' + category_type)
        for line in ranges:
            if amount < line[1]:
                return line[2]

    def _l10n_id_get_worked_days_rate(self):
        """Total number of worked days (incl leaves except out of contract)/total number of days
        value is returned between 0 to 1"""
        total_days = sum(self.worked_days_line_ids.mapped('number_of_days'))
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code != 'OUT')
        number_of_days = sum(wds.mapped('number_of_days'))
        return number_of_days / total_days

    def _l10n_id_get_end_total_pph_amount(self):
        """ Getting the accumulated PPH21 amount over the course of a year (from start of year/contract)"""
        return self._l10n_id_get_historical_categorical_total(['PPH21'])

    def _l10n_id_get_gross_accumulated(self):
        # deprecated, not used anymore, TODO: remove in master
        payslips = self._l10n_id_get_historical_payslips()
        vals = payslips._get_line_values(['GROSS'])['GROSS']
        gross_lines = [vals[i]['total'] for i in payslips.ids]

        sum_gross = 0
        threshold = self._rule_parameter('l10n_id_biaya_jabatan_salary_threshold')
        percent = self._rule_parameter('l10n_id_biaya_jabatan_percent')
        for line in gross_lines:
            amount = min(line, threshold)
            sum_gross += (percent / 100) * amount

        return sum_gross

    def _l10n_id_get_total_gross(self):
        """ Get the total GROSS accumulated before the current payslip"""
        return self._l10n_id_get_historical_categorical_total(['GROSS'])

    @api.depends('date_from', 'date_to', 'version_id.contract_date_start', 'version_id.contract_date_end')
    def _compute_l10n_id_include_pkp_ptkp(self):
        """ by default, set to True on the last payslip of the year/contract only:
        - end of year: the next payslip, of the same duration, would end in the next year
        - end of contract: the end date of the contract is within the payslip period
        """
        for slip in self:
            if not slip.date_from or not slip.date_to:
                slip.l10n_id_include_pkp_ptkp = False
                continue
            next_date_to = slip.date_to + (slip.date_to - slip.date_from) + timedelta(days=1)
            date_end = slip.version_id.contract_date_end
            slip.l10n_id_include_pkp_ptkp = (
                next_date_to.year > slip.date_to.year or
                bool(date_end and slip.date_from <= date_end <= slip.date_to)
            )

    def _get_data_files_to_update(self):
        return super()._get_data_files_to_update() + [(
            'l10n_id_hr_payroll', [
                'data/hr_rule_parameter_data.xml',
                'data/hr_salary_rule_data.xml',
            ])]
