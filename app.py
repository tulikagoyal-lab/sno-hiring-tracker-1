import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

# ── Simple Auth ──
USERS = {
    "Tulika": {"hash": hashlib.sha256("admin123".encode()).hexdigest()[:12], "admin": True},
    "SOC Channel": {"hash": hashlib.sha256("soc123".encode()).hexdigest()[:12], "admin": False},
    "SNO Channel": {"hash": hashlib.sha256("sno123".encode()).hexdigest()[:12], "admin": False},
    "Agency Channel": {"hash": hashlib.sha256("agency123".encode()).hexdigest()[:12], "admin": False},
    "Google Channel": {"hash": hashlib.sha256("google123".encode()).hexdigest()[:12], "admin": False},
    "Referral Channel": {"hash": hashlib.sha256("ref123".encode()).hexdigest()[:12], "admin": False},
    "FR Channel": {"hash": hashlib.sha256("fr123".encode()).hexdigest()[:12], "admin": False},
}

def chk(raw): return hashlib.sha256(raw.encode()).hexdigest()[:12]
def wk(dt): return f"WK{dt.isocalendar()[1]}-{dt.year}"
def cur_mon(): return datetime.now() - timedelta(days=datetime.now().weekday())

# ── Metrics ──
METRICS = [
    ("Orders", "SOC Order Count", "orders_soc"),
    ("Orders", "SNO Order Count", "orders_sno"),
    ("SNO Hiring", "Spillover (>28 days)", "sno_spillover_28"),
    ("SNO Hiring", "CPFOD SW+Spillover - Referral", "sno_cpfod_ref"),
    ("SNO Hiring", "CPFOD SW+Spillover - RB Override", "sno_cpfod_rb_override"),
    ("SNO Hiring", "CPFOD SW+Spillover - Agency", "sno_cpfod_agency"),
    ("SNO Hiring", "Rejoiner/Activation Count", "sno_rejoiner"),
    ("SNO Cost", "Flatpay (w/o Leakage)", "cost_flatpay"),
    ("SNO Cost", "Leakage", "cost_leakage"),
    ("SNO Cost", "Shouldering", "cost_shouldering"),
    ("SNO Cost", "Dormant RB", "cost_dormant_rb"),
    ("SNO Cost", "Impersonation", "cost_impersonation"),
    ("SNO Cost", "JB Cost", "cost_jb"),
    ("SNO Cost", "RB Cost - SW CPFOD", "cost_rb_cpfod"),
    ("SNO Cost", "RB Cost - SW FOD", "cost_rb_fod"),
    ("SNO Cost", "Ref Override - SW CPFOD", "cost_ref_override_cpfod"),
    ("SNO Cost", "Ref Override - SW FOD", "cost_ref_override_fod"),
    ("SNO Cost", "Spillover <=28 Days Cost", "cost_spillover_28"),
    ("SNO Cost", "Agency Cost", "cost_agency"),
    ("SNO Cost", "Google Supper App Cost", "cost_google_supper"),
    ("SNO Cost", "Google Extra Cost", "cost_google_extra"),
    ("SNO Cost", "Google Supper App Fresh FOD", "cost_google_fresh_fod"),
    ("SNO Cost", "Google IM App Cost", "cost_google_im_app"),
    ("SNO Cost", "Google SNO IM 1st Party", "cost_google_im_1st"),
    ("SNO Cost", "Google Extra 1st Party", "cost_google_extra_1st"),
    ("SNO Cost", "Upfront Fee Collection", "cost_upfront_fee"),
    ("SNO Cost", "Insurance", "cost_insurance"),
    ("SNO Cost", "OB Fee Collection", "cost_ob_fee"),
    ("SNO Cost", "Apsflyer Portal", "cost_apsflyer"),
    ("SNO Cost", "Pivot Roots", "cost_pivot_roots"),
    ("SNO Cost", "Autodialer Cost", "cost_autodialer"),
    ("SNO Cost", "BGV Fresh - Betterplace+Authbridge", "cost_bgv_fresh"),
    ("SNO Cost", "BGV Fresh - Address Check", "cost_bgv_address"),
    ("SNO Cost", "BGV Rejoiner", "cost_bgv_rejoiner"),
    ("SNO Cost", "SMS Cost Fresh", "cost_sms_fresh"),
    ("SNO Cost", "SMS Cost Rejoiner", "cost_sms_rejoiner"),
    ("SNO Cost", "Whatsapp Comms Fresh", "cost_whatsapp_fresh"),
    ("SNO Cost", "Whatsapp Comms Rejoiner", "cost_whatsapp_rejoiner"),
    ("SNO Cost", "OBE/RTC Incentive", "cost_obe_rtc"),
    ("SNO Cost", "FR Salary", "cost_fr_salary"),
    ("SNO Cost", "FR Count", "cost_fr_count"),
    ("SNO Cost", "FR TL Salary", "cost_fr_tl_salary"),
    ("SNO Cost", "FR TL Count", "cost_fr_tl_count"),
    ("SNO Cost", "BTL Spend", "cost_btl"),
    ("SNO Cost", "FR+FR TL Incentive", "cost_fr_incentive"),
    ("SNO Cost", "Influencer Payout", "cost_influencer_payout"),
    ("SNO Cost", "Influencer TL Salary", "cost_inf_tl_salary"),
    ("SNO Cost", "Influencer TL Count", "cost_inf_tl_count"),
    ("SNO Cost", "Spillover >28 Days", "cost_spillover_over_28"),
    ("SNO Cost", "Other Cost", "cost_other_mult"),
    ("SNO Same Week Transacting", "Referral", "transact_ref"),
    ("SNO Same Week Transacting", "Google", "transact_google"),
    ("SNO Same Week Transacting", "Affiliate", "transact_affiliate"),
    ("SNO Same Week Transacting", "SSU Direct", "transact_ssu"),
    ("SNO Same Week Transacting", "FR", "transact_fr"),
    ("SNO Same Week Transacting", "Agency", "transact_agency"),
    ("SNO Same Week Transacting", "Influencers", "transact_influencers"),
    ("SNO Spill Over FOD", "Referral", "spill_fod_ref"),
    ("SNO Spill Over FOD", "Google", "spill_fod_google"),
    ("SNO Spill Over FOD", "Affiliate", "spill_fod_affiliate"),
    ("SNO Spill Over FOD", "SSU Direct", "spill_fod_ssu"),
    ("SNO Spill Over FOD", "FR", "spill_fod_fr"),
    ("SNO Spill Over FOD", "Agency", "spill_fod_agency"),
    ("SNO Spill Over FOD", "Influencers", "spill_fod_influencers"),
    ("SNO Onboarding", "Referral", "onboard_ref"),
    ("SNO Onboarding", "Google", "onboard_google"),
    ("SNO Onboarding", "Affiliate", "onboard_affiliate"),
    ("SNO Onboarding", "SSU Direct", "onboard_ssu"),
    ("SNO Onboarding", "FR", "onboard_fr"),
    ("SNO Onboarding", "Agency", "onboard_agency"),
    ("SNO Onboarding", "Influencers", "onboard_influencers"),
    ("SOC Hiring", "Fresh Onboarding", "soc_fresh_onboard"),
    ("SOC Hiring", "SOC Rejoiner Count", "soc_rejoiner"),
    ("SOC Hiring", "Spillover (<28 days)", "soc_spillover_28"),
    ("SOC Hiring", "Spillover (>28 days)", "soc_spillover_over_28"),
    ("SOC CPH", "Referral CPOD", "soc_cpod_ref"),
    ("SOC Cost", "SOC Rejoiner Cost", "soc_rejoiner_cost"),
    ("SOC Cost", "JB Cost", "soc_jb_cost"),
    ("SOC Cost", "RB Cost - SW CPFOD", "soc_rb_cpfod"),
    ("SOC Cost", "Spillover <=28 Days", "soc_cost_spillover_28"),
    ("SOC Cost", "Spillover >28 Days", "soc_cost_spillover_over_28"),
    ("SOC Cost", "JB Adjustment", "soc_jb_adjust"),
    ("SOC Cost", "RB Adjustment", "soc_rb_adjust"),
    ("SOC Cost", "Agency Cost", "soc_agency_cost"),
    ("SOC Cost", "Google IM App Weekly", "soc_google_im"),
    ("SOC Cost", "Google Supper App", "soc_google_supper"),
    ("SOC Cost", "Google IM SA FOD", "soc_google_im_sa_fod"),
    ("SOC Cost", "Google SF SA FOD", "soc_google_sf_sa_fod"),
    ("SOC Cost", "Extra SOC IM App", "soc_extra_im"),
    ("SOC Cost", "Upfront Fee", "soc_upfront_fee"),
    ("SOC Cost", "Insurance", "soc_insurance"),
    ("SOC Cost", "OB Fee", "soc_ob_fee"),
    ("SOC Cost", "SOC OB Fees", "soc_ob_fees_actual"),
    ("SOC Cost", "BGV Cost", "soc_bgv"),
    ("SOC Cost", "SMS Fresh", "soc_sms_fresh"),
    ("SOC Cost", "SMS Rejoiner", "soc_sms_rejoiner"),
    ("SOC Cost", "Whatsapp Fresh", "soc_whatsapp_fresh"),
    ("SOC Cost", "Whatsapp Rejoiner", "soc_whatsapp_rejoiner"),
    ("SOC Cost", "BTL Spend", "soc_btl"),
    ("SOC Cost", "TC Incentive", "soc_tc_incentive"),
    ("SOC Cost", "IM FR Count", "soc_fr_count"),
    ("SOC Cost", "IM TL Count", "soc_tl_count"),
    ("SOC Cost", "FR Initiatives", "soc_fr_initiatives"),
    ("SOC Cost", "FR Cost Extra", "soc_fr_extra"),
    ("SOC Same Week Transacting", "Referral", "soc_transact_ref"),
    ("SOC Same Week Transacting", "Google", "soc_transact_google"),
    ("SOC Same Week Transacting", "Affiliate", "soc_transact_affiliate"),
    ("SOC Same Week Transacting", "SSU Direct", "soc_transact_ssu"),
    ("SOC Same Week Transacting", "FR", "soc_transact_fr"),
    ("SOC Same Week Transacting", "Agency", "soc_transact_agency"),
    ("SOC Same Week Transacting", "Goldmine", "soc_transact_goldmine"),
    ("SOC Same Week Transacting", "Influencers", "soc_transact_influencers"),
    ("SOC Spill Over FOD", "Referral", "soc_spill_fod_ref"),
    ("SOC Spill Over FOD", "Google", "soc_spill_fod_google"),
    ("SOC Spill Over FOD", "Affiliate", "soc_spill_fod_affiliate"),
    ("SOC Spill Over FOD", "SSU Direct", "soc_spill_fod_ssu"),
    ("SOC Spill Over FOD", "FR", "soc_spill_fod_fr"),
    ("SOC Spill Over FOD", "Agency", "soc_spill_fod_agency"),
    ("SOC Spill Over FOD", "Influencers", "soc_spill_fod_influencers"),
]

