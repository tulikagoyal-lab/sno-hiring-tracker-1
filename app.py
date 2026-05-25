import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import warnings
import json
import os

warnings.filterwarnings("ignore")

# ═════════════════════════════════════════════════════
# Snowflake Connection
# ═════════════════════════════════════════════════════

@st.cache_resource(ttl=300)
def get_snowflake_conn():
    try:
        import snowflake.connector
        token = None
        account = None
        warehouse = None
        role = None
        try:
            sf = st.secrets["snowflake"]
            token = sf["access_token"]
            account = sf.get("account", "GZAVXAB-SWIGGY_MUMBAI")
            warehouse = sf.get("warehouse", "NONTECH_WH_01")
            role = sf.get("role", "DRIVERS_ORG")
        except:
            token = os.environ.get("SNOWFLAKE_ACCESS_TOKEN", "")
            account = os.environ.get("SNOWFLAKE_ACCOUNT", "GZAVXAB-SWIGGY_MUMBAI")
            warehouse = "NONTECH_WH_01"
            role = os.environ.get("SNOWFLAKE_ROLE", "DRIVERS_ORG")
        if not token:
            return None
        conn = snowflake.connector.connect(
            account=account, authenticator="oauth", token=token,
            warehouse=warehouse, role=role,
        )
        cur = conn.cursor()
        cur.execute(f"USE WAREHOUSE {warehouse}")
        return conn
    except Exception as e:
        st.warning(f"Snowflake: {e}")
        return None

