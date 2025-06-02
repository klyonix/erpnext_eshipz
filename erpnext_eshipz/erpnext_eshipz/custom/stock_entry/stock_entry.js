frappe.ui.form.on("Stock Entry", {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && frappe.model.can_create("Shipment")) {
			frm.add_custom_button(__('Create Shipment'), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext_eshipz.erpnext_eshipz.custom.stock_entry.stock_entry.make_shipment_from_stock_entry",
					frm: frm
				});
			});
		}
	}
});
