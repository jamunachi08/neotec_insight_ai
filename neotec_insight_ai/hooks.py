from __future__ import annotations

app_name = "neotec_insight_ai"
app_title = "Neotec Insight AI"
app_publisher = "Neotec"
app_description = (
    "Financial analysis cockpit for ERPNext with a local-first AI analyst (NeoNexus). "
    "Period / Dimension / Years / Combo on every report, per-report dimension "
    "provisioning, variance & ratio analysis, bilingual EN/AR."
)
app_email = "info@neotec.ai"
app_license = "mit"

# Apps screen tile -> opens the Desk page
add_to_apps_screen = [
    {
        "name": "neotec_insight_ai",
        "logo": "/assets/neotec_insight_ai/insight/favicon.svg",
        "title": "Neotec Insight AI",
        "route": "/app/insight",
    }
]

after_install = "neotec_insight_ai.install.after_install"
after_migrate = ["neotec_insight_ai.install.after_migrate"]

# No hard ERPNext doc_events here so the app installs on a plain Frappe site too.
