// Copyright (c) 2025, KlyONIX Tech Consulting Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Custom Shipment", {
    refresh: function(frm) {
        // Check if eShipz is enabled
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'eShipz Settings',
                fieldname: 'enabled'
            },
            callback: function(r) {
                if (r.message && r.message.enabled == 1) {
                    setup_shipment_buttons(frm);
                }
            }
        });
        
        const deliveryHtml = build_delivery_address_html(frm);
    if (frm.fields_dict.delivery_address && frm.fields_dict.delivery_address.$wrapper) {
        frm.fields_dict.delivery_address.$wrapper.html(deliveryHtml);
    }

    // Re-set the pickup contact HTML
    if (frm.doc.pickup_contact_person) {
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "User",
                name: frm.doc.pickup_contact_person
            },
            callback: function (response) {
                const user = response.message;
                if (user && frm.fields_dict.pick_up_contact && frm.fields_dict.pick_up_contact.$wrapper) {
                    let html = `
                        <div style="margin-top:10px;">
                            <p><strong>Pickup Contact Details:</strong></p>
                            <p><strong>Email:</strong> ${user.email || 'N/A'}</p>
                            <p><strong>Phone:</strong> ${user.phone || 'N/A'}</p>
                        </div>`;
                    frm.fields_dict.pick_up_contact.$wrapper.html(html);
                }
            }
        });
    } else if (frm.fields_dict.pick_up_contact && frm.fields_dict.pick_up_contact.$wrapper) {
        frm.fields_dict.pick_up_contact.$wrapper.html('');
    }

    // Your existing Add Parcel Template button logic
    if (!frm.custom_buttons || !frm.custom_buttons['Add Parcel Template'] && (frm.doc.docstatus === 0 && frm.doc.type === "Bulk Shipment")) {
        frm.add_custom_button(__('Add Parcel Template'), function () {
            frm.trigger('open_parcel_template_dialog');
        }, __('Tools')).addClass('btn-add-parcel-template');
    }

    const btn = frm.page.inner_toolbar.find('.btn-add-parcel-template');
    if (btn) {
        btn.prop('disabled', !frm.doc.receiver_details || frm.doc.receiver_details.length === 0);
    }
    
    },
    pickup_contact_person: function (frm) {
        if (frm.doc.pickup_contact_person) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "User",
                    name: frm.doc.pickup_contact_person
                },
                callback: function (response) {
                    const user = response.message;
                    if (user && frm.fields_dict.pick_up_contact && frm.fields_dict.pick_up_contact.$wrapper) {
                        let html = `
                            <div style="margin-top:10px;">
                                <p><strong>Pickup Contact Details:</strong></p>
                                <p><strong>Email:</strong> ${user.email || 'N/A'}</p>
                                <p><strong>Phone:</strong> ${user.phone || 'N/A'}</p>
                            </div>`;
                        frm.fields_dict.pick_up_contact.$wrapper.html(html);
                    }
                }
            });
        } else if (frm.fields_dict.pick_up_contact && frm.fields_dict.pick_up_contact.$wrapper) {
            frm.fields_dict.pick_up_contact.$wrapper.html('');
        }
    },
    
    add_template: function (frm) {
		if (frm.doc.parcel_template) {
			frappe.model.with_doc("Shipment Parcel Template", frm.doc.parcel_template, () => {
				let parcel_template = frappe.model.get_doc(
					"Shipment Parcel Template",
					frm.doc.parcel_template
				);
				let row = frappe.model.add_child(frm.doc, "Shipment Parcel", "shipment_parcel");
				row.length = parcel_template.length;
				row.width = parcel_template.width;
				row.height = parcel_template.height;
				row.weight = parcel_template.weight;
				frm.refresh_fields("shipment_parcel");
			});
		}
	},
    
    before_save: function (frm) {
        const html = build_delivery_address_html(frm);
        frm.fields_dict.delivery_address.$wrapper.html(html);
    },
    
    filter_doctype: function (frm) {
        if (!frm.doc.filter_doctype) return;

        frappe.model.with_doctype(frm.doc.filter_doctype, () => {
            const meta = frappe.get_meta(frm.doc.filter_doctype);
            let options = [];

            frm.__link_field_map = {};

            meta.fields.forEach(df => {
                if (df.fieldtype === "Link") {
                    options.push(df.label);
                    frm.__link_field_map[df.label] = df.fieldname;
                    frm.__link_field_map[df.fieldname] = df.options;
                }
            });

            frm.set_df_property("sub_filter", "options", options.join("\n"));
            frm.set_df_property("sub_filter_2", "options", options.join("\n"));
            frm.set_df_property("sub_filter_3", "options", options.join("\n"));
            frm.refresh_field("sub_filter");
            frm.refresh_field("sub_filter_2");
            frm.refresh_field("sub_filter_3");

            frm.set_value("sub_filter", null);
            frm.set_value("dynamic_link_ref", null);
            frm.set_value("value", null);

            frm.set_value("sub_filter_2", null);
            frm.set_value("dynamic_link_ref_2", null);
            frm.set_value("value_2", null);

            frm.set_value("sub_filter_3", null);
            frm.set_value("dynamic_link_ref_3", null);
            frm.set_value("value_3", null);
        });
    },

    // Update link target doctype
    sub_filter: function (frm) {
        const selected_label = frm.doc.sub_filter;
        const fieldname = frm.__link_field_map?.[selected_label];

        if (!fieldname) {
            frm.set_value("dynamic_link_ref", null);
            frm.set_value("value", null);
            return;
        }

        const link_target_doctype = frm.__link_field_map[fieldname];
        frm.set_value("dynamic_link_ref", link_target_doctype);
        frm.set_value("value", null);
        frm.refresh_field("value");
    },

    sub_filter_2: function (frm) {
        const selected_label = frm.doc.sub_filter_2;
        const fieldname = frm.__link_field_map?.[selected_label];

        if (!fieldname) {
            frm.set_value("dynamic_link_ref_2", null);
            frm.set_value("value_2", null);
            return;
        }

        const link_target_doctype = frm.__link_field_map[fieldname];
        frm.set_value("dynamic_link_ref_2", link_target_doctype);
        frm.set_value("value_2", null);
        frm.refresh_field("value_2");
    },

    sub_filter_3: function (frm) {
        const selected_label = frm.doc.sub_filter_3;
        const fieldname = frm.__link_field_map?.[selected_label];

        if (!fieldname) {
            frm.set_value("dynamic_link_ref_3", null);
            frm.set_value("value_3", null);
            return;
        }

        const link_target_doctype = frm.__link_field_map[fieldname];
        frm.set_value("dynamic_link_ref_3", link_target_doctype);
        frm.set_value("value_3", null);
        frm.refresh_field("value_3");
    },

