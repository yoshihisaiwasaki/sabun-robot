import io
import os
import re
import unicodedata
from decimal import Decimal
from datetime import date, datetime

import pandas as pd
import streamlit as st
import stripe
from openpyxl import load_workbook


APP_NAME = "Sabun Robot"
VERSION = "0.2-payment"

PAYMENT_URL = os.getenv(
    "SABUN_PAYMENT_URL",
    "https://buy.stripe.com/00wdRb7ch1jZ51K6dx9fW01",
).strip()


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🤖",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 920px;
        padding-top: 2rem;
    }
    .hero {
        text-align: center;
        padding: 1rem 0;
    }
    .hero h1 {
        font-size: 3rem;
        margin-bottom: .2rem;
    }
    .small {
        opacity: .7;
        font-size: .9rem;
    }
    .card {
        border: 1px solid rgba(128,128,128,.3);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin: .6rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def norm(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKC", str(v)).strip(),
    )


def num(v):
    try:
        return Decimal(
            str(v)
            .replace(",", "")
            .replace("¥", "")
            .replace("$", "")
            .strip()
        )
    except Exception:
        return None


def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "(blank)"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def load_tables(upload):
    name = upload.name.lower()
    data = upload.getvalue()

    if name.endswith(".csv"):
        return {
            "CSV": pd.read_csv(
                io.BytesIO(data),
                dtype=object,
            )
        }

    if name.endswith(".xlsx"):
        wb = load_workbook(
            io.BytesIO(data),
            data_only=True,
            read_only=True,
        )

        out = {}

        for ws in wb.worksheets:
            values = list(ws.values)

            if not values:
                continue

            best_idx = 0
            best_score = -1

            for i, row in enumerate(values[:20]):
                vals = [norm(x) for x in row if norm(x)]
                score = len(set(vals)) if len(vals) >= 2 else -1

                if score > best_score:
                    best_idx = i
                    best_score = score

            header = [
                norm(x) or f"Column_{j + 1}"
                for j, x in enumerate(values[best_idx])
            ]

            width = len(header)
            rows = []

            for r in values[best_idx + 1:]:
                rows.append(
                    list(r[:width])
                    + [None] * max(0, width - len(r))
                )

            out[ws.title] = pd.DataFrame(
                rows,
                columns=header,
            ).dropna(how="all")

        return out

    raise ValueError(
        "Please upload .xlsx or .csv files."
    )


def compare(prev_df, cur_df, key):
    prev_df = prev_df.copy()
    cur_df = cur_df.copy()

    prev_df.columns = [
        norm(c) for c in prev_df.columns
    ]
    cur_df.columns = [
        norm(c) for c in cur_df.columns
    ]

    key = norm(key)

    if (
        key not in prev_df.columns
        or key not in cur_df.columns
    ):
        raise ValueError(
            f'Key column "{key}" must exist in both files.'
        )

    def records(df):
        out = {}
        dup = set()

        for _, row in df.iterrows():
            k = norm(row.get(key))

            if not k:
                continue

            if k in out:
                dup.add(k)

            out[k] = {
                c: row.get(c)
                for c in df.columns
            }

        return out, dup

    a, da = records(prev_df)
    b, db = records(cur_df)

    changes = []

    common = [
        c
        for c in prev_df.columns
        if c in cur_df.columns and c != key
    ]

    for k in sorted(set(a) | set(b)):

        if k not in a:
            changes.append(
                {
                    "status": "ADDED",
                    "item": k,
                    "field": "Record",
                    "before": "—",
                    "after": "Added",
                    "delta": "",
                }
            )
            continue

        if k not in b:
            changes.append(
                {
                    "status": "REMOVED",
                    "item": k,
                    "field": "Record",
                    "before": "Present",
                    "after": "Removed",
                    "delta": "",
                }
            )
            continue

        for c in common:
            av = a[k].get(c)
            bv = b[k].get(c)

            if norm(av) != norm(bv):
                d = ""
                na = num(av)
                nb = num(bv)

                if na is not None and nb is not None:
                    d = str(nb - na)

                changes.append(
                    {
                        "status": "CHANGED",
                        "item": k,
                        "field": c,
                        "before": fmt(av),
                        "after": fmt(bv),
                        "delta": d,
                    }
                )

    return changes, sorted(da | db)


def verify_payment():
    session_id = st.query_params.get("session_id")

    if not session_id:
        return False

    try:
        secret_key = st.secrets["STRIPE_SECRET_KEY"]
        stripe.api_key = secret_key

        session = stripe.checkout.Session.retrieve(
            session_id
        )

        payment_status = session.get(
            "payment_status"
        )

        amount_total = session.get(
            "amount_total"
        )

        currency = session.get(
            "currency"
        )

        if (
            payment_status == "paid"
            and amount_total == 900
            and currency == "usd"
        ):
            return True

    except Exception:
        return False

    return False


paid = verify_payment()


st.markdown(
    """
    <div class='hero'>
        <h1>🤖 Sabun Robot</h1>
        <p><b>See exactly what changed.</b></p>
        <div class='small'>
            “Sabun” means “difference” in Japanese.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if paid:
    st.success(
        "✓ Payment verified. Full Report is unlocked."
    )

st.write(
    "Stop comparing recurring spreadsheets manually. "
    "Upload the previous report and the latest report. "
    "Sabun Robot shows exactly **what changed, "
    "where it changed, and before → after**."
)

st.write(
    "**ADDED · REMOVED · CHANGED**"
)


c1, c2 = st.columns(2)

with c1:
    previous = st.file_uploader(
        "1. Previous report",
        type=["xlsx", "csv"],
    )

with c2:
    latest = st.file_uploader(
        "2. Latest report",
        type=["xlsx", "csv"],
    )


if previous and latest:

    try:
        p = load_tables(previous)
        q = load_tables(latest)

        sheets = [
            s for s in p
            if s in q
        ]

        if not sheets:
            st.error(
                "No matching sheet name was found."
            )
            st.stop()

        sheet = st.selectbox(
            "Sheet to compare",
            sheets,
        )

        pdf = p[sheet]
        cdf = q[sheet]

        cols = [
            c for c in pdf.columns
            if c in cdf.columns
        ]

        if not cols:
            st.error(
                "No matching columns were found."
            )
            st.stop()

        key = st.selectbox(
            "Which column uniquely identifies each row?",
            cols,
            help=(
                "Examples: Project ID, Customer ID, "
                "Order Number, Company Name."
            ),
        )

        if st.button(
            "COMPARE FREE",
            type="primary",
            use_container_width=True,
        ):
            changes, dups = compare(
                pdf,
                cdf,
                key,
            )

            st.session_state["changes"] = changes
            st.session_state["dups"] = dups

        if "changes" in st.session_state:

            changes = st.session_state["changes"]
            dups = st.session_state.get(
                "dups",
                [],
            )

            if dups:
                st.warning(
                    "Duplicate key values found; "
                    "results may be ambiguous: "
                    + ", ".join(dups[:10])
                )

            if not changes:
                st.success(
                    "✓ I found no changes."
                )

            else:
                st.success(
                    f"✓ I found {len(changes)} changes."
                )

                a, b, c = st.columns(3)

                a.metric(
                    "Added",
                    sum(
                        x["status"] == "ADDED"
                        for x in changes
                    ),
                )

                b.metric(
                    "Removed",
                    sum(
                        x["status"] == "REMOVED"
                        for x in changes
                    ),
                )

                c.metric(
                    "Changed",
                    sum(
                        x["status"] == "CHANGED"
                        for x in changes
                    ),
                )

                if paid:

                    st.markdown(
                        "### Full Report"
                    )

                    report_df = pd.DataFrame(
                        changes
                    )

                    st.dataframe(
                        report_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    csv_data = report_df.to_csv(
                        index=False
                    ).encode("utf-8-sig")

                    st.download_button(
                        "DOWNLOAD FULL REPORT (CSV)",
                        data=csv_data,
                        file_name="sabun_robot_full_report.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                else:

                    st.markdown(
                        "### Free preview"
                    )

                    x = changes[0]

                    st.markdown(
                        f"""
                        <div class='card'>
                            <b>{x['status']}</b><br>
                            <b>{x['item']}</b><br>
                            {x['field']}<br>
                            <b>
                                {x['before']}
                                →
                                {x['after']}
                            </b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"### Unlock all "
                        f"{len(changes)} changes "
                        f"— **US$9**"
                    )

                    st.caption(
                        "See every changed item and "
                        "download the full change report."
                    )

                    if PAYMENT_URL:
                        st.link_button(
                            "UNLOCK FULL REPORT — $9",
                            PAYMENT_URL,
                            use_container_width=True,
                        )
                    else:
                        st.info(
                            "Payment link is not configured."
                        )

    except Exception as e:
        st.error(
            f"Could not compare these files: {e}"
        )


st.divider()

st.caption(
    "Sabun Robot finds changes. "
    "You decide what they mean. "
    "Your original files are not modified."
)

st.caption(
    f"{APP_NAME} {VERSION}"
)