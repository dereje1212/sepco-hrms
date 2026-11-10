# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user


class TestQualityReport(TransactionCase):

    def test_quality_worksheet_report_access(self):
        check = self.env['quality.check'].create({
            'team_id': self.env.ref('quality.quality_alert_team0').id,
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
        })
        portal_user = new_test_user(self.env, login='portal_user', groups='base.group_portal')
        internal_user = new_test_user(self.env, login='internal_user', groups='base.group_user')
        quality_user = new_test_user(self.env, login='quality_user', groups='quality.group_quality_user')
        other_company = self.env['res.company'].create({'name': 'Other Company'})
        other_company_user = new_test_user(
            self.env, login='other_company_user', groups='quality.group_quality_user', company_id=other_company.id,
        )
        report_ref = 'quality_control.quality_worksheet'
        for user in (portal_user, internal_user, other_company_user):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                self.env['ir.actions.report'].with_user(user)._render_qweb_html(report_ref, check.ids)
        report = self.env['ir.actions.report'].with_user(quality_user)._render_qweb_html(report_ref, check.ids)[0]
        self.assertIn(check.name, report.decode())
