from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute(): 
   
    custom_field = {
        "Shipment Delivery Note": [
            dict(
                fieldname = "kly_shipment_doctype",
                label = "Shipment Doctype",
                fieldtype = "Link",
                insert_after = "delivery_note",
                options = "DocType",  
                default = "Delivery Note"
            ),
            dict(
                fieldname = "kly_shipment_reference",
                label =  "Shipment Reference",
                fieldtype = "Dynamic Link",
                insert_after = "kly_shipment_doctype",
                options = "kly_shipment_doctype",
                in_list_view = 1
            )
        ]
    }
    create_custom_fields(custom_field)
    
    make_property_setter(
        "Shipment Delivery Note",           
        "delivery_note",                    
        "reqd",                             
        0,                                  
        "Check"                             
    )
    make_property_setter(
        "Shipment Delivery Note",
        "delivery_note",
        "in_list_view",
        0,
        "Check"
    )
    make_property_setter(
        "Shipment Delivery Note",
        "delivery_note",
        "hidden",
        1,
        "Check"
    )
