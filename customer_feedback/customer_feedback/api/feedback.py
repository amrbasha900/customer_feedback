import base64
import os
import secrets

import frappe
from frappe import _
from frappe.utils import get_url, today
from frappe.utils.pdf import get_pdf


# Rating field stores 0-1 in 0.2 increments (5-star system)
# 1 star=0.2, 2 stars=0.4, 3 stars=0.6, 4 stars=0.8, 5 stars=1.0
ALLOWED_RATING_VALUES = {0.2, 0.4, 0.6, 0.8, 1.0}

RATING_FIELDS = [
    "after_installation_site_condition",
    "installation_team_behavior_and_appearance",
    "closet_status_design_expectations",
    "closet_status_finish_and_quality_expectations",
    "showroom_and_designer_evaluation",
]

REMARK_FIELDS = [
    "after_installation_site_condition_remark",
    "installation_team_behavior_and_appearance_remark",
    "closet_status_design_expectations_remark",
    "closet_status_finish_and_quality_expectations_remark",
    "showroom_and_designer_evaluation_remark",
]

TEXT_FIELDS = [
    "site_report",
]

ALL_FEEDBACK_FIELDS = RATING_FIELDS + REMARK_FIELDS + TEXT_FIELDS


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
        doc.url = f"{get_url()}/site-report-feedback?token={doc.feedback_token}"
        doc.save(ignore_permissions=True)

    return f"{get_url()}/site-report-feedback?token={doc.feedback_token}"


@frappe.whitelist(allow_guest=True)
def get_feedback_context(token: str) -> dict:
    doc = _get_site_report_by_token(token)

    feedback = {}
    for field in ALL_FEEDBACK_FIELDS:
        feedback[field] = getattr(doc, field, None) or ""

    return {
        "submitted": bool(doc.customer_replied_date),
        "project_contraction": doc.project_contraction,
        "current_date": today(),
        "customer_replied_date": doc.customer_replied_date,
        "site_report": doc.site_report or "",
        "feedback": feedback,
    }


@frappe.whitelist(allow_guest=True, xss_safe=True)
def submit_feedback(**kwargs) -> dict:
    frappe.flags.ignore_csrf = 1

    token = kwargs.get("token") or frappe.form_dict.get("token")

    if not token:
        frappe.throw(_("Missing feedback link token."))

    doc = _get_site_report_by_token(token)

    if doc.customer_replied_date:
        frappe.throw(_("Feedback has already been submitted."))

    # Collect feedback from kwargs and form_dict
    feedback = {}
    for field in ALL_FEEDBACK_FIELDS:
        value = kwargs.get(field) or frappe.form_dict.get(field)
        if value:
            feedback[field] = value

    if not feedback:
        frappe.throw(_("No feedback data provided."))

    # Validate mandatory fields
    if not feedback.get("site_report", "").strip():
        frappe.throw(_("Site Report is mandatory."))

    for field_name in RATING_FIELDS:
        if not feedback.get(field_name):
            frappe.throw(_("{0} rating is mandatory.").format(field_name.replace("_", " ").title()))

    # Validate rating values (must be valid 0.2 increments)
    for field_name in RATING_FIELDS:
        value = feedback.get(field_name)
        if value:
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                frappe.throw(_("Invalid rating value for {0}.").format(field_name))

            # Round to 1 decimal place to handle floating point precision
            # e.g. JS sends 0.6000000000000001 for 3 * 0.2
            numeric_value = round(numeric_value, 1)

            if numeric_value not in ALLOWED_RATING_VALUES:
                frappe.throw(_("Invalid rating value for {0}.").format(field_name))

            feedback[field_name] = numeric_value

    # Update document
    for field in ALL_FEEDBACK_FIELDS:
        if field in feedback:
            setattr(doc, field, feedback[field])

    doc.customer_replied_date = today()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Generate and attach Certificate of Guarantee PDF
    certificate_url = _generate_certificate_pdf(doc)

    return {
        "customer_replied_date": doc.customer_replied_date,
        "certificate_url": certificate_url,
    }


def _invert_logo_to_dark(logo_path):
    """Invert a white-on-transparent PNG to black-on-transparent for PDF use."""
    try:
        from PIL import Image, ImageOps
        import io

        img = Image.open(logo_path).convert("RGBA")
        r, g, b, a = img.split()
        # Invert RGB channels (white -> black), keep alpha unchanged
        rgb_img = Image.merge("RGB", (r, g, b))
        inverted = ImageOps.invert(rgb_img)
        ri, gi, bi = inverted.split()
        result = Image.merge("RGBA", (ri, gi, bi, a))

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        # Fallback: return original if PIL not available
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


def _generate_certificate_pdf(doc):
    """Generate a Certificate of Guarantee PDF and attach it to the Site Report."""
    try:
        # Load logo and create inverted (dark) version for PDF
        logo_path = os.path.join(
            frappe.get_app_path("customer_feedback"),
            "public", "images", "Vector Smart Object.png"
        )
        logo_dark_b64 = ""
        if os.path.exists(logo_path):
            logo_dark_b64 = _invert_logo_to_dark(logo_path)

        # Parse date
        date_str = str(doc.customer_replied_date or today())
        date_parts = date_str.split("-")
        date_year = date_parts[0] if len(date_parts) > 0 else ""
        date_month = date_parts[1] if len(date_parts) > 1 else ""
        date_day = date_parts[2] if len(date_parts) > 2 else ""

        # Load and render template
        template_path = os.path.join(
            frappe.get_app_path("customer_feedback"),
            "customer_feedback", "templates", "certificate_of_guarantee.html"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template_str = f.read()

        html = frappe.render_template(template_str, {
            "logo_dark_b64": logo_dark_b64,
            "date_day": date_day,
            "date_month": date_month,
            "date_year": date_year,
            "doc": doc,
        })

        # Generate PDF - page config from pdfkit meta tags in template
        pdf_content = get_pdf(html, options={
            "encoding": "UTF-8",
            "no-outline": None,
            "print-media-type": None,
        })

        # Remove any existing certificate for this document
        existing = frappe.db.get_value(
            "File",
            {"attached_to_doctype": "Site Report", "attached_to_name": doc.name, "file_name": ("like", "Certificate_of_Guarantee%")},
            "name"
        )
        if existing:
            frappe.delete_doc("File", existing, ignore_permissions=True)

        # Attach PDF to document
        file_name = f"Certificate_of_Guarantee_{doc.name}.pdf"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": "Site Report",
            "attached_to_name": doc.name,
            "content": pdf_content,
            "is_private": 0,
        })
        file_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return file_doc.file_url

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Certificate PDF Generation Error")
        return None
