import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(layout="wide")
st.title("월별 예상 가공량 상세 대시보드")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("원맥 가공량 예상").worksheet("원맥 가공량")
all_data = sheet.get_all_values()

curr_a4 = int(all_data[3][0])
sel_m = st.sidebar.selectbox("기준 월 선택", range(1, 13), index=curr_a4 - 1)
target = st.sidebar.radio("조회 대상 선택", ["인천공장", "부산공장", "생산본부"])

def get_m(r_idx, p_row, a_row):
    col = 17 + (sel_m - 1)
    ly_col = 33 + (sel_m - 1)
    pl = float(all_data[p_row][col].replace(',', '') or 0)
    ly = float(all_data[a_row][ly_col].replace(',', '') or 0)
    if sel_m < curr_a4:
        ac = float(all_data[a_row][col].replace(',', '') or 0)
        est = ac
    elif sel_m == curr_a4:
        r, s, v = float(all_data[r_idx][17].replace(',','')), float(all_data[r_idx][18].replace(',','')), float(all_data[r_idx][21].replace(',',''))
        est = round((r / s) * v) if s > 0 else 0
        ac = r
    else: ac, est = 0, 0
    p_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(sel_m-1)]) if sel_m > 1 else 0
    p_ac = sum([float(all_data[a_row][17+i].replace(',', '') or 0) for i in range(sel_m-1)]) if sel_m > 1 else 0
    p_ly = sum([float(all_data[a_row][33+i].replace(',', '') or 0) for i in range(sel_m-1)]) if sel_m > 1 else 0
    f_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(sel_m, 12)])
    f_ly = sum([float(all_data[a_row][33+i].replace(',', '') or 0) for i in range(sel_m, 12)])
    return {"PL": pl, "AC": ac, "EST": est, "LY": ly, "P_PL": p_pl, "P_AC": p_ac, "P_LY": p_ly, "F_PL": f_pl, "F_LY": f_ly}

ic, bs = get_m(18, 4, 7), get_m(19, 5, 8)
d = ic if target=="인천공장" else bs if target=="부산공장" else {k: ic[k]+bs[k] for k in ic}
t_n = target.replace("공장","")

c_pl, c_ac, c_ly = d['PL'], d['EST'], d['LY']
m_pl, m_ac, m_ly = d['P_PL']+c_pl, d['P_AC']+c_ac, d['P_LY']+c_ly
y_pl, y_ac, y_ly = m_pl+d['F_PL'], m_ac+d['F_PL'], m_ly+d['F_LY']

def fmt(n): return f"{n:,.0f}"
def d1(a, p): return a - p
def d2(a, p): return f"{(a-p)/p*100:.1f}%" if p > 0 else "0.0%"

h = f"""
<style>
 .t {{ width:100%; border-collapse:collapse; text-align:center; font-family:'Malgun Gothic'; font-size:15px; }}
 .t th, .t td {{ border:1px solid #555; padding:8px; }}
 .n {{ background:#1A3E76; color:white; font-weight:bold; }}
 .g {{ background:#D3D3D3; font-weight:bold; }}
 .l {{ background:#EBEBEB; font-weight:bold; }}
 .r {{ text-align:right; font-weight:bold; }}
</style>
<table class="t">
 <tr class="n"><th rowspan="2">생산단위</th><th rowspan="2">지표</th><th colspan="2">당월(26.{sel_m:02d})</th><th colspan="2">누적(01~{sel_m:02d})</th><th colspan="2">년합계</th></tr>
 <tr class="n"><th>가공량</th><th>차이</th><th>가공량</th><th>차이</th><th>예상량</th><th>차이</th></tr>
 <tr><td class="g" rowspan="3">{t_n}</td><td class="l">'26 계획</td><td class="r">{fmt(c_pl)}</td><td class="g" rowspan="2" class="r">{fmt(d1(c_ac, c_pl))}<br><small>{d2(c_ac, c_pl)}</small></td><td class="r">{fmt(m_pl)}</td><td class="g" rowspan="2" class="r">{fmt(d1(m_ac, m_pl))}<br><small>{d2(m_ac, m_pl)}</small></td><td class="r">{fmt(y_pl)}</td><td class="g" rowspan="2" class="r">{fmt(d1(y_ac, y_pl))}<br><small>{d2(y_ac, y_pl)}</small></td></tr>
 <tr><td class="l">'26 실적</td><td class="r">{fmt(c_ac)}</td><td class="r">{fmt(m_ac)}</td><td class="r">{fmt(y_ac)}</td></tr>
 <tr><td class="g">'25 실적</td><td class="g r">{fmt(c_ly)}</td><td class="g r">{fmt(d1(c_ac, c_ly))}</td><td class="g r">{fmt(m_ly)}</td><td class="g r">{fmt(d1(m_ac, m_ly))}</td><td class="g r">{fmt(y_ly)}</td><td class="g r">{fmt(d1(y_ac, y_ly))}</td></tr>
</table>
"""
st.markdown(h, unsafe_allow_html=True)
st.bar_chart(pd.DataFrame({"구분":["당월계획","당월실적","누계실적","연간추정"], "가공량":[c_pl, c_ac, m_ac, y_ac]}).set_index("구분"))
