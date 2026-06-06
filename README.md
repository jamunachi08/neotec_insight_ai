# Neotec Insight AI

> Financial analysis cockpit for ERPNext, with a **local-first AI analyst** — by **Neotec Integrated Solution** · `info@neotec.ai`

A Frappe app that turns your P&L, Balance Sheet, Trial Balance and Cash Flow into a
decision cockpit: every report supports **Period / Dimension / Years / Combo** views,
per-report **dimension provisioning**, live **variance & ratio analysis**, a scalable
**column manager** (built for 100+ cost centers), and a bilingual **EN/AR** assistant —
**Neotec AI** — powered by your own NeoNexus / Ollama / OpenAI-compatible model.

---

## Highlights

- **VIEW BY on every report** — Period, Dimension, Years, Combo. Which modes a report
  exposes is configurable per report (`Insight Report Definition`), so new reports
  inherit the full set automatically.
- **Dimension provisioning** — choose which dimensions (cost center, project,
  department, branch, custom) a report can pivot/filter by. Default: all on.
- **Column manager** — search, pin and toggle dimensions from a popover instead of a
  wall of chips. Scales to hundreds of values.
- **Analysis cockpit** — KPI sparklines, top-5 budget variance bars, and report-aware
  ratios (margins, current ratio, FCF, cash conversion, …).
- **Heatmap** pivot, **CAGR** in the Years view.
- **Neotec AI** — executive summary, budget-variance explainer, YoY drivers, cost-center
  ranking, and full-year forecast. Bilingual EN/AR with RTL. Runs against a **local**
  model: nothing leaves your network.

---

## Requirements

- A Frappe / ERPNext bench (v15+ recommended)
- (Optional, for live AI) a running model endpoint — NeoNexus, Ollama, LM Studio, or any
  OpenAI-compatible API

---

## Install

```bash
# from your bench directory
bench get-app /path/to/neotec_insight_ai      # or a git URL
bench --site your.site install-app neotec_insight_ai
bench --site your.site migrate
bench build --app neotec_insight_ai
```

Open it at **`/app/insight`** (also on the Apps screen and the **Neotec Insight AI**
workspace). It works immediately with a built-in sample dataset.

---

## Configure the AI (NeoNexus)

1. Go to **Insight Settings** (Desk search → "Insight Settings", or the workspace).
2. Tick **Enable AI assistant**.
3. Set **AI Endpoint** — e.g. `http://host.docker.internal:11434/v1` for Ollama, or your
   NeoNexus / OpenAI-compatible base URL (must end in `/v1`).
4. Set **AI Model** (e.g. `llama3.3`, `qwen2.5`, `gpt-4o`) and an **API Key** if needed.
5. Open the cockpit and click **✦ Ask Neotec AI**. The status dot turns green when
   connected; otherwise the assistant runs locally on the on-screen figures.

The bridge calls `POST {endpoint}/chat/completions` with your report context — the same
contract NeoNexus and every OpenAI-compatible server speaks.

---

## Arabic (العربية) — full localization

The cockpit is fully bilingual with right-to-left layout. The language toggle (top-right)
switches **everything**: UI chrome, report line labels, account / cost-center names, KPI and
column headings, ratios, the dimension manager, the provision modal, and the Neotec AI panel —
which then answers in Arabic.

**Authoring Arabic labels (the provision):**
- **Report name** — `Insight Report Definition → Report Name (Arabic)`.
- **Dimensions** — each row in the report's Dimensions table has a `Label (Arabic)` field.
- **Accounts / report lines** — Arabic line names come from the report engine. When you wire
  `run_report`, return an `label_ar` alongside each row (e.g. from the ERPNext Account's Arabic
  name field). The cockpit shows it automatically in Arabic mode and falls back to the English
  label when no Arabic is set — so Latin brand names stay as-is, which is the expected behaviour.

Numbers stay in Western-Arabic digits (1,234) and render left-to-right inside the RTL tables,
matching Saudi/GCC financial-statement conventions.

## Connecting your real numbers

The bundled cockpit ships with a realistic sample dataset so it looks right on day one.
To drive it from live GL data, implement the documented seam in
`neotec_insight_ai/api.py → run_report(...)`: return `{rows, kpis, headline}` from your
own query, or call into your existing `neotec_insight` report engine. The front-end
already prefers backend data and falls back to the sample only when none is returned.

---

## DocTypes

| DocType | Purpose |
|---|---|
| **Insight Settings** (single) | AI endpoint / model / key, default language |
| **Insight Report Definition** | one per report: type, active, available views, exposed dimensions |
| **Insight Report Dimension** (child) | a dimension a report exposes, with on/off |

---

## Whitelisted API

| Method | Use |
|---|---|
| `neotec_insight_ai.api.get_bootstrap` | reports + AI status for the UI |
| `neotec_insight_ai.api.run_report` | report data (seam for your engine) |
| `neotec_insight_ai.api.ask_ai` | report context + question → AI endpoint |
| `neotec_insight_ai.api.list_models` | discover models from the endpoint |

---

## Uninstall

```bash
bench --site your.site uninstall-app neotec_insight_ai
```

MIT © 2026 Neotec Integrated Solution
