import { Component } from "@odoo/owl";

export class DeferralWarningPopover extends Component {
    static template = "account_reports.DeferralWarningPopover";
    static props = {
        close: Function,
        warning_action: Function,
    };
}
