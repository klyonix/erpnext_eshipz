frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
			if (frappe.model.can_create("Shipment")) {
				frm.add_custom_button(__('Custom Shipment'), () => {
					frappe.model.open_mapped_doc({
						method: "erpnext_eshipz.erpnext_eshipz.custom.sales_invoice.sales_invoice.custom_shipment_from_sales_invoice",
						frm: frm
					});
				}, __('Create'));
			}
		}
	}
});