@st.cache_data(ttl=3600)
def fetch_orders_from_snowflake(d1, d2):
    conn = get_snowflake_conn()
    if conn is None:
        return None
    query = f"""
    with cte as(
    select dt, city_name, order_flag, count(distinct order_id) orders,
    case when order_flag = 'Instamart' then 'IM' else 'Food' end as fleet,
    case when city_name in ('Chennai','Ahmedabad','Hyderabad','Delhi','Bangalore','Mumbai','Vijayawada','Indore','Jaipur','Noida','Kochi','Kolkata','Lucknow','Thiruvananthapuram','Madurai','Pune','Central Goa','Gorakhpur','Kanpur','Pondicherry','Surat','Bhubaneswar','Vizag','Mysore','Noida 1','Dehradun','Guwahati','Tirupur','Chandigarh','Faridabad','Gurgaon','Manipal','Coimbatore','Thrissur','Patna','Vadodara','Rajkot','Agra','Varanasi','Amritsar','Mangaluru','Ludhiana','Raipur') then 'SNO' else 'SOC' end as City_Type
    from (
    select distinct order_id, case when POST_STATUS in ('Completed') then 'Completed' else 'Cancelled' end POST_STATUS,
    ORDERED_TIME, m.city_id::varchar as city_id, c.name city_name,
    (case when lower(delivery_partner) in ('rapido','shadowfax','loadshare','adloggs') then 'SFX_Food'
    when lower(delivery_partner) in ('dominos','petpooja','urbanpiper','faasos','eatclub','popeyes') then 'Dominos_Food'
    else 'Food' end) Order_Flag, dt
    from facts.public.dp_order_fact m
    left join de.swiggy.area a on a.id=m.area_id
    left join de.swiggy.zone z on z.id=a.zone_id
    left join de.swiggy.city c on c.id=z.city_id
    where to_date(dt) between '{d1}' and '{d2}'
    and restaurant_id not in (select distinct restaurant_id from analytics.public.restaurant_attributes
    where (business_classifier='Stores Lite' or parent_id in ('591159')))
    and lower(post_status)='completed' and ignore_order_flag=0
    group by all
    union all
    select distinct a.order_id, case when status in ('DELIVERY_DELIVERED') then 'Completed' else 'Cancelled' end POST_STATUS,
    a.ORDERED_TIME, a.CITY_ID, a.city, 'Instamart' ORDER_FLAG, a.dt
    from analytics.public.IM_PARENT_ORDER_FACT a
    where a.status='DELIVERY_DELIVERED' and a.dt between '{d1}' and '{d2}'
    group by all
    union all
    select distinct id order_id, case when status in ('DELIVERY_DELIVERED') then 'Completed' else 'Cancelled' end POST_STATUS,
    ORDERED_TIME, city_id::varchar city_id, city,
    (case when lower(type) in ('instamart') and lower(city) not in ('budhwal') then 'Instamart'
    when lower(CATEGORY) ilike '%liquor%' then 'Alcohol' else 'stores' end) order_flag, dt
    from ANALYTICS.PUBLIC.STORES_ORDER_FACT
    where dt between '{d1}' and '{d2}' and lower(CATEGORY) ilike '%liquor%' and status in ('DELIVERY_DELIVERED')
    union all
    select distinct id order_id, case when status in ('DELIVERY_DELIVERED') then 'Completed' else 'Cancelled' end POST_STATUS,
    ORDERED_TIME, city_id::varchar city_id, city,
    (case when ORDER_TYPE is not null then 'Genie' end) order_flag, dt
    from ANALYTICS.PUBLIC.GENIE_ORDER_FACT
    where dt between '{d1}' and '{d2}' and status in ('DELIVERY_DELIVERED')
    union all
    select distinct id order_id, case when status in ('DELIVERY_DELIVERED') then 'Completed' else 'Cancelled' end POST_STATUS,
    ORDERED_TIME, city_id::varchar city_id, city,
    (case when SID is not null then 'Genie' end) order_flag, dt
    from ANALYTICS.PUBLIC.GENIE_B2B_ORDER_FACT
    where dt between '{d1}' and '{d2}' and status in ('DELIVERY_DELIVERED')
    union all
    select order_id, ORDER_STATUS POST_STATUS, ordered_time, a.city_id, b.name city, 'Snacc' ORDER_FLAG, to_date(dt) dt
    from ANALYTICS.PUBLIC.SNACC_ORDER_FACT a
    left join de.swiggy.city b on a.city_id=b.id
    where lower(CATEGORY) in ('snacc') and lower(ORDER_STATUS) in ('completed')
    and dt between '{d1}' and '{d2}'
    ) group by all order by city_name
    )
    select City_Type, fleet, sum(orders) as total_orders
    from cte group by 1, 2 order by 1, 2
    """
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        results = {"SNO_Food": 0, "SNO_IM": 0, "SOC_Food": 0, "SOC_IM": 0, "SNO_Total": 0, "SOC_Total": 0}
        for row in rows:
            ct, fl, od = row[0], row[1], int(row[2])
            results[f"{ct}_{fl}"] = od
            results[f"{ct}_Total"] += od
        return results
    except Exception as e:
        st.error(f"Query failed: {e}")
        return None
    finally:
        try: cur.close()
        except: pass

def get_last_week_dates():
    today = datetime.now()
    lm = today - timedelta(days=today.weekday() + 7)
    ls = lm + timedelta(days=6)
    return lm.strftime("%Y-%m-%d"), ls.strftime("%Y-%m-%d")

# ═════════════════════════════════════════════════════
# Google Sheets
# ═════════════════════════════════════════════════════

SHEET_ID = "116n7chDnpyh14Z4TTL7jEBRG1XoYDGzE_O01JCI6iPc"
SHEET_GID = "37744413"

@st.cache_resource
def get_gsheet_client():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
        return gspread.authorize(creds)
    except:
        return None

def get_sheet():
    client = get_gsheet_client()
    if client is None:
        return None
    try:
        sheet = client.open_by_key(SHEET_ID)
        try:
            return sheet.get_worksheet_by_id(int(SHEET_GID))
        except:
            return sheet.sheet1
    except:
        return None

def read_all_submissions():
    ws = get_sheet()
    if ws is None:
        return []
    records = ws.get_all_records()
    subs = []
    for row in records:
        for mk, val in row.items():
            if mk in ["channel", "week_label", "submitted_at"]:
                continue
            try:
                v = float(val) if val and str(val).strip() != "" else 0.0
            except:
                v = 0.0
            if v != 0:
                subs.append({"channel": row.get("channel", ""), "week_label": row.get("week_label", ""),
                            "metric": mk, "value": v})
    return subs