# ── Cache ──
@st.cache_resource
def store():
    return {"subs": [], "targets": []}

# ── UI Config ──
st.set_page_config(page_title="SNO Hiring Cost Tracker", layout="wide")
st.markdown("""
<style>
.metric-card{background:#f0f2f6;border-radius:10px;padding:20px;text-align:center}
.metric-value{font-size:28px;font-weight:bold;color:#1f77b4}
.metric-label{font-size:14px;color:#666}
</style>""", unsafe_allow_html=True)

for k in ["logged_in", "user", "is_admin"]:
    if k not in st.session_state:
        st.session_state[k] = None if k == "user" else False

# ── Login ──
def login_page():
    st.title("SNO Hiring Cost Tracker")
    _, c, _ = st.columns([1,2,1])
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
        st.markdown("---")
        st.markdown("- **Admin:** Tulika / admin123\n- **Channels:** SOC/soc123, SNO/sno123, Agency/agency123, etc.")

# ── Submission ──
def submission_form():
    S = store()
    st.title("Weekly Data Submission")
    st.markdown(f"**User:** {st.session_state.user['name']}")
    if st.button("Logout"):
        for k in ["logged_in", "user", "is_admin"]: st.session_state[k] = None if k == "user" else False
        st.rerun()
    ws = cur_mon(); wl = wk(ws)
    st.markdown(f"### {wl} ({ws.strftime('%d %b %Y')})")
    sections = {}
    for s, l, k in METRICS: sections.setdefault(s, []).append((l, k))
    with st.form("f"):
        data = {}
        for sec, items in sections.items():
            with st.expander(sec, expanded=False):
                cs = st.columns(3)
                for i, (l, k) in enumerate(items):
                    with cs[i%3]:
                        data[k] = st.text_input(l, placeholder="0", key=f"x_{k}")
        if st.form_submit_button("Submit", type="primary", use_container_width=True):
            ch = st.session_state.user["name"]
            S["subs"] = [s for s in S["subs"] if not (s["channel"]==ch and s["week_label"]==wl)]
            for k, v in data.items():
                try: val = float(v.strip().replace(",","")) if v and v.strip() else 0.0
                except: val = 0.0
                S["subs"].append({"channel":ch,"week_label":wl,"metric":k,"value":val,"at":datetime.now().isoformat()})
            st.success(f"Submitted for {wl}!"); st.balloons()
    with st.expander("My Past Submissions"):
        ws2 = sorted(set(s["week_label"] for s in S["subs"] if s["channel"]==st.session_state.user["name"]), reverse=True)
        if ws2:
            for w in ws2[:10]: st.text(w)
        else: st.info("No submissions yet")