apply_filter: function(frm) {
    const { filter_doctype, sub_filter, value, sub_filter_2, value_2, sub_filter_3, value_3 } = frm.doc;

    if (!filter_doctype) {
        frappe.msgprint("Please select Filter Doctype.");
        return;
    }

    // Build filters object
    const filters = {};
    const fieldname = frm.__link_field_map?.[sub_filter];
    const fieldname2 = frm.__link_field_map?.[sub_filter_2];
    const fieldname3 = frm.__link_field_map?.[sub_filter_3];
    
    if (sub_filter && value && fieldname) {
        filters[fieldname] = value;
    }
    
    if (sub_filter_2 && value_2 && fieldname2) {
        filters[fieldname2] = value_2;
    }
    
    if (sub_filter_3 && value_3 && fieldname3) {
        filters[fieldname3] = value_3;
    }

    frappe.call({
        method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.get_filtered_records_with_addresses',
        args: { 
            doctype: filter_doctype,
            filters: filters
        },
        freeze: true,
        callback: function(response) {
            if (response.message) {
                process_records(frm, response.message);
            } else {
                frappe.msgprint(__('No records found matching the criteria'));
            }
        }
    });
    
    function process_records(frm, records) {
        frm.clear_table("receiver_details");
        
        records.forEach(record => {
            // Use primary address if available, otherwise first address
            const address = record.addresses.find(a => a.is_primary_address) || 
                          (record.addresses.length > 0 ? record.addresses[0] : null);
            
            // Use primary contact if available, otherwise first contact
            const contact = record.contacts.find(c => c.is_primary_contact) || 
                         (record.contacts.length > 0 ? record.contacts[0] : null);
            
            const child = frm.add_child("receiver_details");
            child.receiver_party_type = frm.doc.filter_doctype;
            child.receiver_name = record.name;
            
            if (address) {
                child.address = address.name;
                child.address_line_1 = address.address_line1;
                child.address_line_2 = address.address_line2;
                child.city = address.city;
                child.state = address.state;
                child.postal_code = address.pincode;
                child.country = address.country;
            }
            
            if (contact) {
                child.receiver_contact = contact.phone;
                child.receiver_email = contact.email_id;
            }
        });

        frm.refresh_field("receiver_details");
    }
},

    // Dialog to enter parcel template info
    open_parcel_template_dialog: function (frm) {
        if (!frm.doc.receiver_details || frm.doc.receiver_details.length === 0) {
            frappe.msgprint(__("Please add at least one receiver before adding parcel template"));
            return;
        }

        const dialog = new frappe.ui.Dialog({
            title: __('Add Parcel Template'),
            fields: [
                {
                    label: __('Box Type'),
                    fieldname: 'box_type',
                    fieldtype: 'Select',
                    options: ['Equal Box Count', 'Different Box Count'],
                    default: 'Equal Box Count',
                    reqd: 1
                },
                { label: __('Length (cm)'), fieldname: 'lengths', fieldtype: 'Int', reqd: 1, min: 1 },
                { label: __('Width (cm)'), fieldname: 'width', fieldtype: 'Int', reqd: 1, min: 1 },
                { label: __('Height (cm)'), fieldname: 'height', fieldtype: 'Int', reqd: 1, min: 1 },
                { label: __('Weight (kg)'), fieldname: 'weight', fieldtype: 'Float', reqd: 1, min: 0.1 },
                { label: __('Count'), fieldname: 'count', fieldtype: 'Int', reqd: 1, min: 1, default: 1 },
                { fieldname: 'receiver_details_section', fieldtype: 'Section Break' },
                { fieldname: 'receiver_details_html', fieldtype: 'HTML' }
            ],
            primary_action_label: __('Submit'),
            primary_action(values) {
                if (!values) return;

                if (values.lengths <= 0 || values.width <= 0 || values.height <= 0 || values.weight <= 0 || values.count <= 0) {
                    frappe.msgprint(__("Please enter valid positive values for all dimensions"));
                    return;
                }

                frm.events.apply_parcel_template(frm, values);
                dialog.hide();
            }
        });

        let html = `<div style="max-height: 200px; overflow-y: auto;">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Receiver Party Type')}</th>
                        <th>${__('Receiver Name')}</th>
                        <th>${__('Email')}</th>
                        <th>${__('Contact')}</th>
                        <th>${__('Address')}</th>
                    </tr>
                </thead>
                <tbody>`;

        frm.doc.receiver_details.forEach(row => {
            html += `<tr>
                <td>${row.receiver_party_type || ''}</td>
                <td>${row.receiver_name || ''}</td>
                <td>${row.receiver_email || 'N/A'}</td>
                <td>${row.receiver_contact || 'N/A'}</td>
                <td>${row.address || 'N/A'}</td>
            </tr>`;
        });

        html += `</tbody></table></div>`;
        dialog.set_value('receiver_details_html', html);
        dialog.show();
    },

    // Apply the parcel template values to receiver details
    apply_parcel_template: function (frm, values) {
        const { box_type, lengths, width, height, weight, count } = values;

        if (box_type === 'Equal Box Count') {
            frm.doc.receiver_details.forEach(row => {
                row.lengths = lengths;
                row.width = width;
                row.height = height;
                row.weight = weight;
                row.count = count;
            });
            frm.refresh_field('receiver_details');
            frappe.show_alert(__('Parcel details applied to all receivers'));
        } else {
            const items_dialog = new frappe.ui.Dialog({
                title: __('Enter Parcel Details for Each Receiver'),
                fields: [
                    { fieldname: 'receiver_details_section', fieldtype: 'Section Break' },
                    { fieldname: 'receiver_details_html', fieldtype: 'HTML' }
                ],
                size: 'large'
            });

            let html = `<div style="max-height: 400px; overflow-y: auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>${__('Receiver')}</th>
                            <th>${__('Length (cm)')}</th>
                            <th>${__('Width (cm)')}</th>
                            <th>${__('Height (cm)')}</th>
                            <th>${__('Weight (kg)')}</th>
                            <th>${__('Count')}</th>
                        </tr>
                    </thead>
                    <tbody>`;

            frm.doc.receiver_details.forEach((row, idx) => {
                html += `<tr>
                    <td>${row.receiver_name || ''}</td>
                    <td><input type="number" class="form-control lengths-input" data-idx="${idx}" value="${row.lengths || lengths}" min="1"></td>
                    <td><input type="number" class="form-control width-input" data-idx="${idx}" value="${row.width || width}" min="1"></td>
                    <td><input type="number" class="form-control height-input" data-idx="${idx}" value="${row.height || height}" min="1"></td>
                    <td><input type="number" step="0.01" class="form-control weight-input" data-idx="${idx}" value="${row.weight || weight}" min="0.1"></td>
                    <td><input type="number" class="form-control count-input" data-idx="${idx}" value="${row.count || count}" min="1"></td>
                </tr>`;
            });

            html += `</tbody></table></div>`;
            items_dialog.set_value('receiver_details_html', html);

            items_dialog.set_primary_action(__('Submit'), function () {
                let valid = true;

                frm.doc.receiver_details.forEach((row, idx) => {
                    const lengths_val = parseInt(items_dialog.$wrapper.find(`.lengths-input[data-idx="${idx}"]`).val());
                    const width_val = parseInt(items_dialog.$wrapper.find(`.width-input[data-idx="${idx}"]`).val());
                    const height_val = parseInt(items_dialog.$wrapper.find(`.height-input[data-idx="${idx}"]`).val());
                    const weight_val = parseFloat(items_dialog.$wrapper.find(`.weight-input[data-idx="${idx}"]`).val());
                    const count_val = parseInt(items_dialog.$wrapper.find(`.count-input[data-idx="${idx}"]`).val());

                    if (!lengths_val || !width_val || !height_val || !weight_val || !count_val ||
                        lengths_val <= 0 || width_val <= 0 || height_val <= 0 || weight_val <= 0 || count_val <= 0) {
                        valid = false;
                        frappe.msgprint(__("Please enter valid positive values for receiver: ") + row.receiver_name);
                        return false;
                    }

                    row.lengths = lengths_val;
                    row.width = width_val;
                    row.height = height_val;
                    row.weight = weight_val;
                    row.count = count_val;
                });

                if (!valid) return;

                frm.refresh_field('receiver_details');
                items_dialog.hide();
                frappe.show_alert(__('Parcel details applied to all receivers'));
            });

            items_dialog.show();
        }
    }
    
});