def write_submission(channel, week_label, data):
    ws = get_sheet()
    if ws is None:
        st.error("Google Sheets not connected.")
        return False
    try:
        all_records = ws.get_all_records()
        headers = ws.row_values(1)
        all_keys = sorted(set(data.keys()))
        expected = ["channel", "week_label", "submitted_at"] + all_keys
        if set(expected) != set(headers) or not headers:
            ws.clear()
            ws.append_row(expected)
            headers = expected

        row_idx = None
        for i, rec in enumerate(all_records):
            if rec.get("channel") == channel and rec.get("week_label") == week_label:
                row_idx = i + 2
                break

        now = datetime.now().isoformat()
        row_data = {"channel": channel, "week_label": week_label, "submitted_at": now}
        row_data.update(data)
        row_list = [row_data.get(h, "") for h in headers]

        if row_idx:
            for ci, val in enumerate(row_list):
                ws.update_cell(row_idx, ci + 1, val)
        else:
            ws.append_row(row_list)
        return True
    except Exception as e:
        st.error(f"Sheet error: {e}")
        return False

def write_orders_to_sheet(week_label, orders_data):
    channel = "Auto-Fetch (Orders)"
    data = {
        "orders_sno": float(orders_data.get("SNO_Total", 0)),
        "orders_soc": float(orders_data.get("SOC_Total", 0)),
        "orders_sno_food": float(orders_data.get("SNO_Food", 0)),
        "orders_sno_im": float(orders_data.get("SNO_IM", 0)),
        "orders_soc_food": float(orders_data.get("SOC_Food", 0)),
        "orders_soc_im": float(orders_data.get("SOC_IM", 0)),
    }
    return write_submission(channel, week_label, data)

# ═════════════════════════════════════════════════════
# Channel Definitions
# ═════════════════════════════════════════════════════

