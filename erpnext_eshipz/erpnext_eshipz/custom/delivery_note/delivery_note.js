frappe.ui.form.on("Delivery Note", {
	refresh: function(frm) {
		if (!frm.doc.is_return && frm.doc.status !== "Closed" && frm.doc.docstatus === 1) {
			if (frappe.model.can_create("Shipment")) {
				frm.add_custom_button(__("Eshipz Shipment"), function () {
					frappe.model.open_mapped_doc({
						method: "erpnext_eshipz.erpnext_eshipz.custom.delivery_note.delivery_note.custom_make_shipment", 
						frm: frm
					});
				}, __("Create"));
			}
		}
	}
});
