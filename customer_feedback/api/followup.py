import frappe
from frappe.utils import today, date_diff, getdate


def get_pending_followups_for_user(user):
    """
    Core logic: returns customers due for follow-up for a given user.
    Used by both on_login hook and the whitelisted API.
    """
    customers = frappe.db.get_all(
        "Customer",
        filters={
            "erpnext_user": user,
            "enable_daily_followup": 1,
        },
        fields=[
            "name", "customer_name",
            "last_followup_date", "followup_delay_days"
        ]
    )

    pending = []
    today_date = getdate(today())

    for c in customers:
        delay = int(c.get("followup_delay_days") or 1)
        last = c.get("last_followup_date")

        if not last:
            pending.append(c)
        else:
            days_since = date_diff(today_date, getdate(last))
            if days_since >= delay:
                pending.append(c)

    return pending


def on_user_login(login_manager):
    """
    Hook called on every user login.
    Stores pending follow-up customers in the session cache
    so the frontend JS can retrieve it immediately.
    """
    user = login_manager.user
    if not user or user == "Guest":
        return

    pending = get_pending_followups_for_user(user)

    # Store in session-level cache keyed per user
    frappe.cache().set_value(
        f"followup_pending_{user}",
        pending,
        expires_in_sec=86400  # 24 hours — cleared after daily use
    )


@frappe.whitelist()
def get_pending_followups():
    """
    Called by frontend JS after login.
    Reads from session cache set during on_login.
    Falls back to fresh DB query if cache miss.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return []

    cached = frappe.cache().get_value(f"followup_pending_{user}")
    if cached is not None:
        return cached

    # Cache miss fallback
    return get_pending_followups_for_user(user)


@frappe.whitelist()
def clear_followup_cache():
    """Called after all follow-ups completed to clean up cache."""
    user = frappe.session.user
    frappe.cache().delete_value(f"followup_pending_{user}")


def before_comment_insert(doc, method):
    """
    before_insert hook on Comment doctype.
    When a comment is added to a Customer:
      1. Validate it belongs to the assigned user
      2. Validate minimum 20 characters
      3. Update last_followup_date on the Customer
      4. Remove this customer from the pending cache
    """
    # Only process comments on Customer doctype
    if doc.reference_doctype != "Customer":
        return

    # Only process if comment_type is "Comment" (not Log, Info, etc.)
    if doc.comment_type != "Comment":
        return

    user = frappe.session.user
    customer_name = doc.reference_name

    # Fetch customer follow-up settings
    customer = frappe.db.get_value(
        "Customer",
        customer_name,
        ["erpnext_user", "enable_daily_followup", "customer_name"],
        as_dict=True
    )

    if not customer:
        return  # Not a valid customer, let normal flow handle it

    # Only enforce rules if follow-up is enabled for this customer
    if not customer.enable_daily_followup:
        return

    # Only enforce for the assigned user
    if customer.erpnext_user != user:
        return

    # Validate minimum comment length
    content = frappe.utils.strip_html(doc.content or "").strip()
    if len(content) < 20:
        frappe.throw(
            f"Follow-up comment for <strong>{customer.customer_name}</strong> "
            f"must be at least <strong>20 characters</strong>. "
            f"You entered {len(content)} characters.",
            title="Comment Too Short"
        )

    # All good — update last_followup_date
    frappe.db.set_value("Customer", customer_name, "last_followup_date", today())
    frappe.db.commit()

    # Remove from pending cache so popup doesn't re-show this customer
    cached = frappe.cache().get_value(f"followup_pending_{user}")
    if cached:
        updated = [c for c in cached if c.get("name") != customer_name]
        frappe.cache().set_value(
            f"followup_pending_{user}",
            updated,
            expires_in_sec=86400
        )

@frappe.whitelist()
def has_pending_followups():
    """
    Lightweight check — returns True/False + count.
    Called on every page load/refresh.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"pending": False, "count": 0, "customers": []}

    # Try cache first
    cached = frappe.cache().get_value(f"followup_pending_{user}")
    
    if cached is not None:
        # Filter out any that were completed since cache was set
        still_pending = []
        for c in cached:
            last = frappe.db.get_value("Customer", c["name"], "last_followup_date")
            delay = int(c.get("followup_delay_days") or 1)
            if not last:
                still_pending.append(c)
            else:
                from frappe.utils import date_diff, getdate, today
                if date_diff(getdate(today()), getdate(last)) >= delay:
                    still_pending.append(c)
        
        # Update cache with accurate list
        frappe.cache().set_value(
            f"followup_pending_{user}", still_pending, expires_in_sec=86400
        )
        customers = still_pending
    else:
        customers = get_pending_followups_for_user(user)
        frappe.cache().set_value(
            f"followup_pending_{user}", customers, expires_in_sec=86400
        )

    return {
        "pending": len(customers) > 0,
        "count": len(customers),
        "customers": customers
    }


@frappe.whitelist()
def submit_followup_comment(customer, comment):
    """
    Accepts Quill HTML (with <span class="mention"> elements).
    Strips HTML to plain text only for the 20-char length validation.
    Passes raw Quill HTML to doc.add_comment() so ERPNext renders
    mentions and timeline correctly.
    """
    if not customer or not comment:
        frappe.throw("Customer and comment are required.")

    # Strip ALL html tags to get plain text for length validation
    import re
    plain = re.sub(r"<[^>]+>", "", comment)          # remove tags
    plain = plain.replace("\uFEFF", "")               # remove Quill zero-width chars
    plain = plain.replace("&amp;", "&") \
                 .replace("&lt;", "<") \
                 .replace("&gt;", ">") \
                 .replace("&quot;", '"') \
                 .replace("&#39;", "'")
    plain = plain.strip()

    if len(plain) < 20:
        frappe.throw(
            f"Comment must be at least <b>20 characters</b>. "
            f"You entered {len(plain)} character(s).",
            title="Comment Too Short"
        )

    # Verify assigned user
    assigned = frappe.db.get_value(
        "Customer", customer,
        ["erpnext_user", "enable_daily_followup"],
        as_dict=True
    )
    if not assigned or assigned.erpnext_user != frappe.session.user:
        frappe.throw("You are not authorized to follow up on this customer.")
    if not assigned.enable_daily_followup:
        frappe.throw("Daily follow-up is not enabled for this customer.")

    # doc.add_comment() — stores Quill HTML as-is, appears in timeline
    doc = frappe.get_doc("Customer", customer)
    doc.add_comment("Comment", text=comment)

    return {"success": True}