function cancel_shipment(frm) {
    if (frm.doc.type === "Bulk Shipment" && frm.doc.receiver_details) {
        // For bulk shipments, show dialog with list of receivers and selection options
        let cancelableShipments = [];
        
        // Add main shipment if cancelable
        if (frm.doc.awb_number && frm.doc.status != 'Cancelled') {
            cancelableShipments.push({
                type: 'main',
                name: frm.doc.name_of_the_receiver || 'Main Shipment',
                awb: frm.doc.awb_number,
                status: frm.doc.tracking_status || 'N/A',
                selected: true // Default selected
            });
        }
        
        // Add receiver shipments if cancelable
        frm.doc.receiver_details.forEach(r => {
            if (r.awb_number && r.status != 'Cancelled') {
                cancelableShipments.push({
                    type: 'receiver',
                    idx: r.idx,
                    name: r.receiver_name || 'N/A',
                    awb: r.awb_number,
                    status: r.tracking_status || 'N/A',
                    selected: true // Default selected
                });
            }
        });
        
        if (cancelableShipments.length === 0) {
            frappe.msgprint(__('No shipments available to cancel'));
            return;
        }
        
        let dialog = new frappe.ui.Dialog({
            title: __('Cancel Shipments'),
            fields: [
                {
                    fieldname: 'selection_type',
                    fieldtype: 'Select',
                    label: __('Cancel Option'),
                    options: ['All Shipments', 'Selected Shipments'],
                    default: 'All Shipments',
                    reqd: 1,
                    change: function() {
                        const isAll = dialog.get_value('selection_type') === 'All Shipments';
                        dialog.$wrapper.find('.shipment-checkbox').prop('checked', isAll);
                    }
                },
                {
                    fieldname: 'shipments_section',
                    fieldtype: 'Section Break',
                    label: __('Shipments to Cancel'),
                    depends_on: 'eval:doc.selection_type == "Selected Shipments"'
                },
                {
                    fieldname: 'shipments_html',
                    fieldtype: 'HTML',
                    depends_on: 'eval:doc.selection_type == "Selected Shipments"'
                }
            ],
            primary_action_label: __('Cancel Shipments'),
            primary_action: function() {
                const selectionType = dialog.get_value('selection_type');
                let shipmentsToCancel = [];
                
                if (selectionType === 'All Shipments') {
                    shipmentsToCancel = cancelableShipments;
                } else {
                    // Get selected shipments
                    dialog.$wrapper.find('.shipment-checkbox:checked').each(function() {
                        const idx = $(this).data('idx');
                        const type = $(this).data('type');
                        const shipment = cancelableShipments.find(s => 
                            s.type === type && (type === 'main' || s.idx === idx)
                        );
                        if (shipment) shipmentsToCancel.push(shipment);
                    });
                }
                
                if (shipmentsToCancel.length === 0) {
                    frappe.msgprint(__('Please select at least one shipment to cancel'));
                    return;
                }
                
                dialog.hide();
                process_cancellation(frm, shipmentsToCancel);
            }
        });
        
        // Build the shipments HTML table
        let html = `
            <div class="shipment-selection-container" style="max-height: 300px; overflow-y: auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th><input type="checkbox" class="select-all-checkbox" checked></th>
                            <th>${__('Shipment')}</th>
                            <th>${__('AWB Number')}</th>
                            <th>${__('Status')}</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        cancelableShipments.forEach(shipment => {
            html += `
                <tr>
                    <td>
                        <input type="checkbox" class="shipment-checkbox" 
                               data-type="${shipment.type}" 
                               data-idx="${shipment.idx || ''}" 
                               checked>
                    </td>
                    <td>${shipment.name}</td>
                    <td>${shipment.awb}</td>
                    <td>${shipment.status}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            <style>
                .shipment-checkbox, .select-all-checkbox {
                    margin: 0;
                    vertical-align: middle;
                }
                .select-all-checkbox {
                    margin-left: 8px;
                }
            </style>
        `;
        
        dialog.set_value('shipments_html', html);
        
        // Add select all toggle
        dialog.$wrapper.on('change', '.select-all-checkbox', function() {
            const isChecked = $(this).prop('checked');
            dialog.$wrapper.find('.shipment-checkbox').prop('checked', isChecked);
        });
        
        dialog.show();
    } else {
        // For single shipments, show simple confirmation
        frappe.confirm(
            __('Are you sure you want to cancel this shipment?'),
            function() {
                process_cancellation(frm, [{
                    type: 'main',
                    name: frm.doc.name_of_the_receiver || 'Main Shipment',
                    awb: frm.doc.awb_number,
                    status: frm.doc.tracking_status || 'N/A'
                }]);
            }
        );
    }
}

function process_cancellation(frm, shipmentsToCancel) {
    let dialog = new frappe.ui.Dialog({
        title: __('Cancelling Shipment'),
        fields: [
            {
                fieldname: 'progress',
                fieldtype: 'HTML',
                options: `
                    <div class="text-center">
                        <p>${__('Cancelling shipment, please wait...')}</p>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar progress-bar-striped active" role="progressbar" 
                                 style="width: 100%;"></div>
                        </div>
                    </div>
                `
            }
        ]
    });
    
    dialog.show();
    
    frappe.call({
        method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.cancel_shipment',
        args: { 
            docname: frm.doc.name,
            shipments_to_cancel: shipmentsToCancel 
        },
        freeze: true,
        callback: function(r) {
            dialog.hide();
            if (r.message) {
                show_cancellation_results(frm, r.message);
                frm.reload_doc();
            } else {
                frappe.msgprint(__('No response received from the server'));
            }
        },
        error: function() {
            dialog.hide();
            frappe.msgprint(__('Error cancelling shipment'));
        }
    });
}

function show_cancellation_results(frm, results) {
    let hasErrors = false;
    
    if (frm.doc.type === "Single Shipment") {
        hasErrors = results.main_shipment?.status !== "Success";
    } else {
        hasErrors = results.receivers?.some(r => r.status !== "Success");
    }
    
    let html = `
        <div class="cancellation-results">
            <h5>${__('Cancellation Results')}</h5>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Shipment')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Details')}</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    if (frm.doc.type === "Single Shipment") {
        html += `
            <tr class="${results.main_shipment.status === 'Success' ? 'success-row' : 'danger-row'}">
                <td>Main Shipment</td>
                <td>${results.main_shipment.status}</td>
                <td>${results.main_shipment.status === 'Success' ? 
                    results.main_shipment.message : 
                    results.main_shipment.error}</td>
            </tr>
        `;
    } else {
        results.receivers.forEach(receiver => {
            html += `
                <tr class="${receiver.status === 'Success' ? 'success-row' : 'danger-row'}">
                    <td>${receiver.receiver_name || 'N/A'}</td>
                    <td>${receiver.status}</td>
                    <td>${receiver.status === 'Success' ? 
                        receiver.message : 
                        receiver.error}</td>
                </tr>
            `;
        });
    }
    
    html += `
                </tbody>
            </table>
        </div>
        <style>
            .success-row { background-color: #f0fff0; }
            .danger-row { background-color: #fff0f0; }
            .cancellation-results { max-height: 60vh; overflow-y: auto; }
        </style>
    `;
    
    frappe.msgprint({
        title: __('Cancellation Complete'),
        indicator: hasErrors ? 'orange' : 'green',
        message: html
    });
}

