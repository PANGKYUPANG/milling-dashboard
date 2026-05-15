import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 및 인증 설정
st.set_page_config(layout="wide")
st.title("월별 예상 가공량 상세 대시보드 v2.0")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("원맥 가공량 예상").worksheet("원맥 가공량")
all_data = sheet.get_all_values()

# 2. 기준 정보 및 사이드바
curr_a4 = int(all_data[3][0]) # 현재 월 (A4 셀)
sel_m = st.sidebar.selectbox("기준 월 선택", range(1, 13), index=curr_a4 - 1)
target = st.sidebar.radio("조회 대상 선택", ["인천공장", "부산공장", "생산본부"])

# 3. 데이터 추출 함수 (지표별 행 번호: 계획=4, 실적=7, 전년=8)
def get_data(p_row, a_row, ly_row, month):
    col = 17 + (month - 1)    # '26년 데이터 열
    ly_col = 33 + (month - 1) # '25년 데이터 열
    
    # 당월 값 추출
    pl = float(all_data[p_row][col].replace(',', '') or 0)
    ly = float(all_data[ly_row][ly_col].replace(',', '') or 0)
    
    if month < curr_a4:
        ac = float(all_data[a_row][col].replace(',', '') or 0)
        est = ac
    elif month == curr_a4:
        # 추정치 계산 (Row 18,19는 인천, 부산 가동일수 관련 데이터 행 인덱스)
        r_idx = 18 if p_row == 4 else 19
        r, s, v = float(all_data[r_idx][17].replace(',','')), float(all_data[r_idx][18].replace(',','')), float(all_data[r_idx][21].replace(',',''))
        est = round((r / s) * v) if s > 0 else 0
        ac = r
    else:
        ac, est = 0, 0
        
    # 누계(Cumulative) 및 년합계(Annual) 계산을 위한 루프
    p_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(month-1)]) if month > 1 else 0
    p_ac = sum([float(all_data[a_row][17+i].replace(',', '') or 0) for i in range(month-1)]) if month > 1 else 0
    p_ly = sum([float(all_data[ly_row][33+i].replace(',', '') or 0) for i in range(month-1)]) if month > 1 else 0
    f_pl = sum([float(all_data[p_row][17+i].replace(',', '') or 0) for i in range(month, 12)])
    
    return {"PL": pl, "AC": ac, "EST": est, "LY": ly, "P_PL": p_pl, "P_AC": p_ac, "P_LY": p_ly, "F_PL": f_pl}

# 4. 선택한 대상에 따른 데이터 집계 (계획: Row 5(idx 4), 실적: Row 8(idx 7), 전년: Row 9(idx 8))
if target == "생산본부":
    ic = get_data(4, 7, 8, sel_m)
    bs = get_data(5, 8, 8, sel_m) # 부산 계획은 Row 6(idx 5)
    d = {k: ic[k] + bs[k] for k in ic}
elif target == "인천공장":
    d = get_data(4, 7, 8, sel_m)
else: # 부산공장
    d = get_data(5, 8, 8, sel_m)

# 테이블용 변수 가공
t_n = target.replace("공장","")
c_pl, c_ac, c_ly = d['PL'], d['EST'], d['LY']
m_pl, m_ac, m_ly = d['P_PL']+c_pl, d['P_AC']+c_ac, d['P_LY']+c_ly
y_pl, y_ac, y_ly = m_pl+d['F_PL'], m_ac+d['F_PL'], m_ly+d['F_PL'] # 년합계는 미래 계획 포함

# 5. 테이블 렌더링 (CSS 최적화 및 우측 정렬)
def fmt(n): return f"{n:,.0f}"
def d1(a, p): return a - p
def d2(a, p): return f"{(a-p)/p*100:.1f}%" if p > 0 else "0.0%"

table_html = f"""
<style>
    .report-table {{ width:100%; border-collapse:collapse; font-family:'Malgun Gothic'; font-size:14px; border: 1px solid #1A3E76; }}
    .report-table th {{ background-color:#1A3E76; color:white; border:1px solid #555; padding:10px; font-weight:bold; }}
    .report-table td {{ border:1px solid #555; padding:10px; }}
    .hdr-unit {{ background-color:#D3D3D3; font-weight:bold; text-align:center; }}
    .hdr-label {{ background-color:#EBEBEB; font-weight:bold; text-align:center; }}
    .num-val {{ text-align:right; }} /* 숫자 우측 정렬 */
    .diff-val {{ background-color:#D3D3D3; text-align:right; font-weight:bold; }}
    .white-bg {{ background-color:#FFFFFF; }} /* '25 실적 배경색 흰색 */
</style>
<table class="report-table">
    <thead>
        <tr><th rowspan="2">생산단위</th><th rowspan="2">지표</th><th colspan="2">당월(26.{sel_m:02d})</th><th colspan="2">누적(01~{sel_m:02d})</th><th colspan="2">년합계</th></tr>
        <tr><th>가공량</th><th>차이</th><th>가공량</th><th>차이</th><th>예상량</th><th>차이</th></tr>
    </thead>
    <tbody>
        <tr><td class="hdr-unit" rowspan="3">{t_n}</td><td class="hdr-label">'26 계획</td><td class="num-val">{fmt(c_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(c_ac, c_pl))}<br><small>{d2(c_ac, c_pl)}</small></td><td class="num-val">{fmt(m_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(m_ac, m_pl))}<br><small>{d2(m_ac, m_pl)}</small></td><td class="num-val">{fmt(y_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(y_ac, y_pl))}<br><small>{d2(y_ac, y_pl)}</small></td></tr>
        <tr><td class="hdr-label">'26 실적</td><td class="num-val">{fmt(c_ac)}</td><td class="num-val">{fmt(m_ac)}</td><td class="num-val">{fmt(y_ac)}</td></tr>
        <tr><td class="hdr-label white-bg">'25 실적</td><td class="num-val white-bg">{fmt(c_ly)}</td><td class="num-val white-bg">{fmt(d1(c_ac, c_ly))}</td><td class="num-val white-bg">{fmt(m_ly)}</td><td class="num-val white-bg">{fmt(d1(m_ac, m_ly))}</td><td class="num-val white-bg">{fmt(y_ly)}</td><td class="num-val white-bg">{fmt(d1(y_ac, y_ly))}</td></tr>
    </tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)

# 6. 그래프 렌더링 (1월~12월 순서 정렬 및 나란히 배치)
st.write("---")
st.write(f"### {target} 월별 계획 vs 실적 비교")

chart_rows = []
for m in range(1, 13):
    if target == "생산본부":
        ic_m = get_data(4, 7, 8, m)
        bs_m = get_data(5, 8, 8, m)
        val = {k: ic_m[k] + bs_m[k] for k in ic_m}
    elif target == "인천공장":
        val = get_data(4, 7, 8, m)
    else: # 부산공장
        val = get_data(5, 8, 8, m)
    
    chart_rows.append({"월": f"{m:02d}월", "계획": val["PL"], "실적": val["EST"] if m <= curr_a4 else 0})

# 데이터프레임 생성 및 정렬 (01월~12월 문자열 기준으로 자동 정렬됨)
df_chart = pd.DataFrame(chart_rows).sort_values("월")

# st.bar_chart를 사용하여 나란히(Side-by-side) 배치 (stack=False)
st.bar_chart(df_chart, x="월", y=["계획", "실적"], color=["#D3D3D3", "#1A3E76"], stack=False)
