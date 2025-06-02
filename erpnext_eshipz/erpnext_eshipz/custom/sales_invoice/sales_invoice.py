import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def update_delivery_note(doc, method):
    for item in doc.items:
        if item.delivery_note:
            delivery_note = frappe.get_doc("Delivery Note", item.delivery_note)
            for dn_item in delivery_note.items:
                if dn_item.item_code == item.item_code:
                    dn_item.against_sales_invoice = doc.name
            delivery_note.save()


@frappe.whitelist()
def custom_shipment_from_sales_invoice(source_name, target_doc=None):
	def postprocess(source, target):
		# Set pickup contact info using current user details
		user = frappe.db.get_value(
			"User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"], as_dict=1
		)
		target.pickup_contact_email = user.emailK
		target.pickup_contact_person = frappe.session.user

		pickup_contact_display = f"{user.full_name}"
		if user.email:
			pickup_contact_display += "<br>" + user.email
		if user.phone:
			pickup_contact_display += "<br>" + user.phone
		if user.mobile_no and not user.phone:
			pickup_contact_display += "<br>" + user.mobile_no
		target.pickup_contact = pickup_contact_display

	
		if source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

		
		target.kly_shipment_doctype = "Sales Invoice"

		
		for row in target.shipment_delivery_note:
			row.kly_shipment_doctype = "Sales Invoice"
			row.kly_shipment_reference = source.name
		

	
	doclist = get_mapped_doc(
		"Sales Invoice",
		source_name,
		{
			"Sales Invoice": {
				"doctype": "Shipment",
				"field_map": {
					"grand_total": "value_of_goods",
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
					"customer": "delivery_customer",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Invoice Item": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"base_amount": "grand_total",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist
