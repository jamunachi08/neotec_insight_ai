"""Whitelisted server methods for Neotec Insight AI.

The AI bridge here is the integration point with NeoNexus (or any
OpenAI-compatible endpoint such as Ollama / LM Studio / OpenAI). The report
data method ships a documented seam (`run_report`) where you plug your real
ERPNext GL query or call into the existing `neotec_insight` engine.
"""

from __future__ import annotations

import json

import frappe
from frappe import _

DEFAULT_SYSTEM = (
    "You are Neotec AI, a precise, concise financial analyst embedded in an "
    "ERPNext reporting tool. You are given the on-screen report figures as "
    "context. Answer ONLY from those figures. Use short paragraphs and bullet "
    "lists. Quote numbers exactly. When the user writes in Arabic, answer in "
    "Arabic. Never invent data that is not in the context."
)


@frappe.whitelist()
def get_bootstrap():
    """Reports + AI status for the front-end to initialise with."""
    settings = frappe.get_single("Insight Settings")
    reports = frappe.get_all(
        "Neotec AI Report",
        filters={"is_active": 1},
        fields=[
            "name", "report_name", "report_name_ar", "slug", "report_type",
            "view_period", "view_dimension", "view_years", "view_combo",
        ],
        order_by="report_name asc",
    )
    for r in reports:
        r["dimensions"] = frappe.get_all(
            "Neotec AI Report Dimension",
            filters={"parent": r["name"]},
            fields=["dimension_key", "dimension_label", "dimension_label_ar", "enabled"],
            order_by="idx asc",
        )
    return {
        "reports": reports,
        "ai": {
            "enabled": bool(settings.ai_enabled),
            "model": settings.ai_model or "llama3",
            "endpoint_set": bool(settings.ai_endpoint),
        },
        "default_language": settings.language_default or "en",
    }


@frappe.whitelist()
def run_report(report=None, from_date=None, to_date=None, view="period", pivot_by=None, fiscal_year=None):
    """Return report data for a slug, fetched by DOCUMENT (posting) date.

    Data is filtered on ``GL Entry.posting_date BETWEEN from_date AND to_date`` —
    NOT on any fiscal-year field. ``fiscal_year`` is accepted only as a legacy
    convenience: if no explicit dates are passed, the caller may map a fiscal
    year to a date window before calling this. The window itself is always a
    posting-date range here.

    SEAM: this stub returns an empty envelope so the bundled UI falls back to
    its sample dataset. Replace the body with your real query, e.g.::

        from frappe.query_builder import DocType
        from frappe.query_builder.functions import Sum
        gl = DocType("GL Entry")
        rows = (
            frappe.qb.from_(gl)
            .select(gl.account, Sum(gl.debit - gl.credit).as_("amount"))
            .where(gl.is_cancelled == 0)
            .where(gl.posting_date[from_date:to_date])   # document-date filter
            .where(gl.company == company)
            .groupby(gl.account)
        ).run(as_dict=True)

    Return the shape the front-end expects (rows / kpis / headline), with an
    optional ``label_ar`` per row for Arabic.
    """
    return {
        "report": report,
        "view": view,
        "from_date": from_date,
        "to_date": to_date,
        "rows": [],
        "note": "sample-fallback",
    }


@frappe.whitelist()
def ask_ai(report=None, question=None, lang="en", context="", from_date=None, to_date=None):
    """Send report context + question to the configured AI endpoint.

    Mirrors the NeoNexus integration: OpenAI-compatible /chat/completions,
    local-first, nothing leaves the network unless the admin points the
    endpoint at a cloud provider.
    """
    settings = frappe.get_single("Insight Settings")
    if not settings.ai_enabled or not settings.ai_endpoint:
        frappe.throw(_("AI is not configured. Enable it in Insight Settings."))

    system_prompt = settings.ai_system_prompt or DEFAULT_SYSTEM
    period = f"{from_date or '?'} → {to_date or '?'}"
    user_msg = (
        f"Report: {report}\nLanguage: {lang}\nPeriod (by posting/document date): {period}\n\n"
        f"On-screen figures:\n{context}\n\nQuestion: {question}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    headers = {"Content-Type": "application/json"}
    api_key = settings.get_password("ai_api_key") if settings.ai_api_key else None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoint = settings.ai_endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ai_model or "llama3",
        "messages": messages,
        "stream": False,
        "temperature": 0.2,
    }

    import requests  # ships with Frappe

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(data, dict)
            else ""
        )
        if not text:
            frappe.throw(_("The AI endpoint returned an empty response."))
        return {"text": text}
    except Exception as e:  # noqa: BLE001
        frappe.log_error(frappe.get_traceback(), "Neotec Insight AI · ask_ai")
        frappe.throw(_("AI request failed: {0}").format(str(e)[:200]))


@frappe.whitelist()
def list_models():
    """Discover models from the configured endpoint (GET /models)."""
    settings = frappe.get_single("Insight Settings")
    if not settings.ai_endpoint:
        return {"models": []}
    import requests

    headers = {}
    api_key = settings.get_password("ai_api_key") if settings.ai_api_key else None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = requests.get(settings.ai_endpoint.rstrip("/") + "/models", headers=headers, timeout=8)
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return {"models": [m.get("id") for m in data["data"] if m.get("id")]}
        if isinstance(data, list):
            return {"models": [m.get("name") for m in data if m.get("name")]}
    except Exception:  # noqa: BLE001
        pass
    return {"models": []}