CHANNELS = {
    "SNO Channel": {
        "passcode": "sno123",
        "sections": {
            "Orders (SNO)": ["orders_sno"],
            "SNO Hiring": ["sno_spillover_28", "sno_cpfod_ref", "sno_cpfod_rb_override", "sno_cpfod_agency", "sno_rejoiner"],
            "SNO Absolute Cost": [
                "cost_flatpay", "cost_leakage", "cost_shouldering", "cost_dormant_rb",
                "cost_impersonation", "cost_jb", "cost_rb_cpfod", "cost_rb_fod",
                "cost_ref_override_cpfod", "cost_ref_override_fod", "cost_spillover_28",
                "cost_agency", "cost_google_supper", "cost_google_extra", "cost_google_fresh_fod",
                "cost_google_im_app", "cost_google_im_1st", "cost_google_extra_1st",
                "cost_upfront_fee", "cost_insurance", "cost_ob_fee",
                "cost_apsflyer", "cost_pivot_roots", "cost_autodialer",
                "cost_bgv_fresh", "cost_bgv_address", "cost_bgv_rejoiner",
                "cost_sms_fresh", "cost_sms_rejoiner",
                "cost_whatsapp_fresh", "cost_whatsapp_rejoiner",
                "cost_obe_rtc", "cost_fr_salary", "cost_fr_count",
                "cost_fr_tl_salary", "cost_fr_tl_count", "cost_btl",
                "cost_fr_incentive", "cost_influencer_payout",
                "cost_inf_tl_salary", "cost_inf_tl_count",
                "cost_spillover_over_28", "cost_other_mult", "cost_other_val",
            ],
            "SNO Same Week Transacting": ["transact_ref", "transact_google", "transact_affiliate", "transact_ssu", "transact_fr", "transact_agency", "transact_influencers"],
            "SNO Spill Over FOD": ["spill_fod_ref", "spill_fod_google", "spill_fod_affiliate", "spill_fod_ssu", "spill_fod_fr", "spill_fod_agency", "spill_fod_influencers"],
            "SNO Onboarding": ["onboard_ref", "onboard_google", "onboard_affiliate", "onboard_ssu", "onboard_fr", "onboard_agency", "onboard_influencers"],
        }
    },
    "SOC Channel": {
        "passcode": "soc123",
        "sections": {
            "Orders (SOC)": ["orders_soc"],
            "SOC Hiring": ["soc_fresh_onboard", "soc_rejoiner", "soc_spillover_28", "soc_spillover_over_28"],
            "SOC CPH": ["soc_cpod_ref"],
            "SOC Absolute Cost": [
                "soc_rejoiner_cost", "soc_jb_cost", "soc_rb_cpfod", "soc_cost_spillover_28",
                "soc_cost_spillover_over_28", "soc_jb_adjust", "soc_rb_adjust",
                "soc_agency_cost", "soc_google_im", "soc_google_supper",
                "soc_google_im_sa_fod", "soc_google_sf_sa_fod", "soc_extra_im",
                "soc_upfront_fee", "soc_insurance", "soc_ob_fee", "soc_ob_fees_actual",
                "soc_bgv", "soc_sms_fresh", "soc_sms_rejoiner",
                "soc_whatsapp_fresh", "soc_whatsapp_rejoiner",
                "soc_btl", "soc_tc_incentive", "soc_fr_count", "soc_tl_count",
                "soc_fr_initiatives", "soc_fr_extra",
            ],
            "SOC Same Week Transacting": ["soc_transact_ref", "soc_transact_google", "soc_transact_affiliate", "soc_transact_ssu", "soc_transact_fr", "soc_transact_agency", "soc_transact_goldmine", "soc_transact_influencers"],
            "SOC Spill Over FOD": ["soc_spill_fod_ref", "soc_spill_fod_google", "soc_spill_fod_affiliate", "soc_spill_fod_ssu", "soc_spill_fod_fr", "soc_spill_fod_agency", "soc_spill_fod_influencers"],
        }
    },
    "Agency Channel": {
        "passcode": "agency123",
        "sections": {
            "SNO Agency Cost": ["cost_agency"],
            "SNO Agency Transacting": ["transact_agency"],
            "SNO Agency Spillover": ["spill_fod_agency"],
            "SNO Agency Onboarding": ["onboard_agency"],
            "SOC Agency Cost": ["soc_agency_cost"],
            "SOC Agency Transacting": ["soc_transact_agency"],
            "SOC Agency Spillover": ["soc_spill_fod_agency"],
        }
    },
    "Google Channel": {
        "passcode": "google123",
        "sections": {
            "SNO Google Costs": ["cost_google_supper", "cost_google_extra", "cost_google_fresh_fod", "cost_google_im_app", "cost_google_im_1st", "cost_google_extra_1st"],
            "SNO Google Transacting": ["transact_google"],
            "SNO Google Spillover": ["spill_fod_google"],
            "SNO Google Onboarding": ["onboard_google"],
            "SOC Google Costs": ["soc_google_im", "soc_google_supper", "soc_google_im_sa_fod", "soc_google_sf_sa_fod", "soc_extra_im"],
            "SOC Google Transacting": ["soc_transact_google"],
            "SOC Google Spillover": ["soc_spill_fod_google"],
        }
    },
    "Referral Channel": {
        "passcode": "ref123",
        "sections": {
            "SNO Referral CPFOD": ["sno_cpfod_ref", "sno_cpfod_rb_override"],
            "SNO Referral Cost": ["cost_rb_cpfod", "cost_rb_fod", "cost_ref_override_cpfod", "cost_ref_override_fod"],
            "SNO Referral Transacting": ["transact_ref"],
            "SNO Referral Spillover": ["spill_fod_ref"],
            "SNO Referral Onboarding": ["onboard_ref"],
            "SOC Referral CPOD": ["soc_cpod_ref"],
            "SOC Referral Cost": ["soc_rb_cpfod"],
            "SOC Referral Transacting": ["soc_transact_ref"],
            "SOC Referral Spillover": ["soc_spill_fod_ref"],
        }
    },
    "FR Channel": {
        "passcode": "fr123",
        "sections": {
            "SNO FR": ["cost_fr_salary", "cost_fr_count", "cost_fr_tl_salary", "cost_fr_tl_count", "cost_fr_incentive"],
            "SNO FR Transacting": ["transact_fr"],
            "SNO FR Spillover": ["spill_fod_fr"],
            "SNO FR Onboarding": ["onboard_fr"],
            "SOC FR": ["soc_fr_count", "soc_tl_count", "soc_fr_initiatives", "soc_fr_extra"],
            "SOC FR Transacting": ["soc_transact_fr"],
            "SOC FR Spillover": ["soc_spill_fod_fr"],
        }
    },
    "Influencer Channel": {
        "passcode": "inf123",
        "sections": {
            "SNO Influencer Cost": ["cost_influencer_payout", "cost_inf_tl_salary", "cost_inf_tl_count"],
            "SNO Influencer Transacting": ["transact_influencers"],
            "SNO Influencer Spillover": ["spill_fod_influencers"],
            "SNO Influencer Onboarding": ["onboard_influencers"],
            "SOC Influencer Transacting": ["soc_transact_influencers"],
            "SOC Influencer Spillover": ["soc_spill_fod_influencers"],
        }
    },
    "Rejoiner & Spillover": {
        "passcode": "rej123",
        "sections": {
            "SNO Rejoiner": ["sno_rejoiner"],
            "SNO Spillover Cost": ["sno_spillover_28", "cost_spillover_28", "cost_spillover_over_28"],
            "SNO Spillover FOD": ["spill_fod_ref", "spill_fod_google", "spill_fod_affiliate", "spill_fod_ssu", "spill_fod_fr", "spill_fod_agency", "spill_fod_influencers"],
            "SOC Rejoiner": ["soc_rejoiner", "soc_rejoiner_cost"],
            "SOC Spillover Cost": ["soc_spillover_28", "soc_spillover_over_28", "soc_cost_spillover_28", "soc_cost_spillover_over_28"],
            "SOC Spillover FOD": ["soc_spill_fod_ref", "soc_spill_fod_google", "soc_spill_fod_affiliate", "soc_spill_fod_ssu", "soc_spill_fod_fr", "soc_spill_fod_agency", "soc_spill_fod_influencers"],
        }
    },
    "Comms Channel": {
        "passcode": "comms123",
        "sections": {
            "SNO SMS": ["cost_sms_fresh", "cost_sms_rejoiner"],
            "SNO WhatsApp": ["cost_whatsapp_fresh", "cost_whatsapp_rejoiner"],
            "SNO OBE/RTC": ["cost_obe_rtc"],
            "SNO Autodialer": ["cost_autodialer"],
            "SNO BGV Fresh": ["cost_bgv_fresh", "cost_bgv_address"],
            "SNO BGV Rejoiner": ["cost_bgv_rejoiner"],
            "SNO Misc": ["cost_apsflyer", "cost_pivot_roots", "cost_btl"],
            "SOC SMS": ["soc_sms_fresh", "soc_sms_rejoiner"],
            "SOC WhatsApp": ["soc_whatsapp_fresh", "soc_whatsapp_rejoiner"],
            "SOC BGV": ["soc_bgv"],
            "SOC TC Incentive": ["soc_tc_incentive"],
            "SOC BTL": ["soc_btl"],
        }
    },
}

