# Copyright (c) 2026, Amr Basha and contributors
# For license information, please see license.txt

# Copyright (c) 2026, Amr Basha and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, date_diff, getdate, nowdate
import re


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "customer",
            "label":     "Customer",
            "fieldtype": "Link",
            "options":   "Customer",
            "width":     180,
        },
        {
            "fieldname": "customer_name",
            "label":     "Customer Name",
            "fieldtype": "Data",
            "width":     180,
        },
        {
            "fieldname": "assigned_user",
            "label":     "Assigned User",
            "fieldtype": "Link",
            "options":   "User",
            "width":     160,
        },
        {
            "fieldname": "assigned_user_name",
            "label":     "User Full Name",
            "fieldtype": "Data",
            "width":     150,
        },
        {
            "fieldname": "followup_delay_days",
            "label":     "Required Every (Days)",
            "fieldtype": "Int",
            "width":     140,
        },
        {
            "fieldname": "last_followup_date",
            "label":     "Last Follow-Up Date",
            "fieldtype": "Date",
            "width":     140,
        },
        {
            "fieldname": "days_since_last",
            "label":     "Days Since Last",
            "fieldtype": "Int",
            "width":     120,
        },
        {
            "fieldname": "status",
            "label":     "Status",
            "fieldtype": "Data",
            "width":     120,
        },
        {
            "fieldname": "total_comments",
            "label":     "Total Comments",
            "fieldtype": "Int",
            "width":     120,
        },
        {
            "fieldname": "comments_this_month",
            "label":     "Comments This Month",
            "fieldtype": "Int",
            "width":     150,
        },
        {
            "fieldname": "avg_days_between",
            "label":     "Avg Days Between Comments",
            "fieldtype": "Float",
            "precision": 1,
            "width":     180,
        },
        {
            "fieldname": "last_comment",
            "label":     "Last Comment",
            "fieldtype": "Data",
            "width":     300,
        },
    ]


def get_data(filters):
    today_date = getdate(today())

    # ── Build Customer filters ────────────────────────────────────
    cust_filters = {"enable_daily_followup": 1}

    if filters.get("assigned_user"):
        cust_filters["erpnext_user"] = filters["assigned_user"]

    if filters.get("customer"):
        cust_filters["name"] = filters["customer"]

    customers = frappe.db.get_all(
        "Customer",
        filters=cust_filters,
        fields=[
            "name", "customer_name",
            "erpnext_user", "followup_delay_days",
            "last_followup_date",
        ],
    )

    if not customers:
        return []

    # Fetch full names for assigned users in one query
    user_emails = list({c.erpnext_user for c in customers if c.erpnext_user})
    user_name_map = {}
    if user_emails:
        users = frappe.db.get_all(
            "User",
            filters={"name": ["in", user_emails]},
            fields=["name", "full_name"],
        )
        user_name_map = {u.name: u.full_name for u in users}

    # Fetch all comments for these customers in one query
    customer_names = [c.name for c in customers]
    comments = frappe.db.get_all(
        "Comment",
        filters={
            "reference_doctype": "Customer",
            "reference_name":    ["in", customer_names],
            "comment_type":      "Comment",
        },
        fields=["reference_name", "content", "creation"],
        order_by="creation asc",
    )

    # Group comments by customer
    from collections import defaultdict
    comment_map = defaultdict(list)
    for cm in comments:
        comment_map[cm.reference_name].append(cm)

    # Current month boundaries
    from frappe.utils import get_first_day, get_last_day
    first_day_month = get_first_day(today_date)
    last_day_month  = get_last_day(today_date)

    # ── Build rows ────────────────────────────────────────────────
    data = []

    for c in customers:
        delay         = int(c.followup_delay_days or 1)
        last_date     = getdate(c.last_followup_date) if c.last_followup_date else None
        days_since    = date_diff(today_date, last_date) if last_date else None
        cust_comments = comment_map.get(c.name, [])

        # Status
        if not last_date:
            status = "🔴 Never"
        elif days_since >= delay:
            status = "🟠 Overdue"
        elif days_since >= delay - 1:
            status = "🟡 Due Today"
        else:
            status = "🟢 On Track"

        # Filter by status if requested
        if filters.get("status") and filters["status"] not in status:
            continue

        # Comments this month
        comments_month = sum(
            1 for cm in cust_comments
            if first_day_month <= getdate(cm.creation) <= last_day_month
        )

        # Average days between comments
        avg_days = None
        if len(cust_comments) >= 2:
            dates     = [getdate(cm.creation) for cm in cust_comments]
            gaps      = [date_diff(dates[i+1], dates[i]) for i in range(len(dates)-1)]
            avg_days  = round(sum(gaps) / len(gaps), 1)

        # Last comment — strip HTML tags for display
        last_comment_text = ""
        if cust_comments:
            raw = cust_comments[-1].content or ""
            last_comment_text = _strip_html(raw)[:200]
            if len(_strip_html(raw)) > 200:
                last_comment_text += "..."

        data.append({
            "customer":             c.name,
            "customer_name":        c.customer_name,
            "assigned_user":        c.erpnext_user,
            "assigned_user_name":   user_name_map.get(c.erpnext_user, ""),
            "followup_delay_days":  delay,
            "last_followup_date":   c.last_followup_date,
            "days_since_last":      days_since,
            "status":               status,
            "total_comments":       len(cust_comments),
            "comments_this_month":  comments_month,
            "avg_days_between":     avg_days,
            "last_comment":         last_comment_text,
        })

    # Sort: Overdue first, then Never, then Due Today, then On Track
    order = {"🔴 Never": 0, "🟠 Overdue": 1, "🟡 Due Today": 2, "🟢 On Track": 3}
    data.sort(key=lambda r: order.get(r["status"], 9))

    return data


def _strip_html(html):
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", "", html or "")
    text = text.replace("\uFEFF", "")
    text = (text
            .replace("&amp;",  "&")
            .replace("&lt;",   "<")
            .replace("&gt;",   ">")
            .replace("&quot;", '"')
            .replace("&#39;",  "'")
            .replace("&nbsp;", " "))
    return text.strip()