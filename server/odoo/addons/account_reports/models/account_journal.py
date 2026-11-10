from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_tax_return_journal = fields.Boolean(
        compute='_compute_is_tax_return_journal',
    )

    @api.depends('company_id')
    def _compute_is_tax_return_journal(self):
        for journal in self:
            journal.is_tax_return_journal = journal == journal.company_id.account_tax_return_journal_id
