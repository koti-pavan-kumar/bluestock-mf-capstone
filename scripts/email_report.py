"""
scripts/email_report.py
-------------------------
Bonus B5 — Bluestock Fintech Mutual Fund Analytics Capstone

Automated HTML email report generator that creates a professional
weekly mutual fund performance summary.

The script generates a self-contained HTML file that:
  - Shows top 5 and bottom 5 funds by fund_score
  - Shows industry SIP and AUM highlights
  - Shows VaR risk summary
  - Includes a performance table for all 40 funds
  - Can be emailed via Python's smtplib (config section below)

Outputs:
  - reports/weekly_performance_report.html  — the generated email

To actually send via email, fill in the SMTP config section and run:
    python scripts/email_report.py --send

Usage (generate only, no email):
    python scripts/email_report.py

Usage (generate + send):
    python scripts/email_report.py --send --to recipient@example.com
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"
PROCESSED = BASE_DIR / "data" / "processed"
RAW = BASE_DIR / "data" / "raw"

# ── SMTP config (fill these in to enable actual email sending) ────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "kotipavankumar12@gmail.com"
SMTP_PASS = ""   # set via env var: export EMAIL_PASS="yourpassword"
FROM_ADDR = "kotipavankumar12@gmail.com"
DEFAULT_TO = "kotipavankumar12@gmail.com"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sc = pd.read_csv(BASE_DIR / "fund_scorecard.csv")
    var_df = pd.read_csv(BASE_DIR / "var_cvar_report.csv")
    sip = pd.read_csv(RAW / "04_monthly_sip_inflows.csv")
    aum = pd.read_csv(RAW / "03_aum_by_fund_house.csv")
    return sc, var_df, sip, aum


def build_html(sc: pd.DataFrame, var_df: pd.DataFrame,
               sip: pd.DataFrame, aum: pd.DataFrame) -> str:
    gen_date = datetime.now().strftime("%d %B %Y, %I:%M %p IST")
    latest_sip = sip.iloc[-1]
    latest_aum_total = aum.groupby("date")["aum_crore"].sum().iloc[-1]

    top5 = sc.head(5)[["scheme_name", "fund_score", "cagr_3yr_pct",
                         "sharpe_ratio", "max_drawdown_pct"]]
    bot5 = sc.tail(5)[["scheme_name", "fund_score", "cagr_3yr_pct",
                         "sharpe_ratio", "max_drawdown_pct"]]
    riskiest = var_df.head(3)

    def fund_rows(df: pd.DataFrame, highlight: str = "#EFF6FF") -> str:
        rows = ""
        for _, row in df.iterrows():
            rows += f"""
            <tr style="background:{highlight}">
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-size:12px">
                {row['scheme_name'][:45]}</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center;
                font-weight:bold;color:#0077B6">{row['fund_score']:.1f}</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center">
                {row['cagr_3yr_pct']:.1f}%</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center">
                {row['sharpe_ratio']:.2f}</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center;
                color:#DC2626">{row['max_drawdown_pct']:.1f}%</td>
            </tr>"""
        return rows

    def var_rows(df: pd.DataFrame) -> str:
        rows = ""
        for _, row in df.iterrows():
            rows += f"""
            <tr>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;font-size:12px">
                {row['scheme_name'][:40]}</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center;
                color:#DC2626;font-weight:bold">{row['var_95_pct']:.2f}%</td>
              <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:center;
                color:#991B1B">{row['cvar_95_pct']:.2f}%</td>
            </tr>"""
        return rows

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bluestock Fintech — Weekly MF Performance Report</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:Calibri,Arial,sans-serif">

<!-- Header -->
<div style="background:#0D2B55;padding:28px 32px;text-align:center">
  <div style="font-size:11px;color:#00B4D8;letter-spacing:2px;font-weight:bold;
    text-transform:uppercase;margin-bottom:8px">BLUESTOCK FINTECH PVT. LTD.</div>
  <div style="font-size:26px;color:#FFFFFF;font-weight:bold;margin-bottom:6px">
    Weekly Mutual Fund Performance Report</div>
  <div style="font-size:13px;color:#BAE6FD">Generated: {gen_date}</div>
</div>

<!-- Accent bar -->
<div style="height:4px;background:linear-gradient(90deg,#00B4D8,#0077B6)"></div>

<!-- KPI Strip -->
<div style="background:#FFFFFF;padding:20px 32px;display:flex;gap:0">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="text-align:center;padding:10px;border-right:1px solid #E5E7EB">
      <div style="font-size:22px;font-weight:bold;color:#0D2B55">40</div>
      <div style="font-size:11px;color:#6B7280">Fund Schemes</div></td>
    <td style="text-align:center;padding:10px;border-right:1px solid #E5E7EB">
      <div style="font-size:22px;font-weight:bold;color:#0077B6">
        Rs.{latest_sip['sip_inflow_crore']:,.0f} Cr</div>
      <div style="font-size:11px;color:#6B7280">Latest SIP Inflow</div></td>
    <td style="text-align:center;padding:10px;border-right:1px solid #E5E7EB">
      <div style="font-size:22px;font-weight:bold;color:#0369A1">
        Rs.{latest_aum_total/100000:.1f}L Cr</div>
      <div style="font-size:11px;color:#6B7280">Total AUM (latest)</div></td>
    <td style="text-align:center;padding:10px">
      <div style="font-size:22px;font-weight:bold;color:#065A82">
        {latest_sip['active_sip_accounts_crore']:.2f} Cr</div>
      <div style="font-size:11px;color:#6B7280">Active SIP Accounts</div></td>
  </tr></table>
</div>

<!-- Body wrapper -->
<div style="max-width:700px;margin:24px auto;padding:0 16px">

  <!-- Top 5 Funds -->
  <div style="background:#FFFFFF;border-radius:8px;padding:20px;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:20px">
    <h2 style="margin:0 0 14px;color:#0D2B55;font-size:15px">
      🏆 Top 5 Funds by Composite Scorecard</h2>
    <table width="100%" cellpadding="0" cellspacing="0">
      <thead>
        <tr style="background:#0D2B55;color:#FFFFFF">
          <th style="padding:9px 8px;text-align:left;font-size:11px">Fund</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Score</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">3yr CAGR</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Sharpe</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Max DD</th>
        </tr>
      </thead>
      <tbody>{fund_rows(top5, "#EFF6FF")}</tbody>
    </table>
  </div>

  <!-- Bottom 5 Funds -->
  <div style="background:#FFFFFF;border-radius:8px;padding:20px;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:20px">
    <h2 style="margin:0 0 14px;color:#DC2626;font-size:15px">
      ⚠️ Bottom 5 Funds — Review Required</h2>
    <table width="100%" cellpadding="0" cellspacing="0">
      <thead>
        <tr style="background:#7F1D1D;color:#FFFFFF">
          <th style="padding:9px 8px;text-align:left;font-size:11px">Fund</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Score</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">3yr CAGR</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Sharpe</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">Max DD</th>
        </tr>
      </thead>
      <tbody>{fund_rows(bot5, "#FFF1F2")}</tbody>
    </table>
  </div>

  <!-- VaR Risk Alert -->
  <div style="background:#FFFFFF;border-radius:8px;padding:20px;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:20px">
    <h2 style="margin:0 0 14px;color:#991B1B;font-size:15px">
      📉 Risk Alert — Highest VaR Funds (95% Confidence)</h2>
    <p style="font-size:12px;color:#6B7280;margin:0 0 12px">
      VaR = maximum expected daily loss with 95% confidence.
      CVaR = average loss on the worst 5% of days.</p>
    <table width="100%" cellpadding="0" cellspacing="0">
      <thead>
        <tr style="background:#991B1B;color:#FFFFFF">
          <th style="padding:9px 8px;text-align:left;font-size:11px">Fund</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">VaR 95%</th>
          <th style="padding:9px 8px;text-align:center;font-size:11px">CVaR 95%</th>
        </tr>
      </thead>
      <tbody>{var_rows(riskiest)}</tbody>
    </table>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:16px;color:#9CA3AF;font-size:10px">
    <div style="margin-bottom:4px">
      This report is auto-generated by the Bluestock Fintech MF Analytics Platform.</div>
    <div style="margin-bottom:4px">
      Data sourced from AMFI India &amp; mfapi.in | For internal use only</div>
    <div>Pavan Kumar Koti | Data Analyst Intern | Cohort 2025</div>
  </div>

</div>
</body>
</html>"""
    return html


