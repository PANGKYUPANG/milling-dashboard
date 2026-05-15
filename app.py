import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go

# 1. 페이지 설정 및 데이터 로드
st.set_page_config(layout="wide")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("원맥 가공량 예상").worksheet("원맥 가공량")
all_data = sheet.get_all_values()

# 기준 월 및 대상 선택
curr_a4 = int(all_data[3][0])
sel_m = st.sidebar.selectbox("기준 월 선택", range(1, 13), index=curr_a4 - 1)
target = st.sidebar.radio("조회 대상 선택", ["인천공장", "부산공장", "생산본부"])

# 동적 타이틀
st.title(f"2026년도 {sel_m}월 예상 가공량")

# 안전한 숫자 변환 함수
def safe_float(val):
    if not val: return 0.0
    v = str(val).replace(',', '').strip()
    try:
        return float(v) if v else 0.0
    except ValueError:
        return 0.0

def get_data(p_row, a_row, ly_row, month):
    col = 17 + (month - 1)
    ly_col = 33 + (month - 1)
    
    pl = safe_float(all_data[p_row][col])
    ly = safe_float(all_data[ly_row][ly_col])
    
    r_idx = 18 if p_row == 4 else 19
    ac_to_date = safe_float(all_data[r_idx][17]) 
    rem_est = safe_float(all_data[r_idx][20])   
    total_est = safe_float(all_data[r_idx][22]) 
    
    if month < curr_a4:
        ac = safe_float(all_data[a_row][col])
        est_rem = 0.0
        final_ac = ac
    elif month == curr_a4:
        final_ac = total_est
        ac = ac_to_date
        est_rem = rem_est
    else:
        final_ac, ac, est_rem = 0.0, 0.0, 0.0
        
    p_pl = sum([safe_float(all_data[p_row][17+i]) for i in range(month-1)]) if month > 1 else 0.0
    p_ac = sum([safe_float(all_data[a_row][17+i]) for i in range(month-1)]) if month > 1 else 0.0
    p_ly = sum([safe_float(all_data[ly_row][33+i]) for i in range(month-1)]) if month > 1 else 0.0
    f_pl = sum([safe_float(all_data[p_row][17+i]) for i in range(month, 12)])
    
    return {"PL": pl, "AC": ac, "EST_REM": est_rem, "TOTAL_AC": final_ac, "LY": ly, "P_PL": p_pl, "P_AC": p_ac, "P_LY": p_ly, "F_PL": f_pl}

# 데이터 집계
if target == "생산본부":
    ic = get_data(4, 7, 8, sel_m)
    bs = get_data(5, 8, 8, sel_m)
    d = {k: ic[k] + bs[k] for k in ic}
elif target == "인천공장":
    d = get_data(4, 7, 8, sel_m)
else:
    d = get_data(5, 8, 8, sel_m)

t_n = target.replace("공장","")
c_pl, c_ac, c_ly = d['PL'], d['TOTAL_AC'], d['LY']
m_pl, m_ac, m_ly = d['P_PL']+c_pl, d['P_AC']+c_ac, d['P_LY']+c_ly
y_pl, y_ac, y_ly = m_pl+d['F_PL'], m_ac+d['F_PL'], m_ly+d['F_PL']

def fmt(n): return f"{n:,.0f}"
def d1(a, p): return a - p
def d2(a, p): return f"{(a-p)/p*100:.1f}%" if p > 0 else "0.0%"

# 2. 테이블 렌더링
table_html = f"""
<style>
    .report-table {{ width:100%; border-collapse:collapse; font-family:'Malgun Gothic'; font-size:14px; border: 1px solid #1A3E76; }}
    .report-table th {{ background-color:#1A3E
