import frappe
from frappe import _
from customer_feedback.customer_feedback.api.feedback import (
    _get_site_report_by_token,
    ALLOWED_RATING_VALUES,
    RATING_FIELDS,
    ALL_FEEDBACK_FIELDS,
)
from frappe.utils import today


def get_context(context):
    """This function is called for GET requests"""
    context.no_cache = 1
    return context
