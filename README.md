# Sabun Robot v0.1 — Validation Build

**See exactly what changed.**

Minimum validation build: two XLSX/CSV files → ADDED / REMOVED / CHANGED → exact field and before → after → one free preview → US$9 unlock.

## Run on Windows
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
Open `http://localhost:8501`.

## Activate the $9 Stripe button
Create one Stripe Payment Link for **Sabun Robot — Full Comparison — US$9 one-time**.

Before starting Streamlit:
```powershell
$env:SABUN_PAYMENT_URL="PASTE_YOUR_STRIPE_PAYMENT_LINK_HERE"
streamlit run app.py
```
Do not put Stripe secret keys in the app.

## Before public launch
Remove the **Owner test mode — full results** expander. It exists only to verify the engine before payment is live.

## Validation KPI
**PASS #1 = one complete stranger pays US$9 without a personal sales conversation.**


## Payment link configured
The validation build is preconfigured with the live US$9 Stripe Payment Link:
https://buy.stripe.com/00wdRb7ch1jZ51K6dx9fW01
