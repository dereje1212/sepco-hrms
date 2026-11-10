import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    openCashbox() {
        if (this.pos.blackbox.isActive) {
            const cashier = this.pos.l10nBeSigningInsz;
            this.pos.blackbox.signDrawerOpen.sign(this.pos.models, cashier);
        }
        return super.openCashbox(...arguments);
    },
});
