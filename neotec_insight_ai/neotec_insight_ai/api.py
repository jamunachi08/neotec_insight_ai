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


def _trim_context(engine, limit=9000):
    """Compact JSON of the engine payload for the LLM context window."""
    try:
        s = json.dumps(engine, ensure_ascii=False, default=str)
    except Exception:
        s = str(engine)
    return s if len(s) <= limit else s[:limit] + " …(truncated)"


@frappe.whitelist()
def get_bootstrap():
    """Reports + AI status for the front-end to initialise with.

    Source of truth for the report LIST is the existing `neotec_insight`
    app's user-authored "Insight Report Definition" documents — so this app
    shows exactly the reports the user built there (rows, account map,
    dimensions, budget, equity all live in that app). We only fall back to
    this app's own seeded reports if the main app isn't installed.
    """
    settings = frappe.get_single("Insight Settings")
    reports = []

    if frappe.db.table_exists("Insight Report Definition"):
        # The old app owns report authoring — read its active reports.
        for d in frappe.get_all(
            "Insight Report Definition",
            filters={"is_active": 1},
            fields=["name", "report_name", "slug", "report_type", "is_default"],
            order_by="is_default desc, report_name asc",
        ):
            reports.append({
                "name": d["name"],
                "report_name": d["report_name"],
                "report_name_ar": None,        # old app stores labels in definition_json
                "slug": d["slug"],
                "report_type": d["report_type"],
                # The cockpit can offer all views; the engine decides what applies.
                "view_period": 1, "view_dimension": 1, "view_years": 1, "view_combo": 1,
                "dimensions": [],
                "source": "neotec_insight",
            })

    if not reports:
        # Fallback: this app's own (renamed) report doctype.
        for r in frappe.get_all(
            "Neotec AI Report",
            filters={"is_active": 1},
            fields=[
                "name", "report_name", "report_name_ar", "slug", "report_type",
                "view_period", "view_dimension", "view_years", "view_combo",
            ],
            order_by="report_name asc",
        ):
            r["dimensions"] = frappe.get_all(
                "Neotec AI Report Dimension",
                filters={"parent": r["name"]},
                fields=["dimension_key", "dimension_label", "dimension_label_ar", "enabled"],
                order_by="idx asc",
            )
            r["source"] = "neotec_insight_ai"
            reports.append(r)

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
def run_report(report=None, from_date=None, to_date=None, view="period", pivot_by=None,
               fiscal_year=None, company=None):
    """Run a report by delegating to the existing `neotec_insight` engine.

    `report` is a slug (or name) of an "Insight Report Definition" in the main
    app. We look up its report_type and call the matching whitelisted engine
    endpoint, passing the explicit posting-date window (from_date / to_date).
    The raw engine payload is returned under ``engine`` so the front-end (or a
    thin adapter) can render the same numbers the old app produces.

    If the main app isn't installed, returns an empty envelope and the bundled
    UI falls back to its sample dataset.
    """
    if not frappe.db.table_exists("Insight Report Definition"):
        return {"report": report, "view": view, "rows": [], "note": "sample-fallback"}

    # Resolve the report definition (by slug first, then by name).
    name = frappe.db.get_value("Insight Report Definition", {"slug": report}) or report
    rtype = frappe.db.get_value("Insight Report Definition", name, "report_type") or "pnl"

    from neotec_insight.neotec_insight.api import report as eng

    common = dict(report=name, company=company, from_date=from_date, to_date=to_date)
    try:
        if rtype == "trial_balance":
            payload = eng.run_trial_balance(**common)
        elif rtype == "balance_sheet":
            payload = eng.run_balance_sheet(report=name, company=company, as_of_date=to_date)
        elif rtype == "pnl_statement":
            # chart-of-accounts P&L reading Income/Expense directly
            payload = eng.run_report(report=name, fiscal_year=fiscal_year, company=company,
                                     from_date=from_date, to_date=to_date) \
                if hasattr(eng, "run_report") else {}
        else:  # 'pnl' and anything period-matrix based
            payload = eng.run_report(report=name, fiscal_year=fiscal_year, company=company,
                                     date_from=from_date, date_to=to_date)
    except TypeError:
        # Signature differences across engine versions — surface clearly rather
        # than guessing. The UI keeps its current data and the caller can adjust.
        return {"report": name, "report_type": rtype, "view": view,
                "rows": [], "note": "engine-signature-mismatch"}

    return {"report": name, "report_type": rtype, "view": view,
            "from_date": from_date, "to_date": to_date, "engine": payload}


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

    # If the client didn't pass on-screen figures, fetch them from the real
    # report engine so the model answers from live numbers (no client transform).
    if not context and report:
        try:
            data = run_report(report=report, from_date=from_date, to_date=to_date)
            engine = data.get("engine") if isinstance(data, dict) else None
            if engine is not None:
                context = _trim_context(engine)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Neotec Insight AI · ask_ai context")

    system_prompt = settings.ai_system_prompt or DEFAULT_SYSTEM
    period = f"{from_date or '?'} → {to_date or '?'}"
    user_msg = (
        f"Report: {report}\nLanguage: {lang}\nPeriod (by posting/document date): {period}\n\n"
        f"Report data (JSON from the live engine):\n{context}\n\nQuestion: {question}"
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
