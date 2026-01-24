import secrets

import frappe
from frappe import _
from frappe.utils import get_url, today


ALLOWED_RATINGS = {"Fair", "Good", "Very Good", "Excellent"}


def _get_site_report_by_token(token: str):
    if not token:
        frappe.throw(_("Missing feedback link token."))

    site_report_name = frappe.db.get_value("Site Report", {"feedback_token": token}, "name")
    if not site_report_name:
        frappe.throw(_("This feedback link is invalid or expired."))

    return frappe.get_doc("Site Report", site_report_name)


@frappe.whitelist()
def generate_feedback_link(site_report: str) -> str:
    if not site_report:
        frappe.throw(_("Missing Site Report."))

    if not frappe.has_permission("Site Report", "read", site_report):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc = frappe.get_doc("Site Report", site_report)
    if not doc.feedback_token:
        doc.feedback_token = secrets.token_urlsafe(16)
        doc.save(ignore_permissions=True)

    return f"{get_url()}/site-report-feedback?token={doc.feedback_token}"


@frappe.whitelist(allow_guest=True)
def get_feedback_context(token: str) -> dict:
    doc = _get_site_report_by_token(token)

    return {
        "submitted": bool(doc.customer_replied_date),
        "project_contraction": doc.project_contraction,
        "current_date": today(),
        "customer_replied_date": doc.customer_replied_date,
        "feedback": {
            "after_installation_site_condition": doc.after_installation_site_condition,
            "after_installation_site_condition_remark": doc.after_installation_site_condition_remark,
            "installation_team_behavior_and_appearance": doc.installation_team_behavior_and_appearance,
            "installation_team_behavior_and_appearance_remark": doc.installation_team_behavior_and_appearance_remark,
            "closet_status_design_expectations": doc.closet_status_design_expectations,
            "closet_status_design_expectations_remark": doc.closet_status_design_expectations_remark,
            "closet_status_finish_and_quality_expectations": doc.closet_status_finish_and_quality_expectations,
            "closet_status_finish_and_quality_expectations_remark": doc.closet_status_finish_and_quality_expectations_remark,
        },
    }

import secrets

import frappe
from frappe import _
from frappe.utils import get_url, today
from frappe.utils.password import check_password


ALLOWED_RATINGS = {"Fair", "Good", "Very Good", "Excellent"}


def _get_site_report_by_token(token: str):
    if not token:
        frappe.throw(_("Missing feedback link token."))

    site_report_name = frappe.db.get_value("Site Report", {"feedback_token": token}, "name")
    if not site_report_name:
        frappe.throw(_("This feedback link is invalid or expired."))

    return frappe.get_doc("Site Report", site_report_name)


@frappe.whitelist()
def generate_feedback_link(site_report: str) -> str:
    if not site_report:
        frappe.throw(_("Missing Site Report."))

    if not frappe.has_permission("Site Report", "read", site_report):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc = frappe.get_doc("Site Report", site_report)
    if not doc.feedback_token:
        doc.feedback_token = secrets.token_urlsafe(16)
        doc.save(ignore_permissions=True)

    return f"{get_url()}/site-report-feedback?token={doc.feedback_token}"


@frappe.whitelist(allow_guest=True)
def get_feedback_context(token: str) -> dict:
    doc = _get_site_report_by_token(token)

    return {
        "submitted": bool(doc.customer_replied_date),
        "project_contraction": doc.project_contraction,
        "current_date": today(),
        "customer_replied_date": doc.customer_replied_date,
        "feedback": {
            "after_installation_site_condition": doc.after_installation_site_condition,
            "after_installation_site_condition_remark": doc.after_installation_site_condition_remark,
            "installation_team_behavior_and_appearance": doc.installation_team_behavior_and_appearance,
            "installation_team_behavior_and_appearance_remark": doc.installation_team_behavior_and_appearance_remark,
            "closet_status_design_expectations": doc.closet_status_design_expectations,
            "closet_status_design_expectations_remark": doc.closet_status_design_expectations_remark,
            "closet_status_finish_and_quality_expectations": doc.closet_status_finish_and_quality_expectations,
            "closet_status_finish_and_quality_expectations_remark": doc.closet_status_finish_and_quality_expectations_remark,
        },
    }

@frappe.whitelist(allow_guest=True, xss_safe=True)
def submit_feedback(**kwargs) -> dict:
    # CRITICAL: Override verify_request to bypass CSRF for this guest endpoint
    frappe.flags.ignore_csrf = 1
    
    # Get token from kwargs or form_dict
    token = kwargs.get("token") or frappe.form_dict.get("token")
    
    if not token:
        frappe.throw(_("Missing feedback link token."))
    
    doc = _get_site_report_by_token(token)
    
    if doc.customer_replied_date:
        frappe.throw(_("Feedback has already been submitted."))

    # Collect feedback from kwargs and form_dict
    feedback = {}
    for field in [
        "after_installation_site_condition",
        "after_installation_site_condition_remark",
        "installation_team_behavior_and_appearance",
        "installation_team_behavior_and_appearance_remark",
        "closet_status_design_expectations",
        "closet_status_design_expectations_remark",
        "closet_status_finish_and_quality_expectations",
        "closet_status_finish_and_quality_expectations_remark",
    ]:
        value = kwargs.get(field) or frappe.form_dict.get(field)
        if value:
            feedback[field] = value
    
    if not feedback:
        frappe.throw(_("No feedback data provided."))

    # Validate ratings
    for field_name in [
        "after_installation_site_condition",
        "installation_team_behavior_and_appearance",
        "closet_status_design_expectations",
        "closet_status_finish_and_quality_expectations",
    ]:
        value = feedback.get(field_name)
        if value and value not in ALLOWED_RATINGS:
            frappe.throw(_("Invalid rating value for {0}.").format(field_name))

    # Update document
    doc.after_installation_site_condition = feedback.get("after_installation_site_condition")
    doc.after_installation_site_condition_remark = feedback.get("after_installation_site_condition_remark")
    doc.installation_team_behavior_and_appearance = feedback.get("installation_team_behavior_and_appearance")
    doc.installation_team_behavior_and_appearance_remark = feedback.get("installation_team_behavior_and_appearance_remark")
    doc.closet_status_design_expectations = feedback.get("closet_status_design_expectations")
    doc.closet_status_design_expectations_remark = feedback.get("closet_status_design_expectations_remark")
    doc.closet_status_finish_and_quality_expectations = feedback.get("closet_status_finish_and_quality_expectations")
    doc.closet_status_finish_and_quality_expectations_remark = feedback.get("closet_status_finish_and_quality_expectations_remark")
    doc.customer_replied_date = today()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"customer_replied_date": doc.customer_replied_date}