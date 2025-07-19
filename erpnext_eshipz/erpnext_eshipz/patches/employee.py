from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute(): 
   
    custom_field = {
        "Employee": [
            dict(
                fieldname = "address_html",
                label = "Address HTML",
                fieldtype = "HTML",
                insert_after = "cell_number",
                hidden = 1
            )
        ]
    }
    create_custom_fields(custom_field)