USERS = {}
for cn, cd in CHANNELS.items():
    USERS[cn] = {"hash": hashlib.sha256(cd["passcode"].encode()).hexdigest()[:12], "admin": False}
USERS["Tulika"] = {"hash": hashlib.sha256("admin123".encode()).hexdigest()[:12], "admin": True}

METRIC_LABELS = {}
ALL_METRICS_SET = set()
for cd in CHANNELS.values():
    for keys in cd["sections"].values():
        for k in keys:
            ALL_METRICS_SET.add(k)
            if k not in METRIC_LABELS:
                METRIC_LABELS[k] = k.replace("_", " ").title()

def chk(raw): return hashlib.sha256(raw.encode()).hexdigest()[:12]
def wkl(dt): return f"WK{dt.isocalendar()[1]}-{dt.year}"
def cur_ws(): return datetime.now() - timedelta(days=datetime.now().weekday())

# ── UI ──
st.set_page_config(page_title="SNO Hiring Cost Tracker", layout="wide")
st.markdown("<style>.metric-card{background:#f0f2f6;border-radius:10px;padding:20px;text-align:center}.metric-value{font-size:28px;font-weight:bold;color:#1f77b4}.metric-label{font-size:14px;color:#666}</style>", unsafe_allow_html=True)

for k in ["logged_in", "user", "is_admin"]:
    if k not in st.session_state:
        st.session_state[k] = None if k == "user" else False

