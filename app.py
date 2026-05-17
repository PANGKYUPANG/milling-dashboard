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

# 2. 테이블 렌더링 (가로 폭 60%로 수정 완료)
table_html = f"""
<style>
    .report-table {{ width:60%; border-collapse:collapse; font-family:'Malgun Gothic'; font-size:14px; border: 1px solid #1A3E76; }}
    .report-table th {{ background-color:#1A3E76; color:white; border:1px solid #555; padding:10px; font-weight:bold; text-align:center; }}
    .report-table td {{ border:1px solid #555; padding:10px; }}
    .hdr-unit {{ background-color:#D3D3D3; font-weight:bold; text-align:center; }}
    .hdr-label {{ background-color:#EBEBEB; font-weight:bold; text-align:center; }}
    .num-val {{ text-align:right; }}
    .diff-val {{ background-color:#D3D3D3; text-align:right; font-weight:bold; }}
    .white-bg {{ background-color:#FFFFFF; }}
</style>
<table class="report-table">
    <thead>
        <tr><th rowspan="2">생산단위</th><th rowspan="2">지표</th><th colspan="2">당월(26.{sel_m:02d})</th><th colspan="2">누적(01~{sel_m:02d})</th><th colspan="2">년합계</th></tr>
        <tr><th>가공량</th><th>차이</th><th>가공량</th><th>차이</th><th>예상량</th><th>차이</th></tr>
    </thead>
    <tbody>
        <tr><td class="hdr-unit" rowspan="3">{t_n}</td><td class="hdr-label">'26 계획</td><td class="num-val">{fmt(c_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(c_ac, c_pl))}<br><small>{d2(c_ac, c_pl)}</small></td><td class="num-val">{fmt(m_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(m_ac, m_pl))}<br><small>{d2(m_ac, m_pl)}</small></td><td class="num-val">{fmt(y_pl)}</td><td class="diff-val" rowspan="2">{fmt(d1(y_ac, y_pl))}<br><small>{d2(y_ac, y_pl)}</small></td></tr>
        <tr><td class="hdr-label">'26 실적</td><td class="num-val">{fmt(c_ac)}</td><td class="num-val">{fmt(m_ac)}</td><td class="num-val">{fmt(y_ac)}</td></tr>
        <tr><td class="hdr-label white-bg">'25 실적</td><td class="num-val white-bg">{fmt(c_ly)}</td><td class="diff-val">{fmt(d1(c_ac, c_ly))}</td><td class="num-val white-bg">{fmt(m_ly)}</td><td class="diff-val">{fmt(d1(m_ac, m_ly))}</td><td class="num-val white-bg">{fmt(y_ly)}</td><td class="diff-val">{fmt(d1(y_ac, y_ly))}</td></tr>
    </tbody>
</table>
"""
st.markdown(table_html, unsafe_allow_html=True)

# 3. 월별 계획 vs 실적 비교 그래프
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
    else:
        val = get_data(5, 8, 8, m)
    chart_rows.append({"월": f"{m:02d}월", "계획": val["PL"], "실적": val["AC"], "잔여예상": val["EST_REM"]})

df_chart = pd.DataFrame(chart_rows)
fig1 = go.Figure()
fig1.add_trace(go.Bar(x=df_chart["월"], y=df_chart["계획"], name="계획", marker_color="#D3D3D3", offsetgroup=0, text=[f"{v:,.0f}" if v > 0 else "" for v in df_chart["계획"]], textposition='outside'))
fig1.add_trace(go.Bar(x=df_chart["월"], y=df_chart["실적"], name="실적", marker_color="#1A3E76", offsetgroup=1, text=[f"{v:,.0f}" if v > 0 else "" for v in df_chart["실적"]], textposition='inside'))
fig1.add_trace(go.Bar(x=df_chart["월"], y=df_chart["잔여예상"], name="잔여예상", marker_color="#87CEEB", offsetgroup=1, base=df_chart["실적"], text=[f"+{v:,.0f}" if v > 0 else "" for v in df_chart["잔여예상"]], textposition='outside'))

# 월별 차이값 어노테이션
for i, row in df_chart.iterrows():
    total_perf = row["실적"] + row["잔여예상"]
    if total_perf > 0:
        diff = total_perf - row["계획"]
        fig1.add_annotation(
            x=row["월"], y=max(row["계획"], total_perf), text=f"차이: {fmt(diff)}",
            showarrow=False, yshift=40, font=dict(color="red" if diff < 0 else "blue", size=11, weight="bold")
        )

fig1.update_layout(barmode='group', bargroupgap=0.0, margin=dict(t=50, b=30, l=30, r=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig1, use_container_width=True)

# 4. 누적 계획량 VS 누적 실적량 비교 그래프 (가로형)
st.write("---")
st.write(f"### {target} 01~{sel_m:02d}월 누적 계획 vs 실적 비교")

cum_pl = m_pl
cum_ac = m_ac

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    y=["누적 실적", "누적 계획"], 
    x=[cum_ac, cum_pl],         
    orientation='h',           
    text=[fmt(cum_ac), fmt(cum_pl)],
    textposition='inside',
    marker_color=["#1A3E76", "#D3D3D3"],
    width=0.6
))

fig2.update_layout(
    xaxis_title="가공량",
    margin=dict(t=50, b=50, l=150, r=100),
    height=400
)

# 차이 표시용 어노테이션
cum_diff = cum_ac - cum_pl
fig2.add_annotation(
    x=max(cum_ac, cum_pl), y=0, 
    text=f"  차이: {fmt(cum_diff)} ({d2(cum_ac, cum_pl)})",
    showarrow=False, xanchor="left", font=dict(color="red" if cum_diff < 0 else "blue", size=16, weight="bold")
)

st.plotly_chart(fig2, use_container_width=True)
