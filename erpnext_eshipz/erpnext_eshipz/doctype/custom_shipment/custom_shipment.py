# Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json
import requests
from datetime import datetime
from collections import defaultdict
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class CustomShipment(Document):
	pass


@frappe.whitelist()
def validation_of_shipment(self, method):
    try:
        # Validation of address if shipment type is Bulk
        if self.type == "Bulk Shipment":
            for details in self.receiver_details:
                # Check if any of the required fields are missing
                if not (details.receiver_party_type and details.receiver_name and details.address):
                    frappe.throw(_("Receiver details are incomplete. Please fill in party type, name, and address."))

                if not (details.weight and details.count):
                    frappe.throw(_("Package dimensions or weight/count are missing. Please fill all required fields."))
        
        elif self.type == "Single Shipment":
            if self.shipment_parcel == []:
                frappe.throw("Parcel details are incomplete. Please fill the parcel details in Shipment Parcel table")

    except Exception as e:
        frappe.throw(_("An error occurred during shipment validation: {0}").format(str(e)))



@frappe.whitelist()
def get_filtered_records_with_addresses(doctype, filters):
    """Fetch records with their addresses and contacts in optimized queries"""
    import frappe
    from frappe.contacts.doctype.address.address import get_address_display
    
    # Get main records - no limit since we're doing server-side processing
    records = frappe.get_list(
        doctype,
        fields=["name"],
        filters=filters,
        order_by="name"
    )
    
    if not records:
        return []
    
    record_names = [r["name"] for r in records]
    
    # Get all addresses linked to these records
    address_data = frappe.db.sql("""
        SELECT 
            dl.link_name as record_name,
            addr.name
        FROM `tabAddress` addr
        JOIN `tabDynamic Link` dl ON addr.name = dl.parent
        WHERE 
            dl.link_doctype = %(doctype)s AND
            dl.link_name IN %(record_names)s AND
            dl.parenttype = 'Address'
        ORDER BY addr.is_primary_address DESC, addr.modified DESC
    """, {
        "doctype": doctype,
        "record_names": record_names
    }, as_dict=True)
    
    # Get all contacts linked to these records
    contact_data = frappe.db.sql("""
        SELECT 
            dl.link_name as record_name,
            contact.name, contact.email_id, contact.phone, contact.mobile_no
        FROM `tabContact` contact
        JOIN `tabDynamic Link` dl ON contact.name = dl.parent
        WHERE 
            dl.link_doctype = %(doctype)s AND
            dl.link_name IN %(record_names)s AND
            dl.parenttype = 'Contact'
        ORDER BY contact.is_primary_contact DESC, contact.modified DESC
    """, {
        "doctype": doctype,
        "record_names": record_names
    }, as_dict=True)
    
    # Organize addresses and contacts by record name
    addresses_by_record = {}
    for addr in address_data:
        if addr.record_name not in addresses_by_record:
            addresses_by_record[addr.record_name] = addr
    
    contacts_by_record = {}
    for contact in contact_data:
        if contact.record_name not in contacts_by_record:
            contacts_by_record[contact.record_name] = contact
    
    # Combine all data
    result = []
    for record in records:
        record_data = {"name": record["name"]}
        
        # Add address if exists
        if record["name"] in addresses_by_record:
            record_data["address"] = addresses_by_record[record["name"]]
            
        # Add contact if exists
        if record["name"] in contacts_by_record:
            record_data["contact"] = contacts_by_record[record["name"]]
            
        result.append(record_data)
    
    return result


