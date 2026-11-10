from odoo import models
from odoo.exceptions import UserError

from odoo.addons.account_reports.models.account_report import AccountReportFileDownloadException


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _generate_locking_attachments(self, options):
        # Extends account_reports
        super()._generate_locking_attachments(options)
        if self.type_external_id == 'l10n_ma_reports.ma_tax_return_type':
            try:
                file_data = self.type_id.report_id.dispatch_report_action(options, 'l10n_ma_reports_export_vat_to_xml')
            except AccountReportFileDownloadException as e:
                if not e.content:
                    # Blocking errors: the file could not be generated
                    raise UserError('\n'.join(error['message'] for error in e.errors.values()))
                file_data = e.content
            self._add_attachment(file_data)
