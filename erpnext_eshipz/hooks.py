app_name = "erpnext_eshipz"
app_title = "Erpnext Eshipz"
app_publisher = "KlyONIX Tech Consulting Pvt Ltd"
app_description = "Eshipz integration with erpnext"
app_email = "hello@klyonix.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "erpnext_eshipz",
# 		"logo": "/assets/erpnext_eshipz/logo.png",
# 		"title": "Erpnext Eshipz",
# 		"route": "/erpnext_eshipz",
# 		"has_permission": "erpnext_eshipz.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_eshipz/css/erpnext_eshipz.css"
# app_include_js = "/assets/erpnext_eshipz/js/erpnext_eshipz.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_eshipz/css/erpnext_eshipz.css"
# web_include_js = "/assets/erpnext_eshipz/js/erpnext_eshipz.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpnext_eshipz/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}
doctype_js = {
    "Shipment" : "erpnext_eshipz/custom/shipment/shipment.js",
    "Sales Invoice" : "erpnext_eshipz/custom/sales_invoice/sales_invoice.js",
    "Delivery Note" : "erpnext_eshipz/custom/delivery_note/delivery_note.js",
    "Stock Entry" : "erpnext_eshipz/custom/stock_entry/stock_entry.js"
}


# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "erpnext_eshipz/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "erpnext_eshipz.utils.jinja_methods",
# 	"filters": "erpnext_eshipz.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "erpnext_eshipz.install.before_install"
# after_install = "erpnext_eshipz.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "erpnext_eshipz.uninstall.before_uninstall"
# after_uninstall = "erpnext_eshipz.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "erpnext_eshipz.utils.before_app_install"
# after_app_install = "erpnext_eshipz.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "erpnext_eshipz.utils.before_app_uninstall"
# after_app_uninstall = "erpnext_eshipz.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_eshipz.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    "Sales Invoice": {
        "before_submit": "erpnext_eshipz.erpnext_eshipz.custom.sales_invoice.sales_invoice.update_delivery_note"
    },
    "Custom Shipment":
    {
        "before_submit": "erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.validation_of_shipment",
        "on_update": "erpnext_eshipz.erpnext_eshipz.doctype.custom_shipment.custom_shipment.bg_log"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"erpnext_eshipz.tasks.all"
# 	],
# 	"daily": [
# 		"erpnext_eshipz.tasks.daily"
# 	],
# 	"hourly": [
# 		"erpnext_eshipz.tasks.hourly"
# 	],
# 	"weekly": [
# 		"erpnext_eshipz.tasks.weekly"
# 	],
# 	"monthly": [
# 		"erpnext_eshipz.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "erpnext_eshipz.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "erpnext_eshipz.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "erpnext_eshipz.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["erpnext_eshipz.utils.before_request"]
# after_request = ["erpnext_eshipz.utils.after_request"]

# Job Events
# ----------
# before_job = ["erpnext_eshipz.utils.before_job"]
# after_job = ["erpnext_eshipz.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"erpnext_eshipz.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

