from __future__ import annotations

import frappe

DIM_TYPES = [
    ("cost_center", "Cost Center", "مركز التكلفة"),
    ("project", "Project", "المشروع"),
    ("department", "Department", "القسم"),
    ("branch", "Branch", "الفرع"),
    ("business_unit", "Business Unit", "وحدة الأعمال"),
    ("product_line", "Product Line", "خط المنتج"),
]

SEED_REPORTS = [
    ("Consolidated P&L", "consolidated-pnl", "pnl", "الأرباح والخسائر الموحّدة"),
    ("Balance Sheet", "balance-sheet", "balance_sheet", "الميزانية العمومية"),
    ("Trial Balance", "trial-balance", "trial_balance", "ميزان المراجعة"),
    ("Cash Flow Statement", "cash-flow", "cash_flow", "قائمة التدفقات النقدية"),
]


def after_install():
    seed_settings()
    seed_reports()


def after_migrate():
    # Make sure the single + at least the seed reports exist after upgrades.
    seed_settings()
    seed_reports()


def seed_settings():
    settings = frappe.get_single("Insight Settings")
    if not settings.ai_endpoint:
        settings.ai_endpoint = "http://host.docker.internal:11434/v1"
        settings.ai_model = "llama3.3"
        settings.ai_enabled = 0
        settings.language_default = "en"
        settings.flags.ignore_permissions = True
        settings.save()


def seed_reports():
    # The main `neotec_insight` app owns report authoring. When it's installed,
    # this app reads its "Insight Report Definition" documents directly, so we
    # do NOT seed competing fallback reports here.
    if frappe.db.table_exists("Insight Report Definition"):
        return
    for report_name, slug, report_type, name_ar in SEED_REPORTS:
        if frappe.db.exists("Neotec AI Report", {"slug": slug}):
            continue
        doc = frappe.new_doc("Neotec AI Report")
        doc.report_name = report_name
        doc.report_name_ar = name_ar
        doc.slug = slug
        doc.report_type = report_type
        doc.is_active = 1
        doc.view_period = 1
        doc.view_dimension = 1
        doc.view_years = 1
        doc.view_combo = 1
        for key, label, label_ar in DIM_TYPES:
            doc.append("dimensions", {
                "dimension_key": key,
                "dimension_label": label,
                "dimension_label_ar": label_ar,
                "enabled": 1,
            })
        doc.flags.ignore_permissions = True
        doc.insert()
    frappe.db.commit()