def login_page():
    st.title("SNO Hiring Cost Tracker")
    _, c, _ = st.columns([1, 2, 1])
    with c:
        st.markdown("### Login")
        n = st.text_input("Name")
        p = st.text_input("Passcode", type="password")
        if st.button("Login", use_container_width=True):
            u = USERS.get(n)
            if u and u["hash"] == chk(p):
                st.session_state.logged_in = True
                st.session_state.user = {"name": n, "is_admin": u["admin"]}
                st.session_state.is_admin = u["admin"]
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.markdown("---\n**Admin:** Tulika / admin123")
        with st.expander("Channel Logins"):
            for cn, cd in CHANNELS.items():
                st.text(f"{cn}: {cd['passcode']}")

def submission_form():
    cn = st.session_state.user["name"]
    cd = CHANNELS.get(cn)
    st.title(f"{cn} — Weekly Submission")
    if st.button("Logout"):
        for k in ["logged_in", "user", "is_admin"]:
            st.session_state[k] = None if k == "user" else False
        st.rerun()

    wsd = cur_ws(); wl = wkl(wsd)
    st.markdown(f"### {wl} ({wsd.strftime('%d %b %Y')})")
    if cd is None: st.error("Channel not found."); return

    with st.form("cf"):
        data = {}
        for sec, keys in cd["sections"].items():
            with st.expander(f"{sec}", expanded=False):
                cols = st.columns(3)
                for i, mk in enumerate(keys):
                    label = METRIC_LABELS.get(mk, mk.replace("_", " ").title())
                    with cols[i % 3]:
                        data[mk] = st.text_input(label, placeholder="0", key=f"f_{mk}")
        if st.form_submit_button("Submit", type="primary", use_container_width=True):
            clean = {}
            for k, v in data.items():
                raw = v.strip().replace(",", "") if v else ""
                try: clean[k] = float(raw) if raw else 0.0
                except: clean[k] = 0.0
            if write_submission(cn, wl, clean):
                st.success(f"Submitted!"); st.balloons()
            else:
                st.error("Save failed.")
    with st.expander("My Past Submissions"):
        subs = read_all_submissions()
        mw = sorted(set(s["week_label"] for s in subs if s["channel"] == cn), reverse=True)
        for w in mw[:10]: st.text(w)
        if not mw: st.info("No submissions yet.")

