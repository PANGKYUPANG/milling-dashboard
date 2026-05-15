import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(layout="wide")
st.title("월별 예상 가공량 상세 대시보드 v2.0")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("원맥 가공량 예상").worksheet("원맥 가공량")
all_data = sheet.get_all_values()

curr_a4 = int(all_data[3][0])
sel_m = st.sidebar.selectbox("기준 월 선택", range(1, 13), index=curr_a4 - 1)
target = st.sidebar.radio("조회 대상 선택", ["인천공장", "부산공장", "생산본부"])

def get_m(r_idx, p_row, a_row, m_val):
    col = 17 + (m_val - 1)
    ly_col = 33 + (m_val - 1)
    pl = float(all_data[p_row][col].replace(',', '') or 0)
    ly = float(all_data[a_row][ly_col].replace(',', '') or 0)
    if m_val < curr_a4:
        ac = float(all_data[a_row][col].replace(',', '') or 0)
        est = ac
    elif m_val == curr_a4:
        r, s, v = float(all_data[r_idx][17].replace(',','')), float(all_data[r_idx][18].replace(',','')), float(all_data[r_idx][21].replace(',',''))
        est = round((r / s) * v) if s > 0 else 0
        ac = r
    else: ac, est = 0, 0
    p_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(m_val-1)]) if m_val > 1 else 0
    p_ac = sum([float(all_data[a_row][17+i].replace(',', '') or 0) for i in range(m_val-1)]) if m_val > 1 else 0
    p_ly = sum([float(all_data[a_row][33+i].replace(',', '') or 0) for i in range(m_val-1)]) if m_val > 1 else 0
    f_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(m_val, 12)])
    f_ly = sum([float(all_data[a_row][33+i].replace(',', '') or 0) for i in range(m_val, 12)])
    return {"PL": pl, "AC": ac, "EST": est, "LY": ly, "P_PL": p_pl, "P_AC": p_ac, "P_LY": p_ly, "F_PL": f_pl, "F_LY": f_ly}

# Logic for Summary Table
ic, bs = get_m(18, 4, 7, sel_m), get_m(19, 5, 8, sel_m)
d = ic if target=="인천공장" else bs if target=="부산공장" else {k: ic[k]+bs[k] for k in ic}
t_n = target.replace("공장","")

c_pl, c_ac, c_ly = d['PL'], d['EST'], d['LY']
m_pl, m_ac, m_ly = d['P_PL']+c_pl, d['P_AC']+c_ac, d['P_LY']+c_ly
y_pl, y_ac, y_ly = m_pl+d['F_PL'], m_ac+d['F_PL'], m_ly+d['F_LY']

def fmt(n): return f"{n:,.0f}"
def d1(a, p): return a - p
def d2(a, p): return f"{(a-p)/p*100:.1f}%" if p > 0 else "0.0%"

# Table CSS & HTML
h = f"""

생산단위	지표	당월(26.{sel_m:02d})	누적(01~{sel_m:02d})	년합계
가공량	차이	가공량	차이	예상량	차이
{t_n}	'26 계획	{fmt(c_pl)}	{fmt(d1(c_ac, c_pl))}
{d2(c_ac, c_pl)}	{fmt(m_pl)}	{fmt(d1(m_ac, m_pl))}
{d2(m_ac, m_pl)}	{fmt(y_pl)}	{fmt(d1(y_ac, y_pl))}
{d2(y_ac, y_pl)}
'26 실적	{fmt(c_ac)}	{fmt(m_ac)}	{fmt(y_ac)}
'25 실적	{fmt(c_ly)}	{fmt(d1(c_ac, c_ly))}	{fmt(m_ly)}	{fmt(d1(m_ac, m_ly))}	{fmt(y_ly)}	{fmt(d1(y_ac, y_ly))}

"""
st.markdown(h, unsafe_allow_html=True)

# Graph Logic for all 12 months
chart_rows = []
for m in range(1, 13):
    ic_m, bs_m = get_m(18, 4, 7, m), get_m(19, 5, 8, m)
    if target == "생산본부": val = {k: ic_m[k] + bs_m[k] for k in ic_m}
    elif target == "인천공장": val = ic_m
    else: val = bs_m
    chart_rows.append({"월": f"{m}월", "계획": val["PL"], "실적": val["EST"] if m <= curr_a4 else 0})

df_chart = pd.DataFrame(chart_rows).set_index("월")
st.write("### 월별 계획 vs 실적 비교")
st.bar_chart(df_chart, color=["#D3D3D3", "#1A3E76"])
