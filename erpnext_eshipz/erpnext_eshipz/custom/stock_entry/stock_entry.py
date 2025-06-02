import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def make_shipment_from_stock_entry(source_name, target_doc=None):
	def postprocess(source, target):
		
		user = frappe.db.get_value(
			"User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"], as_dict=1
		)
		if user:
			target.pickup_contact_email = user.email
			target.pickup_contact_person = frappe.session.user

			pickup_contact_display = f"{user.full_name or ''}"
			if user.email:
				pickup_contact_display += f"<br>{user.email}"
			if user.phone:
				pickup_contact_display += f"<br>{user.phone}"
			if user.mobile_no and not user.phone:
				pickup_contact_display += f"<br>{user.mobile_no}"
			target.pickup_contact = pickup_contact_display

		

		
		target.kly_shipment_doctype = "Stock Entry"

		
		for row in target.shipment_delivery_note:
			row.kly_shipment_doctype = "Stock Entry"
			row.kly_shipment_reference = source.name

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Shipment",
				"field_map": {
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"amount": "grand_total", 
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist