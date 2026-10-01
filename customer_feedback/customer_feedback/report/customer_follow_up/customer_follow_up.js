// Copyright (c) 2026, Amr Basha and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Amr Basha and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Follow-Up"] = {

	filters: [
		{
			fieldname: "assigned_user",
			label: __("Assigned User"),
			fieldtype: "Link",
			options: "User",
			get_query: function () {
				return { filters: { enabled: 1, user_type: "System User" } };
			},
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function () {
				// If a user is already selected, restrict dropdown to their customers
				let user = frappe.query_report.get_filter_value("assigned_user");
				if (user) {
					return {
						filters: {
							erpnext_user: user,
							enable_daily_followup: 1,
						},
					};
				}
				return { filters: { enable_daily_followup: 1 } };
			},
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nOn Track\nDue Today\nOverdue\nNever",
		},
	],

	// ── Row colour by status ──────────────────────────────────────
	get_datatable_options: function (options) {
		options.getRowHTML = null;  // let formatter handle it
		return options;
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data) {
			let color_map = {
				"🔴 Never": { bg: "#fef2f2", fg: "#dc2626" },
				"🟠 Overdue": { bg: "#fff7ed", fg: "#ea580c" },
				"🟡 Due Today": { bg: "#fefce8", fg: "#ca8a04" },
				"🟢 On Track": { bg: "#f0fdf4", fg: "#16a34a" },
			};
			let style = color_map[data.status];
			if (style) {
				value = `<span style="
                    background:${style.bg};color:${style.fg};
                    padding:2px 10px;border-radius:99px;
                    font-size:11px;font-weight:700;
                ">${data.status}</span>`;
			}
		}

		// Highlight days_since_last red if overdue
		if (column.fieldname === "days_since_last" && data) {
			let delay = data.followup_delay_days || 1;
			if (data.days_since_last === null || data.days_since_last === undefined) {
				value = `<span style="color:#dc2626;font-weight:600">—</span>`;
			} else if (data.days_since_last >= delay) {
				value = `<span style="color:#dc2626;font-weight:700">${data.days_since_last}</span>`;
			} else if (data.days_since_last >= delay - 1) {
				value = `<span style="color:#ca8a04;font-weight:700">${data.days_since_last}</span>`;
			}
		}

		// Truncate last comment with tooltip
		if (column.fieldname === "last_comment" && data && data.last_comment) {
			let short = data.last_comment.length > 80
				? data.last_comment.slice(0, 80) + "…"
				: data.last_comment;
			value = `<span title="${frappe.utils.escape_html(data.last_comment)}"
                           style="color:#374151">${frappe.utils.escape_html(short)}</span>`;
		}

		return value;
	},

	// ── KPI summary cards above the report ───────────────────────
	onload: function (report) {
		// Inject summary after each refresh
		report.page.wrapper.on("report-refresh", function () {
			render_kpi_cards(report);
		});
	},

	after_datatable_render: function (datatable) {
		render_kpi_cards(frappe.query_report);
	},
};


// ─────────────────────────────────────────────────────────────────
// KPI CARDS
// ─────────────────────────────────────────────────────────────────

function render_kpi_cards(report) {
	// Remove existing cards
	report.page.wrapper.find("#cf-kpi-bar").remove();

	let data = (report.data || []);
	if (!data.length) return;

	let total = data.length;
	let on_track = data.filter(r => (r.status || "").includes("On Track")).length;
	let due_today = data.filter(r => (r.status || "").includes("Due Today")).length;
	let overdue = data.filter(r => (r.status || "").includes("Overdue")).length;
	let never = data.filter(r => (r.status || "").includes("Never")).length;
	let total_comments = data.reduce((s, r) => s + (r.total_comments || 0), 0);
	let comments_month = data.reduce((s, r) => s + (r.comments_this_month || 0), 0);

	let avg_days_arr = data
		.filter(r => r.avg_days_between != null)
		.map(r => r.avg_days_between);
	let avg_overall = avg_days_arr.length
		? (avg_days_arr.reduce((a, b) => a + b, 0) / avg_days_arr.length).toFixed(1)
		: "—";

	let cards = [
		{ label: "Total Customers", value: total, color: "#2563eb", icon: "👥" },
		{ label: "🟢 On Track", value: on_track, color: "#16a34a", icon: "" },
		{ label: "🟡 Due Today", value: due_today, color: "#ca8a04", icon: "" },
		{ label: "🟠 Overdue", value: overdue, color: "#ea580c", icon: "" },
		{ label: "🔴 Never Followed Up", value: never, color: "#dc2626", icon: "" },
		{ label: "Total Comments", value: total_comments, color: "#7c3aed", icon: "💬" },
		{ label: "Comments This Month", value: comments_month, color: "#0891b2", icon: "📅" },
		{ label: "Avg Days Between", value: avg_overall, color: "#374151", icon: "⏱" },
	];

	let cards_html = cards.map(function (c) {
		return `
            <div style="
                background:#fff; border:1px solid #e2e8f0;
                border-radius:10px; padding:14px 18px;
                min-width:130px; flex:1;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);
            ">
                <div style="font-size:20px;font-weight:800;color:${c.color};line-height:1.1">
                    ${c.value}
                </div>
                <div style="font-size:11px;color:#64748b;margin-top:4px;font-weight:500">
                    ${c.label}
                </div>
            </div>`;
	}).join("");

	let bar = $(`
        <div id="cf-kpi-bar" style="
            display:flex; flex-wrap:wrap; gap:10px;
            padding:14px 16px 4px;
            border-bottom:1px solid #f1f5f9;
            margin-bottom:8px;
        ">
            ${cards_html}
        </div>
    `);

	// Insert before the datatable
	report.page.wrapper.find(".datatable-wrapper").first().before(bar);
}