def admin_dashboard():
    st.title("Admin Dashboard — SNO Hiring Cost")
    if st.button("Logout"):
        for k in ["logged_in", "user", "is_admin"]:
            st.session_state[k] = None if k == "user" else False
        st.rerun()

    # ── AUTO ORDER FETCH ──
    d1, d2 = get_last_week_dates()
    dw = datetime.strptime(d1, "%Y-%m-%d")
    wl = wkl(dw)
    st.markdown("---")
    st.subheader("Auto-Fetch Orders from Snowflake")
    cf1, cf2, cf3 = st.columns([2, 1, 1])
    cf1.markdown(f"**Last Week:** {d1} → {d2} ({wl})")
    if cf2.button("Fetch Orders", use_container_width=True, type="primary"):
        with st.spinner("Querying Snowflake..."):
            orders = fetch_orders_from_snowflake(d1, d2)
            if orders:
                st.session_state["fo"] = orders
                st.session_state["fow"] = wl
                st.success("Fetched!")
                st.rerun()
            else:
                st.error("Query failed.")
    if cf3.button("Save to Sheet", use_container_width=True):
        if "fo" in st.session_state:
            if write_orders_to_sheet(st.session_state["fow"], st.session_state["fo"]):
                st.success("Saved to Google Sheet!")
                st.rerun()
            else:
                st.error("Save failed.")
        else:
            st.warning("Fetch first!")

    if "fo" in st.session_state:
        fo = st.session_state["fo"]
        cols = st.columns(4)
        for i, (l, v) in enumerate([("SNO Food", fo.get("SNO_Food", 0)), ("SNO IM", fo.get("SNO_IM", 0)),
                                      ("SOC Food", fo.get("SOC_Food", 0)), ("SOC IM", fo.get("SOC_IM", 0))]):
            with cols[i]:
                st.markdown(f'<div class="metric-card"><div class="metric-label">{l}</div><div class="metric-value">{v:,}</div></div>', unsafe_allow_html=True)
        st.markdown(f"**SNO Total:** {fo.get('SNO_Total',0):,} | **SOC Total:** {fo.get('SOC_Total',0):,}")

    st.markdown("---")

    subs = read_all_submissions()
    if not subs:
        st.warning("No data yet.")
        ws = get_sheet()
        if ws: st.success(f"Sheet: `{ws.title}`")
        else: st.error("Google Sheets not connected. Add `gcp_service_account` to secrets.")
        return

    ws = get_sheet()
    if ws: st.success(f"Sheet: `{ws.title}` | {len(subs)} data points")

    t1, t2, t3, t4 = st.tabs(["Submissions", "WoW", "CPFOD", "Channels"])

    ck = ["cost_flatpay", "cost_leakage", "cost_shouldering", "cost_jb", "cost_agency",
          "cost_google_supper", "cost_google_im_app", "cost_insurance", "cost_ob_fee",
          "cost_bgv_fresh", "cost_sms_fresh", "cost_whatsapp_fresh",
          "cost_fr_salary", "cost_fr_tl_salary", "cost_btl", "cost_fr_incentive",
          "cost_influencer_payout", "cost_inf_tl_salary"]
    fk = ["transact_ref", "transact_google", "transact_ssu", "transact_fr",
          "transact_agency", "transact_influencers"]

    def gm(wk):
        return {s["metric"]: sum(s2["value"] for s2 in subs if s2["week_label"] == wk and s2["metric"] == s["metric"])
                for s in subs if s["week_label"] == wk}

    with t1:
        weeks = sorted(set(s["week_label"] for s in subs), reverse=True)
        sw = st.selectbox("Week", weeks)
        st.markdown(f"### {sw}")
        for ch in sorted(set(s["channel"] for s in subs if s["week_label"] == sw)):
            with st.expander(ch):
                rows = [(METRIC_LABELS.get(s["metric"], s["metric"]), s["value"])
                        for s in subs if s["week_label"] == sw and s["channel"] == ch]
                if rows:
                    st.dataframe(pd.DataFrame(rows, columns=["Metric", "Value"]), use_container_width=True, hide_index=True)
        if st.button("Download Excel", use_container_width=True):
            from io import BytesIO
            o = BytesIO()
            aw = sorted(set(s["week_label"] for s in subs))
            with pd.ExcelWriter(o, engine="openpyxl") as wb:
                rd = []
                for mk in sorted(ALL_METRICS_SET):
                    row = {"Metric": METRIC_LABELS.get(mk, mk)}
                    for w in aw:
                        row[w] = sum(s["value"] for s in subs if s["week_label"] == w and s["metric"] == mk)
                    rd.append(row)
                pd.DataFrame(rd).to_excel(wb, sheet_name="Data", index=False)
                sm = []
                for w in aw:
                    d = gm(w)
                    sm.append({"Week": w, "Cost": sum(d.get(k, 0) for k in ck),
                              "FOD": int(sum(d.get(k, 0) for k in fk)),
                              "CPFOD": round(sum(d.get(k, 0) for k in ck) / max(sum(d.get(k, 0) for k in fk), 1))})
                pd.DataFrame(sm).to_excel(wb, sheet_name="Summary", index=False)
            o.seek(0)
            st.download_button("Download", o, "sno_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with t2:
        wa = sorted(set(s["week_label"] for s in subs), reverse=True)
        if len(wa) >= 2:
            tw, pw = wa[0], wa[1]
            d1_, d2_ = gm(tw), gm(pw)
            c1, c2 = sum(d1_.get(k, 0) for k in ck), sum(d2_.get(k, 0) for k in ck)
            f1, f2 = sum(d1_.get(k, 0) for k in fk), sum(d2_.get(k, 0) for k in fk)
            cp1, cp2 = round(c1 / max(f1, 1)), round(c2 / max(f2, 1))
            cards = [("Total Cost", c1, c2), ("Total FOD", f1, f2), ("CPFOD", cp1, cp2), ("Cost WoW", c1 - c2, None)]
            cols = st.columns(4)
            for i, (l, v, pv) in enumerate(cards):
                with cols[i]:
                    dlt = v - pv if pv else 0
                    pct = f" ({dlt/pv*100:+.1f}%)" if pv and pv != 0 else ""
                    clr = "#d32f2f" if dlt > 0 else "#388e3c" if dlt < 0 else "#666"
                    st.markdown(f'<div class="metric-card"><div class="metric-label">{l}</div><div class="metric-value">{v:,.0f}</div><div style="color:{clr}">{dlt:+,.0f}{pct}</div></div>', unsafe_allow_html=True)
            trend = []
            for wk in sorted(set(s["week_label"] for s in subs)):
                d = gm(wk)
                trend.append({"Week": wk, "Cost (L)": round(sum(d.get(k, 0) for k in ck) / 100000, 2),
                             "CPFOD": round(sum(d.get(k, 0) for k in ck) / max(sum(d.get(k, 0) for k in fk), 1))})
            df_t = pd.DataFrame(trend)
            ca, cb = st.columns(2)
            ca.plotly_chart(px.line(df_t, x="Week", y="Cost (L)", markers=True, title="Cost Trend"), use_container_width=True)
            cb.plotly_chart(px.line(df_t, x="Week", y="CPFOD", markers=True, title="CPFOD Trend"), use_container_width=True)
        else:
            st.info("Need 2+ weeks.")

    with t3:
        wa = sorted(set(s["week_label"] for s in subs), reverse=True)
        if len(wa) >= 2:
            ca, cb = st.columns(2)
            w1 = ca.selectbox("Base", wa, index=0, key="cp1")
            rest = [w for w in wa if w != w1]
            w2 = cb.selectbox("Compare", rest, index=0, key="cp2") if rest else None
            if w2:
                da, db = gm(w1), gm(w2)
                analysis = []
                for ch, key in zip(["Referral", "Google", "Agency", "FR", "SSU Direct"],
                                   ["transact_ref", "transact_google", "transact_agency", "transact_fr", "transact_ssu"]):
                    analysis.append({"Channel": ch, f"FOD {w1}": int(da.get(key, 0)),
                                    f"FOD {w2}": int(db.get(key, 0)),
                                    "Delta": int(db.get(key, 0) - da.get(key, 0))})
                st.dataframe(pd.DataFrame(analysis), use_container_width=True, hide_index=True)
        else:
            st.info("Need 2+ weeks.")

    with t4:
        st.subheader("Channel Owners")
        for cn_, cd_ in CHANNELS.items():
            with st.expander(f"{cn_} (pw: {cd_['passcode']})"):
                for sec, keys in cd_["sections"].items():
                    st.text(f"  {sec}: {len(keys)} metrics")

def main():
    if not st.session_state.logged_in:
        login_page()
    elif st.session_state.is_admin:
        admin_dashboard()
    else:
        submission_form()

if __name__ == "__main__":
    main()