function setup_shipment_buttons(frm) {
    if (frm.doc.docstatus == 1 && frm.doc.status != "Cancelled") {
        // Remove existing buttons first to prevent duplicates
        frm.page.clear_primary_action();
        frm.page.clear_secondary_action();
        
        // Main Create Shipment button
        frm.add_custom_button(__('Create Shipment'), function() {
            fetch_services_and_show_popup(frm);
        }).addClass('btn-success').css({'background':'#239b56', 'color':'white'});
        
        
        // Additional buttons if AWB exists
        if (frm.doc.awb_number && frm.doc.status != 'Cancelled') {
            frm.add_custom_button(__('Download Label'), function() {
                window.open(frm.doc.tracking_url, '_blank');
            }).addClass('btn-primary');
            
            frm.add_custom_button(__('Update Status'), function() {
                            frappe.call({
                                method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.update_status',
                                args: {
                                    docname: frm.docname
                                },
                                freeze: true,
                                freeze_message: __('Getting Status... Please wait...⏳☕'),
                                callback: function(r) {
                                    if (r.message) {
                                        frappe.msgprint(__('Status Updated'));
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }).addClass('btn-info').css({'background':'#239b56', 'color':'white'});
            
            frm.add_custom_button(__('Track Shipment'), function() {
                window.open(`https://track.eshipz.com/track?awb=${frm.doc.awb_number}&slug=${frm.doc.service_provider}`, '_blank');
            }).addClass('btn-info');
        }
    }
}



function fetch_services_and_show_popup(frm) {
    if (frm.doc.type === "Bulk Shipment") {
        frappe.call({
            method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.fetch_available_services',
            args: { docname: frm.docname },
            freeze: true,
            freeze_message: __("Fetching Available Services Please Wait⏳..."),
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    // Filter out receivers that already have AWB and Booked status
                    const filteredServices = r.message.filter(service => {
                        // Find the receiver in the document
                        const receiver = frm.doc.receiver_details.find(rd => 
                            rd.receiver_name === service.receiver_name
                        );
                        // Only include if receiver doesn't have AWB or status isn't Booked
                        return !(receiver && receiver.awb_number && receiver.status === "Booked");
                    });
                    
                    if (filteredServices.length > 0) {
                        show_service_selection_popup(filteredServices);
                    } else {
                        frappe.msgprint(__('All receivers already have shipments booked. No services to select.'));
                    }
                } else {
                    frappe.msgprint(__('No shipping services available for this shipment'));
                }
            }
        });
    }
    else if (frm.doc.type === "Single Shipment") {
        frappe.call({
            method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.fetch_single_available_services',
            args: { docname: frm.docname },
            freeze: true,
            freeze_message: __("Fetching Available Services Please Wait⏳..."),
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    show_single_service_popup(r.message);
                } else {
                    frappe.msgprint(__('No shipping services available for this shipment'));
                }
            }
        });
    }
}