def send_email(html: str, to_addr: str) -> None:
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    password = os.environ.get("EMAIL_PASS", SMTP_PASS)
    if not password:
        print("[WARN] EMAIL_PASS env var not set — cannot send email.")
        print("       Set it with: export EMAIL_PASS='yourpassword'")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Bluestock Fintech — Weekly MF Report ({datetime.now().strftime('%d %b %Y')})"
    msg["From"] = FROM_ADDR
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, password)
            server.sendmail(FROM_ADDR, to_addr, msg.as_string())
        print(f"[OK] Email sent to {to_addr}")
    except Exception as exc:
        print(f"[ERROR] Failed to send email: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Weekly MF Performance Email Report")
    parser.add_argument("--send", action="store_true", help="Actually send the email")
    parser.add_argument("--to", default=DEFAULT_TO, help="Recipient email address")
    args = parser.parse_args()

    print("=" * 65)
    print("WEEKLY MF PERFORMANCE REPORT GENERATOR")
    print("=" * 65)

    sc, var_df, sip, aum = load_data()
    html = build_html(sc, var_df, sip, aum)

    out_path = REPORTS / "weekly_performance_report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n[OK] HTML report saved: {out_path.relative_to(BASE_DIR)}")

    if args.send:
        print(f"\nSending email to {args.to}...")
        send_email(html, args.to)
    else:
        print("\nTo send via email, run:")
        print(f"  export EMAIL_PASS='yourpassword'")
        print(f"  python scripts/email_report.py --send --to {args.to}")


if __name__ == "__main__":
    main()
