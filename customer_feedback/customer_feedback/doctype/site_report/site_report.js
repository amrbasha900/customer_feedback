// Copyright (c) 2026, Amr Basha and contributors
// For license information, please see license.txt

frappe.ui.form.on("Site Report", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Get Feedback Link"), async () => {
			const response = await frappe.call({
				method: "customer_feedback.api.feedback.generate_feedback_link",
				args: { site_report: frm.doc.name },
			});

			if (response.message) {
				frappe.msgprint({
					title: __("Share Feedback Link"),
					message: `<a href="${response.message}" target="_blank" rel="noopener noreferrer">${response.message}</a>`,
					indicator: "green",
				});
			}
		});
	},
});
