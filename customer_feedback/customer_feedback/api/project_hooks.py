import frappe
from frappe.utils import today


def on_project_update(doc, method):
    """Called when a Project document is updated.
    Auto-creates a Site Report when Project status changes to Completed.
    """
    # Only proceed if status changed to Completed
    if doc.status != "Completed":
        return

    # Check if status actually changed (not already Completed before)
    previous_status = doc.get_doc_before_save()
    if previous_status and previous_status.status == "Completed":
        return

    # Check if a Site Report already exists for this project
    existing = frappe.db.exists("Site Report", {"job_no": doc.name})
    if existing:
        return

    # Create Site Report
    try:
        site_report = frappe.get_doc({
            "doctype": "Site Report",
            "job_no": doc.name,
            # customer and project_contraction are auto-fetched via fetch_from in the doctype
        })

        # Insert triggers before_insert which auto-fills:
        # - starting_date_of_installation (from Installation Request)
        # - site_engineer (from Installation Request)
        # - ending_date_of_installation (today)
        # - feedback_token + url (auto-generated)
        site_report.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.msgprint(
            f"Site Report <b>{site_report.name}</b> created automatically with feedback link.",
            title="Site Report Created",
            indicator="green",
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Auto Site Report Creation Error")
