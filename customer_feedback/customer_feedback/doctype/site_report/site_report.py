# Copyright (c) 2026, Amr Basha and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document
from frappe.utils import get_url, today


class SiteReport(Document):
    def before_insert(self):
        self._fill_from_project()
        self._fill_from_installation_request()
        self._set_ending_date()
        self._generate_feedback_token()

    def _fill_from_project(self):
        """Auto-fill fields derived from the Project and Customer."""
        if not self.job_no:
            return

        # Fetch project-level fields
        project = frappe.db.get_value(
            "Project",
            self.job_no,
            ["customer", "project_name"],
            as_dict=True,
        )

        if not project:
            return

        if project.customer and not self.customer:
            self.customer = project.customer

        if project.project_name and not self.title_of_project:
            self.title_of_project = project.project_name

        # Fetch customer-level fields (chained from customer)
        if self.customer:
            customer = frappe.db.get_value(
                "Customer",
                self.customer,
                ["customer_name", "mobile_no", "whatsapp_number"],
                as_dict=True,
            )

            if not customer:
                return

            if customer.customer_name and not self.project_contraction:
                self.project_contraction = customer.customer_name

            if customer.mobile_no and not self.mobile_number:
                self.mobile_number = customer.mobile_no

            if customer.whatsapp_number and not self.whatsapp_number:
                self.whatsapp_number = customer.whatsapp_number

    def _fill_from_installation_request(self):
        """Auto-fill starting_date_of_installation and site_engineer from Installation Request."""
        if not self.job_no:
            return

        # Find the latest non-cancelled Installation Request for this project
        ir = frappe.db.get_value(
            "Installation Request",
            filters={"project": self.job_no, "status": ["!=", "Cancelled"]},
            fieldname=["scheduled_date", "installation_engineer_name"],
            order_by="creation desc",
            as_dict=True,
        )

        if not ir:
            return

        if ir.scheduled_date and not self.starting_date_of_installation:
            self.starting_date_of_installation = ir.scheduled_date

        if ir.installation_engineer_name and not self.site_engineer:
            self.site_engineer = ir.installation_engineer_name

    def _set_ending_date(self):
        """Set ending_date_of_installation to today (date of creation)."""
        if not self.ending_date_of_installation:
            self.ending_date_of_installation = today()

    def _generate_feedback_token(self):
        """Generate feedback token and URL automatically."""
        if not self.feedback_token:
            self.feedback_token = secrets.token_urlsafe(16)
            self.url = f"{get_url()}/site-report-feedback?token={self.feedback_token}"
