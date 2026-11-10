from datetime import datetime
from unittest.mock import patch

from pytz import UTC, timezone

from odoo import Command
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestMultiCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_flexible_40h = cls.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'flexible_hours': True,
            'hours_per_day': 8.0,
            'hours_per_week': 30.0,
            'full_time_required_hours': 40.0,
            'tz': 'America/New_York',
        })
        cls.calendar_fixed_20h = cls.env['resource.calendar'].create({
            'name': 'Fixed 20h/week',
            'hours_per_day': 4.0,
            'tz': 'America/New_York',
            'attendance_ids': [Command.create({
                'name': f'Day {dow}',
                'dayofweek': str(dow),
                'hour_from': 8.0,
                'hour_to': 12.0,
            }) for dow in range(5)],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'resource_calendar_id': cls.calendar_fixed_20h.id,
        })

    def test_mixed_calendars_in_weekly_period_with_non_utc_timezone(self):
        """
        Ensures that daily working hours are computed using the
        calendar active during each contract period.
        """
        self.env.user.tz = 'America/New_York'

        # Fixed contract start, built the way hr_contract does it (LMT offset)
        fixed_start = datetime(2026, 7, 30).replace(tzinfo=timezone('America/New_York')).astimezone(UTC)

        periods = [
            (datetime(2026, 7, 1, tzinfo=UTC), fixed_start, self.calendar_flexible_40h),
            (fixed_start, datetime(2026, 9, 1, tzinfo=UTC), self.calendar_fixed_20h),
        ]
        with patch.object(self.registry['hr.employee'], '_get_calendar_periods', return_value={self.employee: periods}):
            res = self.employee._count_daily_working_hours('2026-07-27', '2026-08-02')[self.employee.id]

        # Last day of the flexible period: hours_per_day
        self.assertEqual(res['2026-07-29'], 8.0)

        # First day of the fixed period: must use the fixed calendar (4h),
        self.assertEqual(res['2026-07-30'], 4.0)

        # 3 flexible days * 40/7 + 2 fixed working days * 4h.
        self.assertEqual(res['full_time_required_hours'], round(3 * 40 / 7 + 2 * 4, 2))

        # 3 flexible days * 30/7 + 2 fixed working days * 4h.
        self.assertEqual(res['hours_per_week'], round(3 * 30 / 7 + 2 * 4, 2))
