import frappe

def handle_csrf_for_guest_endpoints():
    """Disable CSRF check for specific guest endpoints"""
    if frappe.request and frappe.request.path:
        # List of endpoints that should bypass CSRF for guests
        csrf_exempt_paths = [
            "/api/method/customer_feedback.customer_feedback.api.feedback.submit_feedback"
        ]
        
        if frappe.request.path in csrf_exempt_paths and frappe.session.user == "Guest":
            frappe.flags.ignore_csrf = True