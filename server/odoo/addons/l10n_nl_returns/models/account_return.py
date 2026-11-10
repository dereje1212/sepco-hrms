from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountReturn(models.Model):
    _inherit = 'account.return'

    l10n_nl_sbr_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('error', 'Error'),
        ],
        string='SBR Status',
        help='Tracks SBR submission status for Kanban UI color coding.',
    )

    @api.depends('state', 'l10n_nl_sbr_status')
    def _compute_visible_states(self):
        super()._compute_visible_states()
        for account_return in self.filtered(lambda x: x.type_external_id in (
            'l10n_nl_reports.nl_tax_return_type', 'l10n_nl_reports.nl_ec_sales_list_return_type',
        )):
            new_states = []
            for state in account_return.visible_states:
                state['custom_class'] = ''
                if (
                    state['name'] == 'submitted'
                    and account_return.state == 'submitted'
                    and account_return.l10n_nl_sbr_status != 'accepted'
                ):
                    state['custom_class'] = f'nl-sbr-{account_return.l10n_nl_sbr_status}'
                new_states.append(state)
            account_return.visible_states = new_states

    @api.depends('next_state', 'state', 'l10n_nl_sbr_status')
    def _compute_show_submit_button(self):
        super()._compute_show_submit_button()
        for account_return in self.filtered(lambda x: x.type_external_id in (
            'l10n_nl_reports.nl_tax_return_type', 'l10n_nl_reports.nl_ec_sales_list_return_type',
        )):
            account_return.show_submit_button = (
                account_return.show_submit_button
                or account_return.state == 'submitted' and account_return.l10n_nl_sbr_status == 'error'
            )

    def action_refresh_sbr_status(self):
        self.ensure_one()
        if self.l10n_nl_sbr_status == 'pending':
            status_service = self.env['l10n_nl_reports.sbr.status.service'].search([
                '|',
                ('closing_entry_id.closing_return_id', '=', self.id),
                ('kenmerk', '=like', f'%:%:%:{self.id}'),
            ], order='id desc', limit=1)
            if not status_service:
                bodies = self.env['mail.message'].search([
                    ('model', '=', self._name),
                    ('res_id', '=', self.id),
                    ('author_id', '=', self.env.ref('base.partner_root').id),
                    ('body', '!=', False),
                ]).mapped('body')
                if bodies:
                    status_service = self.env['l10n_nl_reports.sbr.status.service'].search([
                        ('closing_entry_id', '=', False),
                        ('kenmerk', 'not like', '%:%:%:%'),
                    ], order='id desc').filtered(
                        lambda service: (reference := service._get_submission_data()[0])
                        and any(reference in body for body in bodies)
                    )[:1]
            status_service.is_done = False
        self.env['l10n_nl_reports.sbr.status.service']._cron_process_submission_status()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reset_tax_return_common(self):
        if self.type_external_id == 'l10n_nl_reports.nl_tax_return_type' and self.l10n_nl_sbr_status == 'accepted':
            raise UserError(
                self.env._("This tax return has already been accepted by Digipoort and cannot be modified or reset.")
            )
        return super().action_reset_tax_return_common()

    def action_reset_2_states(self):
        if self.type_external_id == 'l10n_nl_reports.nl_ec_sales_list_return_type' and self.l10n_nl_sbr_status == 'accepted':
            raise UserError(
                self.env._("This sales return has already been accepted by Digipoort and cannot be modified or reset.")
            )
        return super().action_reset_2_states()

    def _on_post_submission_event(self):
        # Don't process anything until the return has been accepted by the SBR.
        if self.type_external_id == 'l10n_nl_reports.nl_tax_return_type' and self.l10n_nl_sbr_status != 'accepted':
            return
        return super()._on_post_submission_event()