# ── Admin ──
def admin_dashboard():
    S = store(); subs = S["subs"]
    st.title("Admin Dashboard — SNO Hiring Cost")
    if st.button("Logout"):
        for k in ["logged_in", "user", "is_admin"]: st.session_state[k] = None if k == "user" else False
        st.rerun()
    if not subs: st.warning("No data yet. Channel owners need to submit first."); return

    t1, t2, t3, t4 = st.tabs(["All Submissions", "WoW", "CPFOD", "Users"])

    with t1:
        st.subheader("Weekly Submissions")
        weeks = sorted(set(s["week_label"] for s in subs), reverse=True)
        sw = st.selectbox("Week", weeks, key="t1w")
        chd = {}
        for s in subs:
            if s["week_label"]==sw:
                chd.setdefault(s["channel"],{})[s["metric"]]=s["value"]
        for ch, d in chd.items():
            with st.expander(ch):
                rows = [(k.replace("_"," ").title(),v) for k,v in d.items() if v!=0]
                if rows: st.dataframe(pd.DataFrame(rows,columns=["Metric","Value"]), use_container_width=True, hide_index=True)
        if st.button("Download Excel", use_container_width=True):
            from io import BytesIO; o=BytesIO()
            records=[];we2=sorted(set(s["week_label"] for s in subs))
            for mk in [m[2] for m in METRICS]:
                ml=next((m[1] for m in METRICS if m[2]==mk),mk);row={"Metric":ml}
                for w in we2: row[w]=sum(s["value"] for s in subs if s["week_label"]==w and s["metric"]==mk)
                records.append(row)
            with pd.ExcelWriter(o,engine="openpyxl") as wb:
                pd.DataFrame(records).to_excel(wb,sheet_name="Data",index=False)
                ck=["cost_flatpay","cost_leakage","cost_shouldering","cost_jb","cost_agency","cost_google_supper","cost_google_im_app","cost_insurance","cost_ob_fee"]
                fk=["transact_ref","transact_google","transact_ssu","transact_fr","transact_agency","transact_influencers"]
                smm=[]
                for w in we2:
                    d={}
                    for s in subs:
                        if s["week_label"]==w:d[s["metric"]]=d.get(s["metric"],0)+(s["value"]or 0)
                    smm.append({"Week":w,"Cost":sum(d.get(k,0) for k in ck),"FOD":int(sum(d.get(k,0) for k in fk)),"CPFOD":round(sum(d.get(k,0) for k in ck)/max(sum(d.get(k,0) for k in fk),1))})
                pd.DataFrame(smm).to_excel(wb,sheet_name="Summary",index=False)
            o.seek(0);st.download_button("Download",o,"sno_data.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with t2:
        st.subheader("WoW Summary")
        wa = sorted(set(s["week_label"] for s in subs), reverse=True)
        if len(wa)>=2:
            tw,pw=wa[0],wa[1]
            def gm(wk):
                m={}
                for s in subs:
                    if s["week_label"]==wk:m[s["metric"]]=m.get(s["metric"],0)+(s["value"]or 0)
                return m
            d1,d2=gm(tw),gm(pw)
            ck=["cost_flatpay","cost_leakage","cost_shouldering","cost_jb","cost_agency","cost_google_supper","cost_google_im_app","cost_insurance","cost_ob_fee","cost_bgv_fresh","cost_sms_fresh","cost_whatsapp_fresh","cost_fr_salary","cost_fr_tl_salary","cost_btl","cost_fr_incentive","cost_influencer_payout","cost_inf_tl_salary"]
            fk=["transact_ref","transact_google","transact_ssu","transact_fr","transact_agency","transact_influencers"]
            c1,c2=sum(d1.get(k,0) for k in ck),sum(d2.get(k,0) for k in ck)
            f1,f2=sum(d1.get(k,0) for k in fk),sum(d2.get(k,0) for k in fk)
            cp1,cp2=round(c1/max(f1,1)),round(c2/max(f2,1))
            cols=st.columns(4)
            for i,(l,v1,v2) in enumerate([("Total Cost",c1,c2),("Total FOD",f1,f2),("CPFOD",cp1,cp2),("Cost Change",c1-c2,None)]):
                with cols[i]:
                    d=v1-v2 if v2 else 0
                    p=f" ({(d/v2*100):+.1f}%)" if v2 else ""
                    cl="#d32f2f" if d>0 else "#388e3c" if d<0 else "#666"
                    st.markdown(f'<div class="metric-card"><div class="metric-label">{l}</div><div class="metric-value">{v1:,.0f}</div><div style="color:{cl}">{d:+,.0f}{p}</div></div>',unsafe_allow_html=True)
            trend=[]
            for wk in sorted(set(s["week_label"] for s in subs)):
                d=gm(wk)
                trend.append({"Week":wk,"Cost (L)":round(sum(d.get(k,0) for k in ck)/100000,2),"CPFOD":round(sum(d.get(k,0) for k in ck)/max(sum(d.get(k,0) for k in fk),1))})
            df_t=pd.DataFrame(trend)
            ca,cb=st.columns(2)
            ca.plotly_chart(px.line(df_t,x="Week",y="Cost (L)",markers=True,title="Cost Trend"),use_container_width=True)
            cb.plotly_chart(px.line(df_t,x="Week",y="CPFOD",markers=True,title="CPFOD Trend"),use_container_width=True)
        else: st.info("Need 2+ weeks")

    with t3:
        st.subheader("CPFOD Analysis")
        wa=sorted(set(s["week_label"] for s in subs),reverse=True)
        if len(wa)>=2:
            c1,c2=st.columns(2)
            w1=c1.selectbox("Base",wa,index=0,key="co1")
            rest=[w for w in wa if w!=w1]
            w2=c2.selectbox("Compare",rest,index=0,key="co2") if rest else None
            if w2:
                d1,d2=gm(w1),gm(w2)
                chs=["Referral","Google","Agency","FR","SSU Direct"]
                ks=["transact_ref","transact_google","transact_agency","transact_fr","transact_ssu"]
                analysis=[]
                for ch,k in zip(chs,ks):
                    f1v,f2v=d1.get(k,0),d2.get(k,0)
                    analysis.append({"Channel":ch,f"FOD {w1}":int(f1v),f"FOD {w2}":int(f2v),"Delta":int(f2v-f1v)})
                st.dataframe(pd.DataFrame(analysis),use_container_width=True,hide_index=True)
        else: st.info("Need 2+ weeks")

    with t4:
        st.subheader("Users")
        for n,i in USERS.items():
            st.text(f"- {n} ({'Admin' if i['admin'] else 'Channel'})")
        st.info("To modify users, update the app code or contact developer.")

# ── Main ──
def main():
    if not st.session_state.logged_in: login_page()
    elif st.session_state.is_admin: admin_dashboard()
    else: submission_form()

if __name__=="__main__": main()
