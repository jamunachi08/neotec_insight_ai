# Reporting filter: document date, not fiscal year

**Finding (existing `neotec_insight` engine).** The report engine already fetches by
**document (posting) date**, not by a fiscal-year field. Every GL query's WHERE clause is:

```python
.where(gl.is_cancelled == 0)
.where(gl.account.isin(accounts))
.where(gl.posting_date.between(date_start, date_end))   # ← document date
```

There is **no filter on a `fiscal_year` column** anywhere (`utils/execution.py`,
`api/report.py`). The engine's own note confirms it never uses
`YEAR(posting_date)=fy`. So results are driven by `posting_date`.

**The only fiscal-year dependency** is how `date_start` / `date_end` are *computed*:
`utils/fiscal_year.py → fy_month_range_to_date_range(company, fiscal_year, month_from, month_to)`
derives the window from the selected fiscal year **and the company's
`Company.year_start_date`**. If that company setting is wrong, or the FY does not
start in January, the window shifts — which can look like fiscal-year filtering.

## Make the window purely date-driven

### This app (`neotec_insight_ai`)
Already done. The cockpit uses **From date / To date** inputs; fiscal year is only a
preset that fills them. `api.run_report(report, from_date, to_date, ...)` filters on
`GL Entry.posting_date BETWEEN from_date AND to_date`. `ask_ai` receives the same dates.

### Existing engine (`neotec_insight`) — minimal patch
Let the report accept an explicit posting-date range and bypass the FY→date derivation.

1. **`utils/execution.py → execute_report(...)`** — add `date_from`/`date_to` params and,
   when present, use them directly instead of deriving from the fiscal year:

```python
def execute_report(report, company, fiscal_year, month_from, month_to,
                   ..., date_from=None, date_to=None):
    ...
    if date_from and date_to:
        date_start, date_end = getdate(date_from), getdate(date_to)
    else:
        from neotec_insight.neotec_insight.utils.fiscal_year import fy_month_range_to_date_range
        date_start, date_end = fy_month_range_to_date_range(
            company, fiscal_year, min(months), max(months))
    # ... pass date_start/date_end into the existing
    #     .where(gl.posting_date.between(date_start, date_end)) calls
```

   Do the same in `_fetch_monthly_for_mappings`, `_fetch_monthly_for_accounts`,
   and `execute_combo_report` (each already calls `fy_month_range_to_date_range`).

2. **`api/report.py`** — accept `date_from`/`date_to` from the frontend and forward them:

```python
@frappe.whitelist()
def run_report(report, company, fiscal_year, month_from=0, month_to=11,
               date_from=None, date_to=None, ...):
    ...
    return execute_report(..., date_from=date_from, date_to=date_to)
```

   (Balance-sheet / equity endpoints already take `from_date` / `as_of_date`.)

3. **Frontend (`RunTab.tsx`)** — add From-date / To-date pickers and send
   `date_from` / `date_to` in the run payload. Keep the Fiscal-year dropdown as a
   one-click preset that fills those dates.

Net effect: the report fetches strictly on `posting_date` between the two dates the
user picks, with no dependency on `Company.year_start_date` or any FY tagging.
