# Create this file: customer_feedback/www/submit_feedback.py

import frappe
from frappe import _
from customer_feedback.customer_feedback.api.feedback import _get_site_report_by_token, ALLOWED_RATINGS
from frappe.utils import today

def get_context(context):
    """This function is called for GET requests"""
    context.no_cache = 1
    return context

@frappe.whitelist(allow_guest=True, methods=['POST'])
def submit():
    """Handle POST submission - no CSRF check for non-API endpoints"""
    try:
        # Get token
        token = frappe.form_dict.get("token")
        
        if not token:
            return {"success": False, "message": "Missing feedback link token."}
        
        doc = _get_site_report_by_token(token)
        
        if doc.customer_replied_date:
            return {"success": False, "message": "Feedback has already been submitted."}

        # Collect feedback
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
            value = frappe.form_dict.get(field)
            if value:
                feedback[field] = value
        
        # Validate ratings
        for field_name in [
            "after_installation_site_condition",
            "installation_team_behavior_and_appearance",
            "closet_status_design_expectations",
            "closet_status_finish_and_quality_expectations",
        ]:
            value = feedback.get(field_name)
            if value and value not in ALLOWED_RATINGS:
                return {"success": False, "message": f"Invalid rating value for {field_name}."}

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

        return {"success": True, "customer_replied_date": doc.customer_replied_date}
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Feedback Submission Error")
        return {"success": False, "message": str(e)}