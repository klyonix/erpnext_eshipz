# Copyright (c) 2024, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
 
def execute():
    custom_field = {
        "Shipment": [
            dict(
                fieldname = "kly_purpose",
                fieldtype = "Select",
                label = "Purpose",
                options = "\npersonal\ncommercial\nsample\nreturn\nrepair\ngift",
                insert_after = "pickup_company",
                reqd = 1,
                default = "commercial"
            ),
            dict(
                fieldname = "kly_pickup_type",
                fieldtype = "Select",
                label = "Pickup Type",
                options = "\nbusiness\nresidential",
                insert_after = "kly_purpose",
                reqd = 1,
                default = "business"
            ),
            dict(
                fieldname = "kly_delivery_type",
                fieldtype = "Select",
                label = "Delivery Type",
                options = "\nbusiness\nresidential",
                insert_after = "delivery_customer",
                reqd = 1,
                default = "business"
            ),
            dict(
                fieldname = "kly_latest_location",
                fieldtype = "Data",
                label = "Latest location",
                insert_after = "tracking_status_info",
            ),
            dict(
                fieldname = "kly_expected_delivery_date",
                fieldtype = "Datetime",
                label = "Expected Delivery Date",
                insert_after = "kly_latest_location",
            ),
            dict(
                fieldname = "kly_delivery_date",
                fieldtype = "Datetime",
                label = "Delivery Date",
                insert_after = "kly_expected_delivery_date",
            ),
            dict(
                fieldname = "kly_last_update_received",
                fieldtype = "Datetime",
                label = "Last Update Received",
                insert_after = "tracking_url",
            ),
        ]
    }
    create_custom_fields(custom_field)
    make_property_setter("Batch", "expiry_date", "reqd", 1, "Check")
    make_property_setter("Shipment", "description_of_content", "default", "Medicine", "Small Text")
    make_property_setter("Shipment", "pickup_date", "default", "Today", "Small Text")