import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def custom_make_shipment(source_name, target_doc=None):
	def postprocess(source, target):
		# Set pickup contact details (optional)
		user = frappe.db.get_value(
			"User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"], as_dict=1
		)
		target.pickup_contact_email = user.email
		target.pickup_contact_person = frappe.session.user
		pickup_contact_display = f"{user.full_name}"
		if user.email:
			pickup_contact_display += "<br>" + user.email
		if user.phone:
			pickup_contact_display += "<br>" + user.phone
		if user.mobile_no and not user.phone:
			pickup_contact_display += "<br>" + user.mobile_no
		target.pickup_contact = pickup_contact_display

		# Set delivery contact details (optional)
		if source.contact_person:
			contact = frappe.db.get_value(
				"Contact", source.contact_person, ["email_id", "phone", "mobile_no"], as_dict=1
			)
			delivery_contact_display = f"{source.contact_display or ''}"
			if contact:
				if contact.email_id:
					delivery_contact_display += "<br>" + contact.email_id
				if contact.phone:
					delivery_contact_display += "<br>" + contact.phone
				if contact.mobile_no and not contact.phone:
					delivery_contact_display += "<br>" + contact.mobile_no
			target.delivery_contact = delivery_contact_display

		# Set address
		if source.shipping_address_name:
			target.delivery_address_name = source.shipping_address_name
			target.delivery_address = source.shipping_address
		elif source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

		# Set custom doc-level field
		target.kly_shipment_doctype = "Delivery Note"

		# Set child table custom fields
		for row in target.shipment_delivery_note:
			row.kly_shipment_reference = source.name
			row.kly_shipment_doctype = "Delivery Note"
			row.delivery_note = None  # ❌ Leave core 'delivery_note' field empty

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Shipment",
				"field_map": {
					"grand_total": "value_of_goods",
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
					"customer": "delivery_customer",
					"contact_person": "delivery_contact_name",
					"contact_email": "delivery_contact_email",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
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