function show_service_selection_popup(services) {
    let dialog = new frappe.ui.Dialog({
        title: __('Select Shipping Services'),
        fields: [
            {
                fieldname: 'services_section',
                fieldtype: 'Section Break',
                label: __('Available Services')
            },
            {
                fieldname: 'services_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Create Selected Shipments'),
        primary_action: function() {
            create_selected_shipments(dialog, services);
        }
    });

    // Build the services HTML
    let html = build_services_html(services);
    dialog.fields_dict.services_html.$wrapper.html(html);
    
    dialog.show();
}




function build_services_html(services) {
    // Group by receiver
    let receivers = {};
    services.forEach(service => {
        if (!receivers[service.receiver_idx]) {
            receivers[service.receiver_idx] = {
                name: service.receiver_name,
                services: []
            };
        }
        receivers[service.receiver_idx].services.push(service);
    });

    let html = `
        <div class="service-selection-container">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Receiver')}</th>
                        <th>${__('Available Services')}</th>
                    </tr>
                </thead>
                <tbody>
    `;

    Object.keys(receivers).forEach(receiverIdx => {
        let receiver = receivers[receiverIdx];
        let hasDefaultSet = false;
        
        html += `
            <tr>
                <td>${receiver.name}</td>
                <td>
                    <select class="form-control service-select" data-receiver-idx="${receiverIdx}">
                        <option value="">${__('Select a service...')}</option>
        `;
        
        receiver.services.forEach(service => {
            if (service.technicality && service.technicality.length > 0) {
                service.technicality.forEach(tech => {
                    let serviceJson = JSON.stringify(service)
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&apos;');
                    
                    const selected = !hasDefaultSet ? 'selected' : '';
                    if (!hasDefaultSet) hasDefaultSet = true;
                    
                    html += `
                        <option value="${service.vendor_id}" 
                                data-service="${serviceJson}"
                                data-service-type="${tech.service_type}"
                                ${selected}>
                            ${service.slug} - ${tech.service_type} (${service.vendor_id})
                        </option>
                    `;
                });
            } else {
                let serviceJson = JSON.stringify(service)
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&apos;');
                
                const selected = !hasDefaultSet ? 'selected' : '';
                if (!hasDefaultSet) hasDefaultSet = true;
                
                html += `
                    <option value="${service.vendor_id}" 
                            data-service="${serviceJson}"
                            data-service-type="standard"
                            ${selected}>
                        ${service.slug} - Standard Service (${service.vendor_id})
                    </option>
                `;
            }
        });
        
        html += `
                    </select>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
            <div class="alert alert-info">
                ${__('Select services for each receiver and click "Create Selected Shipments"')}
            </div>
        </div>
        <style>
            .service-selection-container { max-height: 60vh; overflow-y: auto; }
            .service-select { width: 100%; margin: 5px 0; }
            .table { margin-bottom: 10px; }
        </style>
    `;

    return html;
}

function show_single_service_popup(services) {
    let dialog = new frappe.ui.Dialog({
        title: __('Available Shipping Services'),
        fields: [
            {
                fieldname: 'services_section',
                fieldtype: 'Section Break',
                label: __('Select a Service')
            },
            {
                fieldname: 'services_html',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });

    // Build the services HTML table with select buttons
    let html = `
        <div class="service-table-container">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Service Type')}</th>
                        <th>${__('Description')}</th>
                        <th>${__('Slug')}</th>
                        <th>${__('Vendor ID')}</th>
                        <th>${__('Action')}</th>
                    </tr>
                </thead>
                <tbody>
    `;

    services.forEach(service => {
        if (service.technicality && service.technicality.length > 0) {
            service.technicality.forEach(tech => {
                // Create a clean service object with only the needed properties
                let serviceData = {
                    vendor_id: service.vendor_id,
                    description: service.description,
                    slug: service.slug,
                    selected_service_type: tech.service_type
                };
                
                html += `
                    <tr>
                        <td>${tech.service_type || 'N/A'}</td>
                        <td>${tech.description || service.description || 'N/A'}</td>
                        <td>${service.slug || 'N/A'}</td>
                        <td>${service.vendor_id || 'N/A'}</td>
                        <td>
                            <button class="btn btn-primary btn-xs select-service-btn" 
                                    data-service='${JSON.stringify(serviceData).replace(/'/g, "\\'")}'>
                                ${__('Select')}
                            </button>
                        </td>
                    </tr>
                `;
            });
        } else {
            // For services without technicality
            let serviceData = {
                vendor_id: service.vendor_id,
                description: service.description,
                slug: service.slug,
                selected_service_type: 'standard'
            };
            
            html += `
                <tr>
                    <td>Standard</td>
                    <td>${service.description || 'N/A'}</td>
                    <td>${service.slug || 'N/A'}</td>
                    <td>${service.vendor_id || 'N/A'}</td>
                    <td>
                        <button class="btn btn-primary btn-xs select-service-btn" 
                                data-service='${JSON.stringify(serviceData).replace(/'/g, "\\'")}'>
                            ${__('Select')}
                        </button>
                    </td>
                </tr>
            `;
        }
    });

    html += `
                </tbody>
            </table>
        </div>
        <style>
            .service-table-container { max-height: 60vh; overflow-y: auto; }
            .table { margin-bottom: 15px; }
            .table th { background-color: #f7f7f7; }
            .select-service-btn { width: 80px; }
        </style>
    `;

    dialog.fields_dict.services_html.$wrapper.html(html);
    
    // Add click handler for select buttons
    dialog.$wrapper.on('click', '.select-service-btn', function() {
        let $btn = $(this);
        let service = JSON.parse($btn.attr('data-service'));
        
        // Prepare parcel data
        let parcels = [];
        if (cur_frm.doc.shipment_parcel && cur_frm.doc.shipment_parcel.length > 0) {
            parcels = cur_frm.doc.shipment_parcel.map(parcel => ({
                description: cur_frm.doc.description_of_content,
                box_type: cur_frm.doc.shipment_type,
                weight: {
                    value: parcel.weight,
                    unit: "kg"
                },
                dimension: {
                    width: parcel.width,
                    height: parcel.height,
                    length: parcel.length,
                    unit: "cm"
                },
                items: [{
                    description: cur_frm.doc.description_of_content,
                    origin_country: "IN", // Assuming India as origin
                    quantity: parcel.count,
                    price: {
                        amount: cur_frm.doc.value_of_goods,
                        currency: "INR"
                    },
                    weight: {
                        unit: "kg",
                        value: parcel.weight
                    }
                }]
            }));
        }
        
        create_shipment(service, parcels);
        dialog.hide();
    });
    
    dialog.show();
}

function create_shipment(service, parcels) {
    let dialog = new frappe.ui.Dialog({
        title: __('Creating Shipment'),
        fields: [
            {
                fieldname: 'progress',
                fieldtype: 'HTML',
                options: `
                    <div class="text-center">
                        <p>${__('Creating shipment, please wait...')}</p>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar progress-bar-striped active" role="progressbar" 
                                 style="width: 100%;"></div>
                        </div>
                    </div>
                `
            }
        ]
    });
    
    dialog.show();
    
    frappe.call({
        method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.create_shipment',
        args: {
            docname: cur_frm.docname,
            selected_service: JSON.stringify(service),
            item_data: JSON.stringify({
                parcels: parcels,
                description_of_content: cur_frm.doc.description_of_content,
                value_of_goods: cur_frm.doc.value_of_goods,
                shipment_type: cur_frm.doc.shipment_type
            })
        },
        freeze: true,
        callback: function(r) {
            dialog.hide();
            if (r.message) {
                if (r.message.awb_number) {
                    frappe.show_alert({
                        message: __('Shipment created successfully! AWB: {0}', [r.message.awb_number]),
                        indicator: 'green'
                    });
                    
                    // Update form fields
                    cur_frm.set_value('awb_number', r.message.awb_number);
                    cur_frm.set_value('tracking_url', r.message.label_url);
                    cur_frm.set_value('service_provider', r.message.service_provider);
                    cur_frm.set_value('status', 'Booked');
                    cur_frm.set_value('tracking_status', 'In Progress');
                    cur_frm.set_value('shipment_id', r.message.shipment_id);
                    cur_frm.set_value('carrier_service', r.message.carrier_service);
                    
                    // Refresh the form
                    cur_frm.reload_doc();
                    
                    // Update buttons
                    setup_shipment_buttons(cur_frm);
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: r.message.error || __('Failed to create shipment')
                    });
                }
            } else {
                frappe.msgprint(__('No response received from the server'));
            }
        },
        error: function(r) {
            dialog.hide();
            let errorMsg = r.responseJSON && r.responseJSON.exc ? 
                r.responseJSON.exc.join('\n') : 
                __('Unknown error occurred');
            frappe.msgprint(__('Error creating shipment: ') + errorMsg);
        }
    });
}

function create_selected_shipments(dialog, all_services) {
    try {
        let selected_services = [];
        let hasSelection = false;
        
        dialog.$wrapper.find('.service-select').each(function() {
            let $select = $(this);
            let selectedOption = $select.find('option:selected');
            
            if (selectedOption.val()) {
                hasSelection = true;
                let receiverIdx = $select.data('receiver-idx');
                let serviceData = selectedOption.attr('data-service');
                let serviceType = selectedOption.attr('data-service-type');
                
                // Fix JSON parsing - handle both string and object cases
                let service;
                try {
                    if (typeof serviceData === 'string') {
                        service = JSON.parse(serviceData);
                    } else {
                        service = serviceData;
                    }
                } catch (e) {
                    console.error('Error parsing service data:', e);
                    frappe.msgprint(__('Error processing service data'));
                    return;
                }
                
                selected_services.push({
                    receiver_idx: receiverIdx,
                    receiver_name: all_services.find(s => s.receiver_idx == receiverIdx).receiver_name,
                    service: {
                        ...service,
                        selected_service_type: serviceType
                    }
                });
            }
        });

        if (!hasSelection) {
            frappe.msgprint(__('Please select at least one service'));
            return;
        }

        dialog.hide();
        process_shipment_creation(selected_services);
    } catch (e) {
        console.error('Error in create_selected_shipments:', e);
        frappe.msgprint(__('An error occurred while processing your request'));
    }
}

function process_shipment_creation(selected_services) {
    let dialog = new frappe.ui.Dialog({
        title: __('Creating Shipments'),
        fields: [
            {
                fieldname: 'progress',
                fieldtype: 'HTML',
                options: `
                    <div class="text-center">
                        <p>${__('Creating shipments, please wait...')}</p>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar progress-bar-striped active" role="progressbar" 
                                 style="width: 100%;"></div>
                        </div>
                    </div>
                `
            }
        ]
    });
    
    dialog.show();
    
    // Prepare item data for each receiver
    let shipments_data = selected_services.map(service => {
        let receiver_row = cur_frm.doc.receiver_details.find(r => r.idx == service.receiver_idx);
        return {
            child_name: receiver_row.name,
            receiver_idx: service.receiver_idx,
            receiver_name: service.receiver_name,
            service_data: service.service,
            item_data: {
                description: cur_frm.doc.description_of_content,
                weight: receiver_row.weight,
                dimensions: {
                    width: receiver_row.width,
                    height: receiver_row.height,
                    length: receiver_row.lengths,
                    quantity: receiver_row.count
                }
            }
        };
    });
    
    frappe.call({
        method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.create_bulk_shipment',
        args: {
            docname: cur_frm.docname,
            shipments_data: shipments_data
        },
        freeze: true,
        callback: function(r) {
            dialog.hide();
            if (r.message) {
                show_results(r.message);
                // Refresh the form and specifically the child table
                cur_frm.refresh_field('receiver_details');
                cur_frm.reload_doc();
            } else {
                frappe.msgprint(__('No response received from the server'));
            }
        },
        error: function(r) {
            dialog.hide();
            frappe.msgprint(__('Error creating shipments: ') + (r.responseJSON.exc || __('Unknown error')));
        }
    });
}

function show_results(results) {
    let hasErrors = results.some(r => r.status !== 'Success');
    
    let html = `
        <div class="shipment-results">
            <h5>${__('Shipment Creation Results')}</h5>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Receiver')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Details')}</th>
                        <th>${__('Actions')}</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    results.forEach(result => {
        html += `
            <tr class="${result.status === 'Success' ? 'success-row' : 'danger-row'}">
                <td>${result.receiver_name || __('N/A')}</td>
                <td>${result.status || __('Unknown')}</td>
                <td>
        `;
        
        if (result.status === 'Success') {
            html += `
                ${__('AWB')}: ${result.awb_number || __('N/A')}<br>
                ${__('Provider')}: ${result.service_provider || __('N/A')}
            `;
            if (result.tracking_url) {
                html += `<br><a href="${result.tracking_url}" target="_blank">${__('Track Shipment')}</a>`;
            }
        } else {
            html += result.error || __('Unknown error occurred');
        }
        
        html += `
                </td>
                <td>
        `;
        
        if (result.status === 'Success' && result.receiver_idx !== undefined) {
            html += `
                <button class="btn btn-default btn-xs view-receiver" 
                        data-receiver-idx="${result.receiver_idx}">
                    ${__('View Receiver')}
                </button>
            `;
        }
        
        html += `
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        <style>
            .success-row { background-color: #f0fff0; }
            .danger-row { background-color: #fff0f0; }
            .shipment-results { max-height: 60vh; overflow-y: auto; }
        </style>
    `;
    
    let msg = frappe.msgprint({
        title: __('Shipment Results'),
        indicator: hasErrors ? 'orange' : 'green',
        message: html
    });
    
    // Add click handler for view receiver buttons
    $(msg.$wrapper).on('click', '.view-receiver', function() {
        let receiverIdx = $(this).data('receiver-idx');
        let grid = cur_frm.fields_dict['receiver_details'].grid;
        let row = grid.grid_rows[receiverIdx - 1]; // idx is 1-based
        
        if (row) {
            grid.scroll_to_row(row);
            row.toggle_view();
        }
    });
}

function setup_shipment_buttons(frm) {
    if (frm.doc.docstatus == 1) {
        // Remove existing buttons first to prevent duplicates
        frm.page.clear_primary_action();
        frm.page.clear_secondary_action();
        
        // Check if we should show the Create Shipment button
        let showCreateButton = false;
        
        if (frm.doc.type === "Single Shipment") {
            // For single shipment, show if awb_number is empty
            showCreateButton = !frm.doc.awb_number;
        } else if (frm.doc.type === "Bulk Shipment") {
            // For bulk shipment, show if any receiver doesn't have awb_number
            if (frm.doc.receiver_details && frm.doc.receiver_details.length > 0) {
                showCreateButton = frm.doc.receiver_details.some(receiver => !receiver.awb_number);
            } else {
                // No receivers - probably shouldn't show button
                showCreateButton = false;
            }
        }
        
        // Main Create Shipment button
        if (showCreateButton) {
            frm.add_custom_button(__('Create Shipment'), function() {
                fetch_services_and_show_popup(frm);
            }).addClass('btn-success').css({'background':'#239b56', 'color':'white'});
        }

        // Single Track button if there are any shipments to track
        const hasTrackableShipments = (frm.doc.awb_number && frm.doc.status != 'Cancelled') || 
            (frm.doc.receiver_details && frm.doc.receiver_details.some(r => r.awb_number && r.status != 'Cancelled'));
        
        const hasPrintLabel = (frm.doc.awb_number && frm.doc.status != 'Cancelled') ||
            (frm.doc.receiver_details && frm.doc.receiver_details.some(r => r.awb_number && r.tracking_url && r.status != 'Cancelled'));
        
        const hasCancelableShipments = (frm.doc.awb_number && frm.doc.status != 'Cancelled') ||
            (frm.doc.receiver_details && frm.doc.receiver_details.some(r => r.awb_number && r.status != 'Cancelled'));
        
        if (hasTrackableShipments) {
            frm.add_custom_button(__('Track Shipments'), function() {
                show_tracking_popup(frm);
            }).addClass('btn-info');
        }
        
        if (hasTrackableShipments)
        {
        frm.add_custom_button(__('Update Status'), function() {
                            frappe.call({
                                method: 'erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.update_status',
                                args: {
                                    docname: frm.docname
                                },
                                freeze: true,
                                freeze_message: __('Getting Status... Please wait...⏳☕'),
                                callback: function(r) {
                                    if (r.message) {
                                        frappe.msgprint(__('Status Updated'));
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }).addClass('btn-info').css({'background':'#239b56', 'color':'white'});
    }
        
        if (hasPrintLabel){
            frm.add_custom_button(__('Download/Print Label'), function(){
                show_printing_popup(frm);
            }).addClass('btn-info').css({'background':'#0000FF', 'color':'white'});
        }
        
        if (hasCancelableShipments) {
            frm.add_custom_button(__('Cancel Shipment'), function() {
                cancel_shipment(frm);
            }).addClass('btn-danger');
        }
    }
}

function show_printing_popup(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Download/Print Label'),
        fields: [
            {
                fieldname: 'print_label',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });

    let html = `
        <div class="label-table-container">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Receiver')}</th>
                        <th>${__('AWB Number')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Action')}</th>
                    </tr>
                </thead>
                <tbody>
    `;

    // Add main shipment if exists
    if (frm.doc.awb_number && frm.doc.status != 'Cancelled' && frm.doc.tracking_url) {
        html += `
            <tr>
                <td>${frm.doc.name_of_the_receiver || 'Main Shipment'}</td>
                <td>${frm.doc.awb_number}</td>
                <td>${frm.doc.tracking_status || 'N/A'}</td>
                <td>
                    <button class="btn btn-xs btn-primary print-btn" 
                            data-url="${frm.doc.tracking_url}">
                        ${__('Print Label')}
                    </button>
                </td>
            </tr>
        `;
    }

    // Add receiver details if bulk shipment
    if (frm.doc.receiver_details) {
        frm.doc.receiver_details.forEach(receiver => {
            if (receiver.awb_number && receiver.status != 'Cancelled' && receiver.tracking_url) {
                html += `
                    <tr>
                        <td>${receiver.receiver_name || 'N/A'}</td>
                        <td>${receiver.awb_number}</td>
                        <td>${receiver.tracking_status || 'N/A'}</td>
                        <td>
                            <button class="btn btn-xs btn-primary print-btn" 
                                    data-url="${receiver.tracking_url}">
                                ${__('Print Label')}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    html += `
                </tbody>
            </table>
        </div>
        <style>
            .label-table-container { max-height: 60vh; overflow-y: auto; }
            .print-btn { width: 100px; }
            .table th { background-color: #f7f7f7; }
        </style>
    `;

    dialog.fields_dict.print_label.$wrapper.html(html);
    
    // Add click handler for print buttons
    dialog.$wrapper.on('click', '.print-btn', function() {
        const url = $(this).data('url');
        if (url) {
            window.open(url, '_blank');
        } else {
            frappe.msgprint(__('No label URL available for this shipment'));
        }
    });
    
    dialog.show();
}

function show_tracking_popup(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Shipment Tracking'),
        fields: [
            {
                fieldname: 'tracking_table',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });

    let html = `
        <div class="tracking-table-container">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Receiver')}</th>
                        <th>${__('AWB Number')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Action')}</th>
                    </tr>
                </thead>
                <tbody>
    `;

    // Add main shipment if exists
    if (frm.doc.awb_number && frm.doc.status != 'Cancelled') {
        html += `
            <tr>
                <td>${frm.doc.name_of_the_receiver || 'Main Shipment'}</td>
                <td>${frm.doc.awb_number}</td>
                <td>${frm.doc.tracking_status || 'N/A'}</td>
                <td>
                    <button class="btn btn-xs btn-default track-btn" 
                            data-awb="${frm.doc.awb_number}" 
                            data-slug="${frm.doc.service_provider}">
                        ${__('Track')}
                    </button>
                </td>
            </tr>
        `;
    }

    // Add receiver details if bulk shipment
    if (frm.doc.receiver_details) {
        frm.doc.receiver_details.forEach(receiver => {
            if (receiver.awb_number && receiver.status != 'Cancelled') {
                html += `
                    <tr>
                        <td>${receiver.receiver_name || 'N/A'}</td>
                        <td>${receiver.awb_number}</td>
                        <td>${receiver.tracking_status || 'N/A'}</td>
                        <td>
                            <button class="btn btn-xs btn-default track-btn" 
                                    data-awb="${receiver.awb_number}" 
                                    data-slug="${receiver.service_provider}">
                                ${__('Track')}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    html += `
                </tbody>
            </table>
        </div>
        <style>
            .tracking-table-container { max-height: 60vh; overflow-y: auto; }
            .track-btn { width: 70px; }
            .table th { background-color: #f7f7f7; }
        </style>
    `;

    dialog.fields_dict.tracking_table.$wrapper.html(html);
    
    // Add click handler for track buttons
    dialog.$wrapper.on('click', '.track-btn', function() {
        const awb = $(this).data('awb');
        const slug = $(this).data('slug');
        if (awb && slug) {
            window.open(`https://track.eshipz.com/track?awb=${awb}&slug=${slug}`, '_blank');
        }
    });
    
    dialog.show();
}

function build_delivery_address_html(frm) {
    const name = frm.doc.name_of_the_receiver || '';
    const line1 = frm.doc.address_line_1 || '';
    const line2 = frm.doc.address_line_2 || '';
    const city = frm.doc.city || '';
    const state = frm.doc.state || '';
    const postal_code = frm.doc.postal_code || '';
    const country = frm.doc.country || '';
    const contact = frm.doc.contact || '';

    const addressLine = [line1, line2].filter(Boolean).join(', ');
    const cityState = [city, state].filter(Boolean).join(', ');
    const lines = [name, addressLine, cityState, country, postal_code, contact].filter(Boolean);

    return `
        <div style="margin-top:10px; white-space: pre-line;">
            <strong>Delivery Address Details:</strong><br>
            ${lines.join('<br>')}
        </div>`;
}
