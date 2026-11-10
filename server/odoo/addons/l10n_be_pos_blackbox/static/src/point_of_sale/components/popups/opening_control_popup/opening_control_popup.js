import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";

patch(OpeningControlPopup.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
        this.confirm = useAsyncLockedMethod(this.confirm);
    },
    async confirm() {
        await super.confirm();
        if (this.pos.blackbox.isActive) {
            await this.pos.data.read("pos.session", [this.pos.session.id]);
            const cashier = this.pos.getCashier();
            // If it fails, the cashier stays logged in: the work in is retried before the next event
            await this.pos.handleClockInOut(cashier, "in");
        }
    },
    async openDetailsPopup() {
        if (this.pos.blackbox.isActive) {
            await this.pos.blackbox.signDrawerOpen.sign(
                this.pos.models,
                this.pos.l10nBeSigningInsz
            );
        }
        return super.openDetailsPopup();
    },
});
