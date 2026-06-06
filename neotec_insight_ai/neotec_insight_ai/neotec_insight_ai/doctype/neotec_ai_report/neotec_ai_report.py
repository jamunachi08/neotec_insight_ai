from __future__ import annotations

import frappe
from frappe.model.document import Document


class NeotecAIReport(Document):
    def validate(self):
        if self.slug:
            self.slug = frappe.scrub(self.slug).replace("_", "-")
