import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    isSettlementOnly() {
        return (
            (this.is_settling_account && this.lines.length === 0) ||
            (this.lines.length > 0 && this.lines.every((line) => line.isAnySettleLine()))
        );
    },
    // @Override
    setToInvoice(to_invoice) {
        super.setToInvoice(this.isSettlementOnly() ? false : to_invoice);
    },
});