@frappe.whitelist()
def fetch_available_services(docname):
    # Get main document in one query
    doc = frappe.get_doc('Custom Shipment', docname)
    
    # Optimize address fetching - get all receiver addresses in one query
    receiver_addresses = {r.address: r for r in doc.receiver_details}
    address_names = [doc.address] + list(receiver_addresses.keys())
    
    # Get all addresses in one query
    addresses = frappe.db.sql(f"""
        SELECT name, address_line1, address_line2, city, state, pincode, country, phone, email_id
        FROM `tabAddress`
        WHERE name IN ({','.join(['%s']*len(address_names))})
    """, address_names, as_dict=1)
    
    # Create address mapping
    address_map = {a.name: a for a in addresses}
    pickup_address = address_map.get(doc.address)
    if not pickup_address:
        frappe.throw("Pickup address not found")
    
    # Get country codes in one query
    country_names = {pickup_address.country}
    for addr in receiver_addresses.values():
        country_names.add(address_map.get(addr.address, {}).get('country'))
    
    countries = frappe.db.sql(f"""
        SELECT name, code FROM `tabCountry`
        WHERE name IN ({','.join(['%s']*len(country_names))})
    """, list(country_names), as_dict=1)
    country_code_map = {c.name: c.code.upper() for c in countries}
    
    pickup_country_code = country_code_map.get(pickup_address.country)
    if not pickup_country_code:
        frappe.throw("Country code not found for pickup address")

    if doc.type == "Bulk Shipment":
        api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
        if not api_token:
            frappe.throw("API token not found in eShipz Settings")

        url = "https://app.eshipz.com/api/v2/services"
        headers = {
            "X-API-TOKEN": api_token,
            "Content-Type": "application/json"
        }

        all_services = []
        
        for receiver in doc.receiver_details:
            delivery_address = address_map.get(receiver.address)
            if not delivery_address:
                continue
                
            delivery_country_code = country_code_map.get(delivery_address.country)
            if not delivery_country_code:
                continue
            
            data = {    
                "is_document": False,
                "shipment": {
                    "is_reverse": False,
                    "purpose": doc.kly_purpose,
                    "is_cod": False,
                    "collect_on_delivery": {"amount": 0, "currency": "INR"},
                    "ship_from": {
                        "contact_name": doc.pickup_contact_person,
                        "company_name": doc.company,
                        "street1": pickup_address.address_line1,
                        "street2": pickup_address.address_line2,
                        "city": pickup_address.city,
                        "state": pickup_address.state,
                        "postal_code": pickup_address.pincode,
                        "country": pickup_country_code,
                        "type": doc.kly_pickup_type,
                        "phone": pickup_address.phone,
                        "email": pickup_address.email_id,
                        "is_primary": True
                    },
                    "ship_to": {
                        "contact_name": receiver.receiver_name,
                        "company_name": receiver.receiver_name,
                        "street1": delivery_address.address_line1,
                        "street2": delivery_address.address_line2,
                        "city": delivery_address.city,
                        "state": delivery_address.state,
                        "postal_code": delivery_address.pincode,
                        "phone": delivery_address.phone,
                        "country": delivery_country_code,
                        "type": doc.kly_delivery_type,
                        "email": delivery_address.email_id,
                    },
                    "return_to": {
                        "contact_name": doc.pickup_contact_person,
                        "company_name": doc.company,
                        "street1": pickup_address.address_line1,
                        "city": pickup_address.city,
                        "state": pickup_address.state,
                        "postal_code": pickup_address.pincode,
                        "country": pickup_country_code,
                        "type": doc.kly_pickup_type,
                        "phone": pickup_address.phone,
                        "email": pickup_address.email_id,
                        "is_primary": True
                    },
                    "parcels": [
                        {
                            "description": doc.description_of_content,
                            "box_type": doc.shipment_type,
                            "weight": {"value": receiver.weight, "unit": "kg"},
                            "dimension": {
                                "width": receiver.width,
                                "height": receiver.height,
                                "length": receiver.lengths,
                                "unit": "cm"
                            },
                            "items": [
                                {
                                    "description": doc.description_of_content,
                                    "origin_country": pickup_country_code,
                                    "quantity": receiver.count,
                                    "price": {
                                        "amount": doc.value_of_goods,
                                        "currency": "INR"
                                    },
                                    "weight": {
                                        "unit": "kg",
                                        "value": receiver.weight
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
            
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                if 'rates' in result.get('data', {}):
                    rates_list = result['data']['rates']
                    if rates_list:
                        services = [rate for rate in rates_list if rate.get('code') in [200, 201]]
                        for service in services:
                            service['receiver_name'] = receiver.receiver_name
                            service['receiver_idx'] = receiver.idx
                        all_services.extend(services)
            except Exception as e:
                frappe.log_error(f"Failed to fetch services for receiver {receiver.idx}: {str(e)}")
                continue
        
        return all_services

@frappe.whitelist()
def fetch_single_available_services(docname):
    doc = frappe.get_doc('Custom Shipment', docname)
    pickup_address = frappe.db.get_value('Address', doc.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)

    if doc.type == "Single Shipment":
        cnty_code = doc.country_code
        delivery_country_code = doc.country_code.upper()

        api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
        if not api_token:
            frappe.throw("API token not found in eShipz Settings")

        url = "https://app.eshipz.com/api/v2/services"
        headers = {
            "X-API-TOKEN": api_token,
            "Content-Type": "application/json"
        }

        data = {    
            "is_document": False,
            "shipment": {
                "is_reverse": False,
                "purpose": doc.kly_purpose,
                "is_cod": False,
                "collect_on_delivery": {"amount": 0, "currency": "INR"},
                "ship_from": {
                    "contact_name": doc.pickup_contact_person,
                    "company_name": doc.company,
                    "street1": pickup_address.address_line1,
                    "street2": pickup_address.address_line2,
                    "city": pickup_address.city,
                    "state": pickup_address.state,
                    "postal_code": pickup_address.pincode,
                    "country": pickup_country_code,
                    "type": doc.kly_pickup_type,
                    "phone": pickup_address.phone,
                    "email": pickup_address.email_id,
                    "is_primary": True
                },
                "ship_to": {
                    "contact_name": doc.name_of_the_receiver,
                    "company_name": doc.name_of_the_receiver,
                    "street1": doc.address_line_1,
                    "street2": doc.address_line_2,
                    "city": doc.city,
                    "state": doc.state,
                    "postal_code": doc.pincode,
                    "country": delivery_country_code,
                    "type": doc.kly_delivery_type,
                    "phone": doc.contact,
                    "email": doc.email_id,
                },
                "return_to": {
                    "contact_name": doc.pickup_contact_person,
                    "company_name": doc.company,
                    "street1": pickup_address.address_line1,
                    "street2": pickup_address.address_line2,
                    "city": pickup_address.city,
                    "state": pickup_address.state,
                    "postal_code": pickup_address.pincode,
                    "country": pickup_country_code,
                    "type": doc.kly_pickup_type,
                    "phone": pickup_address.phone,
                    "email": pickup_address.email_id,
                    "is_primary": True
                },
                "parcels": [
                    {
                        "description": doc.description_of_content,
                        "box_type": doc.shipment_type,
                        "weight": {"value": parcel.weight, "unit": "kg"},
                        "dimension": {
                            "width": parcel.width,
                            "height": parcel.height,
                            "length": parcel.length,
                            "unit": "cm"
                        },
                        "items": [
                            {
                                "description": doc.description_of_content,
                                "origin_country": pickup_country_code,
                                "quantity": parcel.count,
                                "price": {
                                    "amount": doc.value_of_goods,
                                    "currency": "INR"
                                },
                                "weight": {
                                    "unit": "kg",
                                    "value": parcel.weight
                                }
                            }
                        ]
                    } for parcel in doc.get("shipment_parcel")
                ]
            }
        }
        json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

        response = requests.post(url, headers=headers, data=json_data)

        if response.status_code == 200:
            result = response.json()
            if 'rates' in result['data']:
                rates_list = result['data']['rates']
                if rates_list:
                    return [rate for rate in rates_list if rate.get('code') in [200, 201]]
                        
                frappe.throw("Failed to fetch services: " + response.text)
            else:
                frappe.throw("Rates key not found in API response: " + frappe.as_json(result))


@frappe.whitelist()
def create_shipment(docname, selected_service, item_data=None):
    doc = frappe.get_doc('Custom Shipment', docname)
    
    selected_service = json.loads(selected_service)
    if item_data:
        item_data = json.loads(item_data)

    pickup_address = frappe.db.get_value('Address', doc.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
    delivery_country_code = doc.country_code.upper()

    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/create-shipments"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    charged_weight = sum(parcel.weight for parcel in doc.get("shipment_parcel"))

    invoice_numbers = set()
    invoice_dates = set()
    consolidated_items = defaultdict(lambda: {"weight": 0, "amount": 0})
    gst_invoices = []

    total_order_value = 0
    invoice_number = ''
    invoice_date = ''
    ewaybill_number = ''
    ewaybill_date = ''
    invoice_value = doc.value_of_goods
    invoice_currency = 'INR'


    gst_invoices.append({
                    "invoice_number": invoice_number,
                    "invoice_date": str(invoice_date),
                    "invoice_value": invoice_value,
                    "ewaybill_number": ewaybill_number,
                    "ewaybill_date": str(ewaybill_date)
                })
    items = [
        {
            "description": doc.description_of_content,
            "box_type": doc.shipment_type,
            "origin_country": pickup_country_code,
            "variant": "",
            "quantity": info.count,
            "weight": {
                "value": info.weight,
                "unit": "kg"
            },
            "dimension": {
                "width": info.width,
                "height": info.height,
                "length": info.length,
                "unit": "cm"
            },

        } for info in doc.get("shipment_parcel")
    ]


    data = {
        "billing": {
            "paid_by": "shipper"
        },
        "vendor_id": selected_service['vendor_id'],
        "description": selected_service['description'],
        "slug": selected_service['slug'],
        "purpose": doc.kly_purpose,
        "order_source": "erpnext",
        "parcel_contents": doc.description_of_content,
        "is_document": False,
        "service_type": selected_service['selected_service_type'],
        "charged_weight": {
            "unit": "KG",
            "value": charged_weight
        },
        "customer_reference": doc.name,
        "invoice_number": ", ".join(invoice_numbers),
        "invoice_date": ", ".join(invoice_dates),
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": invoice_currency},
        "shipment": {
            "ship_from": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "tax_id": pickup_address.gstin,
                "country": pickup_country_code,
                "type": doc.kly_pickup_type
            },
            "ship_to": {
                "contact_name": doc.name_of_the_receiver,
                "company_name": doc.name_of_the_receiver,
                "street1": doc.address_line_1,
                "street2": doc.address_line_2,
                "city": doc.city,
                "state": doc.state,
                "postal_code": doc.pincode,
                "phone": doc.contact,
                "email": doc.email_id,
                "country": delivery_country_code,
                "type": doc.kly_delivery_type
            },
            "return_to": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "tax_id": pickup_address.gstin,
                "country": pickup_country_code,
                "type": doc.kly_pickup_type
            },
            "is_reverse": False,
            "is_to_pay": False,
            "parcels": items
        },
        "gst_invoices": gst_invoices
    }

    json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        result = response.json()
        if 'files' in result['data']:
            label_url = result['data']['files']['label']['label_meta']['url']
            awb_number = result['data']['files']['label']['label_meta']['awb']
            service_provider = result['data']['slug']
            tracking_status_info = result['data']['status']
            carrier_service = result['data']['service_type']
            shipment_id = result['data']['order_id']

            doc.db_set('tracking_url', label_url)
            doc.db_set('awb_number', awb_number)
            doc.db_set('status', "Booked")
            doc.db_set('tracking_status', "In Progress")
            doc.db_set('service_provider', service_provider)
            doc.db_set('shipment_id', shipment_id)
            doc.db_set('tracking_status_info', tracking_status_info)
            doc.db_set('carrier_service', carrier_service)
            frappe.db.commit()
            return {"label_url": label_url, "awb_number": awb_number, "service_provider": service_provider, "tracking_status_info": tracking_status_info, "carrier_service": carrier_service, "shipment_id": shipment_id}
        else:
            frappe.throw("Files key not found in API response: " + frappe.as_json(result))
    else:
        frappe.throw("Failed to create shipment: " + response.text)


@frappe.whitelist()
def create_bulk_shipment(docname, shipments_data):
    """
    Create shipments for multiple receivers at once and update each receiver row
    """
    doc = frappe.get_doc("Custom Shipment", docname)
    results = []
    
    try:
        shipments_data = json.loads(shipments_data)
        
        for shipment in shipments_data:
            receiver_idx = shipment.get('receiver_idx')
            service_data = shipment.get('service_data')
            item_data = shipment.get('item_data', {})
            
            try:
                # Get the receiver detail row
                receiver_row = None
                if receiver_idx is not None:
                    for row in doc.receiver_details:
                        if row.idx == receiver_idx:
                            receiver_row = row
                            break
                
                if not receiver_row:
                    results.append({
                        'receiver_idx': receiver_idx,
                        'receiver_name': shipment.get('receiver_name'),
                        'status': 'Failed',
                        'error': 'Receiver details not found'
                    })
                    continue
                
                # Create the shipment - pass docname instead of doc
                shipment_result = create_single_shipment(
                    docname=docname,
                    receiver_idx=receiver_idx,
                    service_data=service_data,
                    item_data=item_data
                )
                
                # Update the receiver row with shipment details
                if shipment_result.get('status') == 'Success':
                    receiver_row.awb_number = shipment_result.get('awb_number')
                    receiver_row.service_provider = shipment_result.get('service_provider')
                    receiver_row.tracking_url = shipment_result.get('tracking_url')
                    receiver_row.status = 'Booked'
                    receiver_row.shipment_id = shipment_result.get('shipment_id')
                
                results.append({
                    'receiver_idx': receiver_idx,
                    'receiver_name': receiver_row.receiver_name,
                    'status': shipment_result.get('status', 'Failed'),
                    'awb_number': shipment_result.get('awb_number'),
                    'service_provider': shipment_result.get('service_provider'),
                    'tracking_url': shipment_result.get('tracking_url'),
                    'error': shipment_result.get('error'),
                    'tracking_status_info': shipment_result.get('tracking_status_info'),
                    'tracking_status': shipment_result.get('tracking_status'),
                    'carrier_service': shipment_result.get('carrier_service')

                })
                
            except Exception as e:
                frappe.log_error(f"Failed to create shipment for receiver {receiver_idx}")
                results.append({
                    'receiver_idx': receiver_idx,
                    'receiver_name': shipment.get('receiver_name'),
                    'status': 'Failed',
                    'error': str(e)
                })
        
        # Save the document with all updates
        doc.save()
        frappe.db.commit()
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Bulk shipment creation failed for {docname}")
        frappe.db.rollback()
        return [{
            'status': 'Failed',
            'error': str(e)
        }]

@frappe.whitelist()
def create_single_shipment(docname, receiver_idx, service_data, item_data):
    """
    Create a single shipment for a receiver
    """
    doc = frappe.get_doc("Custom Shipment", docname)
    pickup_address = frappe.db.get_value('Address', doc.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    # Find the receiver row
    receiver_row = None
    for row in doc.receiver_details:
        if row.idx == receiver_idx:
            receiver_row = row
            break
    
    if not receiver_row:
        frappe.throw(f"Receiver with idx {receiver_idx} not found")
    
    delivery_address = frappe.db.get_value('Address', receiver_row.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
    delivery_country_code = get_country_code(delivery_address.country)
    
    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/create-shipments"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    # Prepare parcels data
    parcels = [{
        "description": item_data.get('description', doc.description_of_content),
        "box_type": doc.shipment_type,
        "quantity": receiver_row.count,
        "weight": {
            "value": receiver_row.weight,
            "unit": "kg"
        },
        "dimension": {
            "width": receiver_row.width,
            "height": receiver_row.height,
            "length": receiver_row.lengths,
            "unit": "cm"
        },
        "items": [{
            "description": item_data.get('description', doc.description_of_content),
            "origin_country": pickup_country_code,
            "quantity": receiver_row.count,
            "price": {
                "amount": doc.value_of_goods,
                "currency": "INR"
            },
            "weight": {
                "value": receiver_row.weight,
                "unit": "kg"
            }
        }]
    }]

    data = {
        "billing": {
            "paid_by": "shipper"
        },
        "vendor_id": service_data.get('vendor_id'),
        "description": service_data.get('description'),
        "slug": service_data.get('slug'),
        "purpose": doc.kly_purpose,
        "order_source": "erpnext",
        "is_document": False,
        "parcel_contents": doc.description_of_content,
        "service_type": service_data.get('selected_service_type'),
        "charged_weight": {
            "unit": "KG",
            "value": receiver_row.weight
        },
        "customer_reference": f"{doc.name}-{receiver_idx}",
        "invoice_number": " ",
        "invoice_date": " ",
        "is_reverse": False,
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": "INR"},
        "shipment": {
            "ship_from": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "country": pickup_country_code,
                "type": doc.kly_pickup_type
            },
            "ship_to": {
                "contact_name": receiver_row.receiver_name,
                "company_name": receiver_row.receiver_name,
                "street1": delivery_address.address_line1,
                "street2": delivery_address.address_line2,
                "city": delivery_address.city,
                "state": delivery_address.state,
                "postal_code": delivery_address.pincode,
                "phone": delivery_address.phone,
                "email": delivery_address.email_id,
                "country": delivery_country_code,
                "type": doc.kly_delivery_type
            },
            "return_to": {
                "contact_name": doc.pickup_contact_person,
                "company_name": doc.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "country": pickup_country_code,
                "type": doc.kly_pickup_type
            },
            "is_to_pay": False,
            "parcels": parcels
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        if 'files' in result.get('data', {}):
            label_url = result['data']['files']['label']['label_meta']['url']
            awb_number = result['data']['files']['label']['label_meta']['awb']
            service_provider = result['data']['slug']
            shipment_id = result['data']['order_id']
            tracking_status_info = result['data']['status']
            carrier_service = result['data']['service_type']

            return {
                'status': 'Success',
                'awb_number': awb_number,
                'service_provider': service_provider,
                'tracking_url': label_url,
                'shipment_id': shipment_id,
                'tracking_status': 'In Progress',
                'tracking_status_info': tracking_status_info,
                'carrier_service': carrier_service
            }
        else:
            frappe.log_error(f"{result['meta']['message']} for {receiver_row.receiver_name}")
            frappe.throw(f"{result['meta']['details']}")
    else:
        error_msg = response.json().get("msg", response.text)
        frappe.log_error(f"API Failed for {receiver_row.receiver_name} with {response.status_code}: {error_msg}")
        frappe.throw(f"API request failed with status {response.status_code}: {error_msg}")


@frappe.whitelist()
def update_status(docname):
    doc = frappe.get_doc('Custom Shipment', docname)
    
    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v2/trackings"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    results = {}
    
    if doc.type == "Single Shipment":
        # Handle single shipment
        if not doc.awb_number:
            frappe.throw("AWB number not found for this shipment")
            
        tracking_data = fetch_tracking_data(url, headers, doc.awb_number)
        update_doc_status(doc, tracking_data)
        results["main_shipment"] = prepare_tracking_result(doc, tracking_data)
        
    elif doc.type == "Bulk Shipment":
        # Handle bulk shipment
        if not doc.receiver_details:
            frappe.throw("No receiver details found for bulk shipment")
            
        results["receivers"] = []
        updated_receivers = []
        
        for receiver in doc.receiver_details:
            if not receiver.awb_number:
                continue
                
            try:
                tracking_data = fetch_tracking_data(url, headers, receiver.awb_number)
                update_receiver_status(receiver, tracking_data)
                results["receivers"].append({
                    "receiver_name": receiver.receiver_name,
                    **prepare_tracking_result(receiver, tracking_data)
                })
                updated_receivers.append(receiver)
            except Exception as e:
                results["receivers"].append({
                    "receiver_name": receiver.receiver_name,
                    "error": str(e),
                    "awb_number": receiver.awb_number
                })
        
        # Save all updated receivers at once
        if updated_receivers:
            doc.save()
    
    frappe.db.commit()
    return results

def fetch_tracking_data(url, headers, awb_number):
    """Fetch tracking data from eShipz API"""
    response = requests.post(url, headers=headers, json={"track_id": awb_number})
    
    if response.status_code != 200:
        frappe.throw(f"Failed to retrieve shipment status for AWB {awb_number}: {response.text}")
    
    result = response.json()
    if not result or not isinstance(result, list):
        frappe.throw(f"Invalid API response format for AWB {awb_number}: {frappe.as_json(result)}")
    
    return result[0] if result else None

def update_doc_status(doc, tracking_data):
    """Update the main document status"""
    if not tracking_data or 'checkpoints' not in tracking_data:
        frappe.throw("Invalid tracking data format")
    
    process_tracking_data(doc, tracking_data)
    doc.last_update_received = frappe.utils.now()

def update_receiver_status(receiver, tracking_data):
    """Update receiver status in bulk shipment"""
    if not tracking_data or 'checkpoints' not in tracking_data:
        frappe.throw("Invalid tracking data format")
    
    process_tracking_data(receiver, tracking_data)
    receiver.last_update_received = frappe.utils.now()

def process_tracking_data(target, tracking_data):
    """Process tracking data and update the target (doc or receiver)"""
    checkpoints = tracking_data.get('checkpoints', [])
    delivery_date = tracking_data.get('delivery_date')
    expected_delivery_date = tracking_data.get('expected_delivery_date')
    tag = tracking_data.get('tag')
    
    # Process latest checkpoint
    latest_city = None
    latest_remark = None
    
    if checkpoints:
        latest_checkpoint = sorted(
            checkpoints, 
            key=lambda x: datetime.strptime(x['date'], "%a, %d %b %Y %H:%M:%S %Z"), 
            reverse=True
        )[0]
        latest_city = latest_checkpoint.get('city')
        latest_remark = latest_checkpoint.get('remark')
        target.latest_location = latest_city
    
    # Update status based on tag
    if tag == "Delivered":
        target.status = "Completed"
        target.tracking_status = "Delivered"
    elif tag == "InTransit":
        target.tracking_status = "In Progress"
    
    # Update dates
    if delivery_date:
        target.delivery_date = datetime.strptime(
            delivery_date, "%a, %d %b %Y %H:%M:%S %Z"
        ).strftime("%Y-%m-%d %H:%M:%S")
    
    if expected_delivery_date:
        target.expected_delivery_date = datetime.strptime(
            expected_delivery_date, "%a, %d %b %Y %H:%M:%S %Z"
        ).strftime("%Y-%m-%d %H:%M:%S")
    
    target.tracking_status_info = latest_remark

def prepare_tracking_result(target, tracking_data):
    """Prepare the tracking result for API response"""
    return {
        "awb_number": target.awb_number,
        "latest_location": target.latest_location,
        "tracking_status": target.tracking_status,
        "tracking_status_info": target.tracking_status_info,
        "delivery_date": target.delivery_date,
        "expected_delivery_date": target.expected_delivery_date,
        "status": target.status,
        "tag": tracking_data.get('tag'),
        "shipment_status": tracking_data.get('shipment_status')
    }


@frappe.whitelist()
def cancel_shipment(docname, shipments_to_cancel=None):
    doc = frappe.get_doc('Custom Shipment', docname)
    
    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/cancel"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    results = {}
    
    try:
        if shipments_to_cancel:
            # Convert string parameter to Python list if needed
            if isinstance(shipments_to_cancel, str):
                shipments_to_cancel = json.loads(shipments_to_cancel)
            
            if doc.type == "Single Shipment":
                # Handle single shipment cancellation
                if not doc.shipment_id:
                    frappe.throw("Shipment ID not found for this shipment")
                
                data = {
                    "order_id": [doc.shipment_id]
                }
                
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    doc.tracking_url = ""
                    doc.status = "Cancelled"
                    doc.tracking_status = ""
                    doc.service_provider = ""
                    doc.tracking_status_info = "Cancelled"
                    doc.carrier_service = ""
                    doc.save()
                    results["main_shipment"] = {
                        "status": "Success",
                        "message": "Shipment cancelled successfully"
                    }
                else:
                    results["main_shipment"] = {
                        "status": "Failed",
                        "error": response.text
                    }
                    
            elif doc.type == "Bulk Shipment":
                # Handle bulk shipment with selective cancellation
                results["receivers"] = []
                receivers_to_update = []
                
                for shipment in shipments_to_cancel:
                    if shipment.get('type') == 'main':
                        # Cancel main shipment
                        if not doc.shipment_id:
                            results["receivers"].append({
                                "receiver_name": "Main Shipment",
                                "status": "Failed",
                                "error": "Shipment ID not found",
                                "awb_number": doc.awb_number
                            })
                            continue
                            
                        data = {
                            "order_id": [doc.shipment_id]
                        }
                        
                        response = requests.post(url, headers=headers, json=data)
                        
                        if response.status_code == 200:
                            doc.tracking_url = ""
                            doc.status = "Cancelled"
                            doc.tracking_status = ""
                            doc.service_provider = ""
                            doc.tracking_status_info = "Cancelled"
                            doc.carrier_service = ""
                            doc.save()
                            
                            results["receivers"].append({
                                "receiver_name": "Main Shipment",
                                "status": "Success",
                                "message": "Shipment cancelled successfully",
                                "awb_number": doc.awb_number
                            })
                        else:
                            results["receivers"].append({
                                "receiver_name": "Main Shipment",
                                "status": "Failed",
                                "error": response.text,
                                "awb_number": doc.awb_number
                            })
                            
                    elif shipment.get('type') == 'receiver':
                        # Cancel receiver shipment
                        receiver_idx = shipment.get('idx')
                        receiver = next((r for r in doc.receiver_details if r.idx == receiver_idx), None)
                        
                        if not receiver:
                            results["receivers"].append({
                                "receiver_name": f"Receiver IDX {receiver_idx}",
                                "status": "Failed",
                                "error": "Receiver not found",
                                "awb_number": ""
                            })
                            continue
                            
                        if not receiver.shipment_id:
                            results["receivers"].append({
                                "receiver_name": receiver.receiver_name,
                                "status": "Failed",
                                "error": "Shipment ID not found",
                                "awb_number": receiver.awb_number
                            })
                            continue
                            
                        try:
                            data = {
                                "order_id": [receiver.shipment_id]
                            }
                            
                            response = requests.post(url, headers=headers, json=data)
                            
                            if response.status_code == 200:
                                receiver.tracking_url = ""
                                receiver.status = "Cancelled"
                                receiver.tracking_status = ""
                                receiver.service_provider = ""
                                receiver.tracking_status_info = "Cancelled"
                                receiver.carrier_service = ""
                                receivers_to_update.append(receiver)
                                
                                results["receivers"].append({
                                    "receiver_name": receiver.receiver_name,
                                    "status": "Success",
                                    "message": "Shipment cancelled successfully",
                                    "awb_number": receiver.awb_number
                                })
                            else:
                                results["receivers"].append({
                                    "receiver_name": receiver.receiver_name,
                                    "status": "Failed",
                                    "error": response.text,
                                    "awb_number": receiver.awb_number
                                })
                                
                        except Exception as e:
                            results["receivers"].append({
                                "receiver_name": receiver.receiver_name,
                                "status": "Failed",
                                "error": str(e),
                                "awb_number": receiver.awb_number
                            })
                
                # Save all updated receivers at once
                if receivers_to_update:
                    doc.save()
        
        frappe.db.commit()
        return results
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Shipment Cancellation Error")
        frappe.throw(f"Error cancelling shipment: {str(e)}")