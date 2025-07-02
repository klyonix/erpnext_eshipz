# Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

import json
import frappe
import requests
from datetime import datetime
from collections import defaultdict
from frappe import _
from frappe.model.document import Document


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
    doc = frappe.get_doc('Custom Shipment', docname)
    pickup_address = frappe.db.get_value('Address', doc.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
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
        
        for receiver in doc.get("receiver_details"):
            delivery_address = frappe.db.get_value('Address', receiver.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
            delivery_country_code = get_country_code(delivery_address.country)
            
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
            
            json_data = json.dumps(data, separators=(',', ':'), default=lambda x: str(x).lower() if isinstance(x, bool) else x)
            response = requests.post(url, headers=headers, data=json_data)

            if response.status_code == 200:
                result = response.json()
                if 'rates' in result['data']:
                    rates_list = result['data']['rates']
                    if rates_list:
                        services = [rate for rate in rates_list if rate.get('code') in [200, 201]]
                        for service in services:
                            service['receiver_name'] = receiver.receiver_name
                            service['receiver_idx'] = receiver.idx
                        all_services.extend(services)
                else:
                    frappe.throw("Rates key not found in API response: " + frappe.as_json(result))
            else:
                frappe.throw("Failed to fetch services: " + response.text)
        
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

    data = {
        "track_id": doc.awb_number
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if not result:
            frappe.throw("API response is empty")

        if not isinstance(result, list):
            frappe.throw("API response format is not a list: " + frappe.as_json(result))

        tracking_data = result[0] if result else None
        if not tracking_data or 'checkpoints' not in tracking_data:
            frappe.throw("Invalid tracking data format: " + frappe.as_json(result))

        checkpoints = tracking_data.get('checkpoints', [])
        delivery_date = tracking_data.get('delivery_date')
        expected_delivery_date = tracking_data.get('expected_delivery_date')
        shipment_status = tracking_data.get('shipment_status')
        tag = tracking_data.get('tag')

        latest_city = None
        latest_remark = None
        latest_tag = None

        if checkpoints:
            latest_checkpoint = sorted(checkpoints, key=lambda x: datetime.strptime(x['date'], "%a, %d %b %Y %H:%M:%S %Z"), reverse=True)[0]
            latest_city = latest_checkpoint.get('city')
            latest_remark = latest_checkpoint.get('remark')
            latest_tag = latest_checkpoint.get('tag')

            doc.db_set('latest_location', latest_city)

        if tag == "Delivered":
            doc.db_set('status', "Completed")
            doc.db_set('tracking_status', "Delivered")
        elif tag == "InTransit":
            doc.db_set('tracking_status', "In Progress")

        if delivery_date:
            delivery_date_erp = datetime.strptime(delivery_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S")
            doc.db_set('delivery_date', delivery_date_erp)

        if expected_delivery_date:
            expected_delivery_date_erp = datetime.strptime(expected_delivery_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S")
            doc.db_set('expected_delivery_date', expected_delivery_date_erp)

        last_update_received = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc.db_set('last_update_received', last_update_received)
        doc.db_set('tracking_status_info', latest_remark)
        frappe.db.commit()

        return {
            "latest_checkpoint": {
                "latest_location": latest_city,
                "remark": latest_remark,
                "tag": latest_tag
            },
            "tracking_status_info": latest_remark,
            "delivery_date": delivery_date_erp if delivery_date else None,
            "expected_delivery_date": expected_delivery_date_erp if expected_delivery_date else None,
            "shipment_status": shipment_status,
            "tag": tag,
        }
    else:
        frappe.throw("Failed to retrieve shipment status: " + response.text)


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


def enqueue_bulk_log_update(custom_shipment_name):
    frappe.enqueue(
        method="erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.process_bulk_shipment_log",
        queue='long',
        timeout=600,
        is_async=True,
        custom_shipment_name=custom_shipment_name
    )

def process_bulk_shipment_log(custom_shipment_name):
    doc = frappe.get_doc("Custom Shipment", custom_shipment_name)

    for row in doc.receiver_details:
        log = frappe.new_doc("Bulk Shipment Log")
        log.parent_doctype_name = doc.name
        log.child_table_row = row.name

        # Copy matching fields from child table to log
        for field in [
            "receiver_party_type", "receiver_name", "address", "lengths", "width",
            "height", "weight", "count", "service_provider", "shipment_id",
            "shipment_amount", "status", "tracking_url", "carrier", "carrier_service",
            "awb_number", "tracking_status", "tracking_status_info", "last_update_received",
            "latest_location", "expected_delivery_date", "delivery_date"
        ]:
            if hasattr(row, field):
                setattr(log, field, getattr(row, field, None))

        log.insert(ignore_permissions=True)

    frappe.db.commit()


@frappe.whitelist()
def bg_log(doc, method):
    if doc.type == "Bulk Shipment":
        enqueue_bulk_log_update(doc.name)


@frappe.whitelist()
def create_bulk_shipment(docname, shipments_data):
    """
    Create shipments for multiple receivers from Bulk Shipment Log
    and update both Bulk Shipment Log and Custom Shipment
    """
    try:
        shipments_data = json.loads(shipments_data)
        
        # Enqueue the job for background processing
        frappe.enqueue(
            "erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment._enqueue_bulk_shipment_creation",
            docname=docname,
            shipments_data=shipments_data,
            timeout=600,
            now=False  # Process in background
        )
        
        return {
            'status': 'Queued',
            'message': 'Shipment creation has been queued for background processing'
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk shipment queue failed for {docname}")
        frappe.db.rollback()
        return {
            'status': 'Failed',
            'error': str(e)
        }

def _enqueue_bulk_shipment_creation(docname, shipments_data):
    """
    Background job to process bulk shipments
    """
    custom_shipment = frappe.get_doc("Custom Shipment", docname)
    results = []
    
    try:
        for shipment in shipments_data:
            child_name = shipment.get('child_name')
            receiver_name = shipment.get('receiver_name')
            service_data = shipment.get('service_data')
            item_data = shipment.get('item_data', {})
            
            try:
                # Generate the Bulk Shipment Log name
                log_name = f"{docname}-{child_name}"
                
                # Create the shipment
                shipment_result = create_single_shipment(
                    docname=docname,
                    log_name=log_name,
                    child_name=child_name,
                    receiver_name=receiver_name,
                    service_data=service_data,
                    item_data=item_data,
                    custom_shipment=custom_shipment
                )
                
                # Update the Bulk Shipment Log
                update_bulk_shipment_log(log_name, shipment_result)
                
                # Update the corresponding Custom Shipment receiver row
                update_custom_shipment_receiver(
                    docname=docname,
                    child_name=child_name,
                    shipment_result=shipment_result
                )
                
                results.append({
                    'parent_doctype_name': docname,
                    'child_table_row': child_name,
                    'receiver_name': receiver_name,
                    'name': log_name,
                    'status': shipment_result.get('status', 'Failed'),
                    'awb_number': shipment_result.get('awb_number'),
                    'service_provider': shipment_result.get('service_provider'),
                    'tracking_url': shipment_result.get('tracking_url'),
                    'error': shipment_result.get('error')
                })
                
            except Exception as e:
                error_msg = str(e)
                frappe.log_error(f"(child: {child_name}) - {error_msg}")
                results.append({
                    'child_name': child_name,
                    'receiver_name': receiver_name,
                    'status': 'Failed',
                    'error': error_msg
                })
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Bulk shipment creation failed for {docname}")
        frappe.db.rollback()
        raise e

def create_bulk_log(docname, log_name, child_name, receiver_name, service_data, item_data):
    """
    Create a new Bulk Shipment Log record with the specified name
    """
    bulk_log = frappe.new_doc("Bulk Shipment Log")
    bulk_log.name = log_name
    bulk_log.custom_shipment = docname
    bulk_log.child_name = child_name
    bulk_log.receiver_name = receiver_name
    bulk_log.status = "Pending"
    
    # Set service provider info
    if service_data:
        bulk_log.service_provider = service_data.get('description')
        bulk_log.carrier_service = service_data.get('selected_service_type')
        bulk_log.service_slug = service_data.get('slug')
    
    # Set item details
    if item_data:
        bulk_log.description = item_data.get('description')
        bulk_log.weight = item_data.get('weight', 0)
        dimensions = item_data.get('dimensions', {})
        bulk_log.width = dimensions.get('width', 0)
        bulk_log.height = dimensions.get('height', 0)
        bulk_log.lengths = dimensions.get('length', 0)
        bulk_log.count = dimensions.get('quantity', 1)
    
    bulk_log.insert(ignore_permissions=True)
    return bulk_log

def update_bulk_shipment_log(bulk_log, shipment_result):
    """
    Update Bulk Shipment Log with shipment details
    """
    # If bulk_log is a string (docname), get the document first
    if isinstance(bulk_log, str):
        bulk_log = frappe.get_doc("Bulk Shipment Log", bulk_log)
    
    if shipment_result.get('status') == 'Success':
        bulk_log.update({
            'awb_number': shipment_result.get('awb_number'),
            'service_provider': shipment_result.get('service_provider'),
            'tracking_url': shipment_result.get('tracking_url'),
            'status': 'Booked',
            'shipment_id': shipment_result.get('shipment_id'),
            'tracking_status': shipment_result.get('tracking_status', 'In Progress'),
            'tracking_status_info': shipment_result.get('tracking_status_info'),
            'carrier_service': shipment_result.get('carrier_service')
        })
        bulk_log.save()

def update_custom_shipment_receiver(docname, child_name, shipment_result):
    """
    Update the receiver row in Custom Shipment with shipment details
    """
    doc = frappe.get_doc("Custom Shipment", docname)
    
    for row in doc.receiver_details:
        if row.name == child_name:
            row.update({
                'awb_number': shipment_result.get('awb_number'),
                'service_provider': shipment_result.get('service_provider'),
                'tracking_url': shipment_result.get('tracking_url'),
                'status': 'Booked',
                'shipment_id': shipment_result.get('shipment_id'),
                'tracking_status': shipment_result.get('tracking_status', 'In Progress'),
                'tracking_status_info': shipment_result.get('tracking_status_info'),
                'carrier_service': shipment_result.get('carrier_service')
            })
            doc.save()
            break

@frappe.whitelist()
def create_single_shipment(docname, log_name, child_name, receiver_name, service_data, item_data, custom_shipment=None):
    """
    Create a single shipment using data from Bulk Shipment Log
    """
    if not custom_shipment:
        custom_shipment = frappe.get_doc("Custom Shipment", docname)
    
    # Get pickup address from Custom Shipment
    pickup_address = frappe.db.get_value('Address', custom_shipment.address, 
        ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'phone', 'email_id'], 
        as_dict=1)
    
    def get_country_code(country_name):
        country = frappe.get_doc('Country', country_name)
        return country.code.upper()

    pickup_country_code = get_country_code(pickup_address.country)
    delivery_country_code = pickup_country_code  # Assuming same country for delivery
    
    api_token = frappe.db.get_single_value('eShipz Settings', 'api_token')
    if not api_token:
        frappe.throw("API token not found in eShipz Settings")

    url = "https://app.eshipz.com/api/v1/create-shipments"
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    # Prepare parcels data using item_data
    parcels = [{
        "description": item_data.get('description', custom_shipment.description_of_content),
        "box_type": custom_shipment.shipment_type,
        "quantity": item_data.get('dimensions', {}).get('quantity', 1),
        "weight": {
            "value": item_data.get('weight', 0),
            "unit": "kg"
        },
        "dimension": {
            "width": item_data.get('dimensions', {}).get('width', 0),
            "height": item_data.get('dimensions', {}).get('height', 0),
            "length": item_data.get('dimensions', {}).get('length', 0),
            "unit": "cm"
        },
        "items": [{
            "description": item_data.get('description', custom_shipment.description_of_content),
            "origin_country": pickup_country_code,
            "quantity": item_data.get('dimensions', {}).get('quantity', 1),
            "price": {
                "amount": custom_shipment.value_of_goods,
                "currency": "INR"
            },
            "weight": {
                "value": item_data.get('weight', 0),
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
        "purpose": custom_shipment.kly_purpose,
        "order_source": "erpnext",
        "is_document": False,
        "parcel_contents": custom_shipment.description_of_content,
        "service_type": service_data.get('selected_service_type'),
        "charged_weight": {
            "unit": "KG",
            "value": item_data.get('weight', 0)
        },
        "customer_reference": log_name,
        "invoice_number": " ",
        "invoice_date": " ",
        "is_reverse": False,
        "is_cod": False,
        "collect_on_delivery": {"amount": 0, "currency": "INR"},
        "shipment": {
            "ship_from": {
                "contact_name": custom_shipment.pickup_contact_person,
                "company_name": custom_shipment.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "country": pickup_country_code,
                "type": custom_shipment.kly_pickup_type
            },
            "ship_to": {
                "contact_name": receiver_name,
                "company_name": receiver_name,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "country": delivery_country_code,
                "type": custom_shipment.kly_delivery_type
            },
            "return_to": {
                "contact_name": custom_shipment.pickup_contact_person,
                "company_name": custom_shipment.company,
                "street1": pickup_address.address_line1,
                "street2": pickup_address.address_line2,
                "city": pickup_address.city,
                "state": pickup_address.state,
                "postal_code": pickup_address.pincode,
                "phone": pickup_address.phone,
                "email": pickup_address.email_id,
                "country": pickup_country_code,
                "type": custom_shipment.kly_pickup_type
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
            error_msg = result.get('meta', {}).get('message', 'Unknown error')
            frappe.log_error(f"{error_msg} for {receiver_name}")
            frappe.throw(error_msg)
    else:
        error_msg = response.json().get("msg", response.text)
        frappe.log_error(f"API Failed with {error_msg}")
        frappe.throw(f"API request failed with status {response.status_code}: {error_msg}")