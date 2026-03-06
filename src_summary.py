import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import openai
import os
import json
from datetime import datetime
import glob
import requests  # 추가

def to_num(v):
    try: return float(str(v).replace(',', ''))
    except: return 0

def safe_read_csv(file_path):
    """CSV 파일을 여러 인코딩으로 시도하여 읽기"""
    for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1']:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            return df
        except:
            continue
    return None

def get_rev(df_sum, df_items, d_str, mode='gross', game_key='m2'):
    if df_sum is None or df_sum.empty: return 0
    
    BLESSING_PRICE = 55000
    
    if mode == 'gross':
        row = df_sum[df_sum['일자'] == d_str]
        base = sum(row['매출대상소진금액_금액'].apply(to_num)) - sum(row['매출대상소진금액_취소금액'].apply(to_num))
        
        blessing = 0
        if game_key == 'm2' and not row.empty and '미르의축복_수량' in row.columns:
            blessing = sum(row['미르의축복_수량'].apply(to_num)) * BLESSING_PRICE
        
        return base + blessing
    
    else:  # 'cum' 모드
        if df_items is None or df_items.empty:
            return 0
        
        year = d_str[:4]
        month = int(d_str[4:])
        
        # 아이템 누적
        mask = (df_items['일자'] >= year + "01") & (df_items['일자'] <= d_str)
        items_cum = df_items[mask]['합계_순매출'].apply(to_num).sum()
        
        # 미르의축복 누적 추가 (m2만)
        blessing_cum = 0
        if game_key == 'm2' and df_sum is not None:
            for i in range(1, month + 1):
                row = df_sum[df_sum['일자'] == f"{year}{i:02d}"]
                if not row.empty and '미르의축복_수량' in row.columns:
                    blessing_cum += sum(row['미르의축복_수량'].apply(to_num)) * BLESSING_PRICE
        
        return items_cum + blessing_cum


def get_metrics_row(df, d_str):
    if df is None or df.empty: return None
    row = df[df['일자'] == d_str]
    return row.iloc[0] if not row.empty else None

def get_analysis_from_csv(df, d_str):
    if df is None or df.empty: return "데이터 없음"
    row = df[df['일자'] == d_str]
    if not row.empty and '비고' in df.columns:
        val = row.iloc[0]['비고']
        return str(val) if pd.notna(val) and str(val).strip() != "" else "해당 월의 비고 내용이 없습니다."
    return "데이터 없음"

def make_rev_chart(df, df_sum, color, c_year, c_d, hex_to_rgba, game_key='m2'):
    x_m = [f"{i:02d}월" for i in range(1, 13)]
    c_idx = int(c_d[4:])
    
    BLESSING_PRICE = 55000
    
    # 누적 매출 계산 (items + blessing)
    cum_c_v = []
    cum_total = 0
    for i in range(1, c_idx + 1):
        monthly = to_num(df[df['일자'] == f"{c_year}{i:02d}"]["합계_순매출"].sum()) if not df[df['일자'] == f"{c_year}{i:02d}"].empty else 0
        
        # 미르의축복 추가 (m2만)
        blessing = 0
        if game_key == 'm2' and df_sum is not None:
            row = df_sum[(df_sum['일자'] == f"{c_year}{i:02d}") & (df_sum['일자'].str.upper() != 'TOTAL')]
            if not row.empty and '미르의축복_수량' in row.columns:
                blessing = to_num(row['미르의축복_수량'].sum()) * BLESSING_PRICE
        
        cum_total += monthly + blessing
        cum_c_v.append(cum_total)
    
    cum_l_v = []
    cum_total_l = 0
    for i in range(1, 13):
        monthly = to_num(df[df['일자'] == f"{c_year-1}{i:02d}"]["합계_순매출"].sum()) if not df[df['일자'] == f"{c_year-1}{i:02d}"].empty else 0
        
        blessing = 0
        if game_key == 'm2' and df_sum is not None:
            row = df_sum[(df_sum['일자'] == f"{c_year-1}{i:02d}") & (df_sum['일자'].str.upper() != 'TOTAL')]
            if not row.empty and '미르의축복_수량' in row.columns:
                blessing = to_num(row['미르의축복_수량'].sum()) * BLESSING_PRICE
        
        cum_total_l += monthly + blessing
        cum_l_v.append(cum_total_l)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_m, y=cum_l_v, name=f'{c_year-1}', line=dict(color='#94a3b8', width=2, dash='dot'), fill='tozeroy', fillcolor='rgba(148, 163, 184, 0.1)'))
    fig.add_trace(go.Scatter(x=x_m[:c_idx], y=cum_c_v, name=f'{c_year}', line=dict(color=color, width=5), mode='lines+markers+text', text=[f"{v/1e8:.1f}억" for v in cum_c_v], textposition="top center", fill='tozeroy', fillcolor=hex_to_rgba(color, 0.15)))
    
    fig.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#f8fafc',
        height=300,
        margin=dict(l=40, r=20, t=10, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color="black")),
        xaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickfont=dict(color='black'), side='bottom'),
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickformat=',.0f', tickfont=dict(color='black'), rangemode='tozero')
    )
    return fig

def make_combined_metrics_chart(df, main_color, c_year, hex_to_rgba):
    if df is None or df.empty: 
        return go.Figure()
    x_m = [f"{i:02d}월" for i in range(1, 13)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    mau_v = [to_num(df[df['일자']==f"{c_year}{i:02d}"]["MAU"].values[0]) if not df[df['일자']==f"{c_year}{i:02d}"].empty else 0 for i in range(1, 13)]
    nru_v = [to_num(df[df['일자']==f"{c_year}{i:02d}"]["NRU"].values[0]) if not df[df['일자']==f"{c_year}{i:02d}"].empty else 0 for i in range(1, 13)]
    bu_v = [to_num(df[df['일자']==f"{c_year}{i:02d}"]["BU"].values[0]) if not df[df['일자']==f"{c_year}{i:02d}"].empty else 0 for i in range(1, 13)]
    arppu_v = [to_num(df[df['일자']==f"{c_year}{i:02d}"]["ARPPU"].values[0]) if not df[df['일자']==f"{c_year}{i:02d}"].empty else 0 for i in range(1, 13)]
    
    fig.add_trace(go.Scatter(x=x_m, y=mau_v, name="MAU", line=dict(color=main_color, width=4), mode='lines+markers', hovertemplate='<b>MAU</b><br>%{y:,.0f}<extra></extra>'), secondary_y=False)
    fig.add_trace(go.Bar(x=x_m, y=nru_v, name="NRU", marker_color=hex_to_rgba(main_color, 0.4), hovertemplate='<b>NRU</b><br>%{y:,.0f}<extra></extra>'), secondary_y=False)
    fig.add_trace(go.Bar(x=x_m, y=bu_v, name="BU", marker_color=hex_to_rgba(main_color, 0.7), hovertemplate='<b>BU</b><br>%{y:,.0f}<extra></extra>'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x_m, y=arppu_v, name="ARPPU (₩)", line=dict(color="#f59e0b", width=3, dash='dot'), mode='lines+markers', hovertemplate='<b>ARPPU (₩)</b><br>%{y:,.0f}<extra></extra>'), secondary_y=True)
    
    fig.update_layout(
        height=400, 
        paper_bgcolor='#ffffff', 
        plot_bgcolor='#f8fafc', 
        margin=dict(l=60, r=60, t=20, b=20), 
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="black")), 
        xaxis=dict(tickfont=dict(color='black'), gridcolor='#e2e8f0', gridwidth=0.5, showgrid=True, side='bottom'), 
        yaxis=dict(title=dict(text="유저 수 (명)", font=dict(color='#000000', size=12)), tickfont=dict(color='black'), gridcolor='#e2e8f0', gridwidth=0.5, tickformat=',.0f', showgrid=True, rangemode='tozero'), 
        yaxis2=dict(title=dict(text="ARPPU (원)", font=dict(color='#f59e0b', size=12)), tickfont=dict(color='#f59e0b'), gridwidth=0, showgrid=False, tickformat=',.0f', rangemode='tozero'), 
        hovermode='x unified'
    )
    return fig

# ============ AI 분석 탭 (완전히 새로 작성) ============
def get_data(items_df, summary_df, metrics_df, d_str):
    """월별 데이터 추출"""
    res = {'rev': 0, 'nru': 0, 'mau': 0, 'bu': 0, 'arppu': 0}
    
    if items_df is not None and not items_df.empty:
        filtered = items_df[items_df['일자'].astype(str).str.strip().str[:6] == d_str]
        if not filtered.empty:
            res['rev'] = int(filtered['합계_순매출'].apply(to_num).sum())
    
    if metrics_df is not None and not metrics_df.empty:
        filtered = metrics_df[metrics_df['일자'].astype(str).str.strip() == d_str]
        if not filtered.empty:
            row = filtered.iloc[0]
            res['nru'] = int(to_num(row['NRU']))
            res['mau'] = int(to_num(row['MAU']))
            res['bu'] = int(to_num(row['BU']))
            res['arppu'] = int(to_num(row['ARPPU']))
    
    return res

def show_ai_analysis_tab(c_d, c_month, c_year, p_d, df_sum_m2, df_sum_m3, df_items_m2, df_items_m3, df_met_m2, df_met_m3, format_val):
    st.markdown('<div style="background:#3a3f47; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">🤖 AI 분석 리포트</div>', unsafe_allow_html=True)
    
    # 세션 상태 (같은 달 재분석 방지)
    if 'ai_month' not in st.session_state:
        st.session_state.ai_month = None
    if 'ai_m2' not in st.session_state:
        st.session_state.ai_m2 = ""
    if 'ai_m3' not in st.session_state:
        st.session_state.ai_m3 = ""
    if 'ai_btn' not in st.session_state:
        st.session_state.ai_btn = False
    
    # 월 변경 시 초기화
    if st.session_state.ai_month != c_d:
        st.session_state.ai_m2 = ""
        st.session_state.ai_m3 = ""
        st.session_state.ai_month = c_d
    
    api_key = st.secrets.get("openai", {}).get("api_key")
    if not api_key:
        st.error("❌ `.streamlit/secrets.toml`에 추가:\n```\n[openai]\napi_key = \"sk-YOUR-KEY\"\n```")
        return
    
    # 버튼: 클릭했을 때만 True
    if st.button("🔄 분석 생성", use_container_width=True, type="primary"):
        st.session_state.ai_btn = True
    
    # 버튼 클릭했고 이전에 분석 없을 때만 API 호출
    if st.session_state.ai_btn and not st.session_state.ai_m2:
        with st.spinner("📊 데이터를 전략적으로 분석 중입니다"):
            try:
                # 데이터 추출
                m2c = get_data(df_items_m2, df_sum_m2, df_met_m2, c_d)
                m2p = get_data(df_items_m2, df_sum_m2, df_met_m2, p_d)
                m3c = get_data(df_items_m3, df_sum_m3, df_met_m3, c_d)
                m3p = get_data(df_items_m3, df_sum_m3, df_met_m3, p_d)
                
                # 짧은 프롬프트 (토큰 절약)
                prompt = f"""M2/M3 분석 ({c_year}{c_month:02d}월)

M2: 매출 {m2c['rev']:,}원 (전월: {m2p['rev']:,}, {((m2c['rev']-m2p['rev'])/m2p['rev']*100 if m2p['rev'] else 0):+.0f}%), NRU {m2c['nru']}, MAU {m2c['mau']}, ARPPU {m2c['arppu']:,}원

M3: 매출 {m3c['rev']:,}원 (전월: {m3p['rev']:,}, {((m3c['rev']-m3p['rev'])/m3p['rev']*100 if m3p['rev'] else 0):+.0f}%), NRU {m3c['nru']}, MAU {m3c['mau']}, ARPPU {m3c['arppu']:,}원

각 게임별 분석 (1-2줄):
1) 매출 평가
2) 사용자 건강도
3) 개선 방향"""
                
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                # 한 번의 API 호출로 M2/M3 분석 (할당량 절약!)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,  # 낮춤 (토큰 절약)
                    max_tokens=500     # 최소화
                )
                
                result = response.choices[0].message.content
                
                # 결과 분리 (간단하게)
                if "M2:" in result or "미르의전설2" in result:
                    parts = result.split("M3:") if "M3:" in result else result.split("미르의전설3")
                    st.session_state.ai_m2 = parts[0].strip()
                    st.session_state.ai_m3 = parts[1].strip() if len(parts) > 1 else "분석 중..."
                else:
                    st.session_state.ai_m2 = result
                    st.session_state.ai_m3 = ""
                
                st.session_state.ai_btn = False
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 오류: {str(e)}")
                st.session_state.ai_btn = False
    
    # 결과 표시
    if st.session_state.ai_m2:
        st.markdown('<div style="border-left:6px solid #dc2626; padding:20px; margin:30px 0 20px 0;"><h3 style="color:#000000; margin:0; font-size:20px; font-weight:900;">🎮 미르의전설2 분석</h3></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#000000; line-height:1.8; font-size:14px; background:#f8fafc; padding:20px; border-radius:6px;">{st.session_state.ai_m2}</div>', unsafe_allow_html=True)
    
    if st.session_state.ai_m3:
        st.markdown('<div style="border-left:6px solid #2563eb; padding:20px; margin:30px 0 20px 0;"><h3 style="color:#000000; margin:0; font-size:20px; font-weight:900;">🎮 미르의전설3 분석</h3></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#000000; line-height:1.8; font-size:14px; background:#f8fafc; padding:20px; border-radius:6px;">{st.session_state.ai_m3}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div style="background:#3a3f47; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">💬 코멘트</div>', unsafe_allow_html=True)
    
    comment = st.text_area("의견:", height=100, label_visibility="collapsed", key=f"cmt_{c_d}")
    
    c1, c2, c3 = st.columns([2, 1, 1])
    
    with c2:
        if st.button("저장", use_container_width=True, type="primary", key=f"sv_{c_d}"):
            if comment.strip():
                os.makedirs("data", exist_ok=True)
                data = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "month": f"{c_year}{c_month:02d}",
                    "comment": comment,
                    "m2": st.session_state.ai_m2,
                    "m3": st.session_state.ai_m3
                }
                file = "data/ai_comments.json"
                coms = json.load(open(file, 'r', encoding='utf-8')) if os.path.exists(file) else []
                coms.append(data)
                json.dump(coms, open(file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
                st.success("✅ 저장됨!")
                st.rerun()
            else:
                st.warning("⚠️ 입력")
    
    st.markdown("---")
    st.markdown('<div style="color:#000000; font-weight:600; font-size:18px; margin-bottom:15px;">📝 히스토리</div>', unsafe_allow_html=True)
    
    file = "data/ai_comments.json"
    if os.path.exists(file):
        coms = json.load(open(file, 'r', encoding='utf-8'))
        if coms:
            for c in reversed(coms[-10:]):
                with st.expander(f"📅 {c['date'][:10]}"):
                    st.markdown(f"<div style='color:#000000;'><b>💭 {c['comment']}</b></div>", unsafe_allow_html=True)
                    if c.get('m2'):
                        st.markdown(f"<div style='color:#000000; background:#f8fafc; padding:10px; margin-top:10px; border-radius:4px;'>{c['m2']}</div>", unsafe_allow_html=True)
                    if c.get('m3'):
                        st.markdown(f"<div style='color:#000000; background:#f8fafc; padding:10px; margin-top:10px; border-radius:4px;'>{c['m3']}</div>", unsafe_allow_html=True)
    else:
        st.info("저장된 코멘트 없음")
    
def show(menu, c_d, c_month, c_year, p_d, l_d, df_sum_m2, df_sum_m3, df_items_m2, df_items_m3, df_met_m2, df_met_m3, format_val, get_colored_html, hex_to_rgba, clean_item_name):
    
    # 세션 상태 초기화
    if 'ai_analysis' not in st.session_state:
        st.session_state.ai_analysis = ""
        st.session_state.ai_analysis_loading = False
        st.session_state.ai_analysis_m2 = ""
        st.session_state.ai_analysis_m3 = ""
    
    WEMADE_PURPLE = "#7C3AED"
    MIR_RED = "#dc2626"
    
    if menu == "미르의전설2/3 종합 리포트":
        # 탭 생성
        tab1, tab2 = st.tabs(["📊 종합 현황", "🤖 AI 분석"])
        
        with tab1:
            m2_g_c, m3_g_c = get_rev(df_sum_m2, df_items_m2, c_d, 'gross', 'm2'), get_rev(df_sum_m3, df_items_m3, c_d, 'gross', 'm3')
            m2_g_l, m3_g_l = get_rev(df_sum_m2, df_items_m2, l_d, 'gross', 'm2'), get_rev(df_sum_m3, df_items_m3, l_d, 'gross', 'm3')
            m2_c_c, m3_c_c = get_rev(df_sum_m2, df_items_m2, c_d, 'cum', 'm2'), get_rev(df_sum_m3, df_items_m3, c_d, 'cum', 'm3')
            m2_c_l, m3_c_l = get_rev(df_sum_m2, df_items_m2, l_d, 'cum', 'm2'), get_rev(df_sum_m3, df_items_m3, l_d, 'cum', 'm3')

            def draw_summary_table(title, ct, c2, c3, lt, l2, l3, lc, ll):
                st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                dt, d2, d3 = ct-lt, c2-l2, c3-l3
                pt, p2, p3 = (dt/lt*100 if lt!=0 else 0), (d2/l2*100 if l2!=0 else 0), (d3/l3*100 if l3!=0 else 0)
                st.markdown(f"""<table class="styled-table"><tr><th>구분</th><th>합산 (M2+M3)</th><th>미르의전설 2</th><th>미르의전설 3</th></tr>
                    <tr><td style="font-weight:900; background-color:#f1f5f9;">{lc}</td><td>{format_val(ct)}</td><td>{format_val(c2)}</td><td>{format_val(c3)}</td></tr>
                    <tr><td style="font-weight:900; background-color:#f1f5f9;">{ll}</td><td>{format_val(lt)}</td><td>{format_val(l2)}</td><td>{format_val(l3)}</td></tr>
                    <tr><td style="font-weight:900; background-color:#f1f5f9;">차액</td><td>{get_colored_html(dt, is_rev=True)}</td><td>{get_colored_html(d2, is_rev=True)}</td><td>{get_colored_html(d3, is_rev=True)}</td></tr>
                    <tr><td style="font-weight:900; background-color:#f1f5f9;">증감(%)</td><td>{get_colored_html(pt, True)}</td><td>{get_colored_html(p2, True)}</td><td>{get_colored_html(p3, True)}</td></tr></table>""", unsafe_allow_html=True)

            draw_summary_table("📍 당월 Gross 매출 현황", m2_g_c+m3_g_c, m2_g_c, m3_g_c, m2_g_l+m3_g_l, m2_g_l, m3_g_l, "당월 매출", "전년 동기")
            
            m2_note = get_analysis_from_csv(df_sum_m2, c_d)
            m3_note = get_analysis_from_csv(df_sum_m3, c_d)

            st.markdown(f"""
                <div class="analysis-header">📝 {c_year}년 {c_month}월 매출 변동 원인</div>
                <div class="analysis-body">
                    <div class="analysis-col">
                        <div class="col-label">미르의전설 2</div>
                        <div class="col-content">{m2_note}</div>
                    </div>
                    <div class="analysis-col">
                        <div class="col-label">미르의전설 3</div>
                        <div class="col-content">{m3_note}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            draw_summary_table("📅 당해 연도 누적 매출 현황", m2_c_c+m3_c_c, m2_c_c, m3_c_c, m2_c_l+m3_c_l, m2_c_l, m3_c_l, "올해 누적", "전년 누적")

            st.markdown('<div class="section-title">📈 전년 대비 누적 매출 추이 비교</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설2 누적 매출</h3></div>', unsafe_allow_html=True)
                st.plotly_chart(make_rev_chart(df_items_m2, df_sum_m2, MIR_RED, c_year, c_d, hex_to_rgba, 'm2'), use_container_width=True, key="rev_m2")
            with c2:
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설3 누적 매출</h3></div>', unsafe_allow_html=True)
                st.plotly_chart(make_rev_chart(df_items_m3, df_sum_m3, MIR_RED, c_year, c_d, hex_to_rgba, 'm3'), use_container_width=True, key="rev_m3")
         

            st.markdown('<div class="section-title">📊 게임별 주요 지표 현황 (전월 대비 MoM)</div>', unsafe_allow_html=True)
            m2_curr, m2_prev = get_metrics_row(df_met_m2, c_d), get_metrics_row(df_met_m2, p_d)
            m3_curr, m3_prev = get_metrics_row(df_met_m3, c_d), get_metrics_row(df_met_m3, p_d)

            def draw_mom_metrics(game_name, curr, prev):
                if curr is None: return "<tr><td colspan='5'>데이터 없음</td></tr>"
                cols, html = ["NRU", "MAU", "BU", "ARPPU"], f"<tr><td style='background-color:#f1f5f9; font-weight:900;'>{game_name}</td>"
                for col in cols:
                    c_val, p_val = to_num(curr[col]), (to_num(prev[col]) if prev is not None else 0)
                    diff_html = get_colored_html(c_val - p_val, is_rev=(col=='ARPPU'))
                    html += f"<td>{c_val:,.0f}<br/>({diff_html})</td>"
                return html + "</tr>"

            st.markdown(f"""<table class="styled-table"><tr><th>구분</th><th>NRU (신규)</th><th>MAU (활성)</th><th>BU (결제)</th><th>ARPPU</th></tr>
                {draw_mom_metrics("미르의전설 2", m2_curr, m2_prev)}{draw_mom_metrics("미르의전설 3", m3_curr, m3_prev)}</table>""", unsafe_allow_html=True)

            st.markdown('<div class="section-title">📊 게임별 통합 지표 추이 (NRU / MAU / BU / ARPPU)</div>', unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설2 통합 지표</h3></div>', unsafe_allow_html=True)
                st.plotly_chart(make_combined_metrics_chart(df_met_m2, WEMADE_PURPLE, c_year, hex_to_rgba), use_container_width=True, key="metrics_m2")
            with mc2:
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설3 통합 지표</h3></div>', unsafe_allow_html=True)
                st.plotly_chart(make_combined_metrics_chart(df_met_m3, MIR_RED, c_year, hex_to_rgba), use_container_width=True, key="metrics_m3")

            st.markdown('<div class="section-title">🏆 당월 아이템 판매 순위 (Top 10)</div>', unsafe_allow_html=True)
            
            def render_items(df, d_str, game_name):
                if df is None: return
                curr = df[df['일자'] == d_str]
                if curr.empty: 
                    st.info(f"{game_name} - 판매 데이터 없음")
                    return
                curr = curr.copy()
                curr['합계_순매출_n'] = curr['합계_순매출'].apply(to_num)
                sum_df = curr.groupby(curr.columns[0])['합계_순매출_n'].sum().reset_index()
                top10 = sum_df.sort_values(by='합계_순매출_n', ascending=False).head(10)
                total = sum_df['합계_순매출_n'].sum()
                html = '<table class="styled-table"><thead><tr><th>순위</th><th>아이템명</th><th>순매출</th><th>비중</th></tr></thead><tbody>'
                for i, row in enumerate(top10.itertuples(), 1):
                    html += f'<tr><td>{i}</td><td>{clean_item_name(row[1])}</td><td>{format_val(row[2])}</td><td>{(row[2]/total*100):.1f}%</td></tr>'
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

            sl, sr = st.columns(2)
            with sl: 
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설2</h3></div>', unsafe_allow_html=True)
                render_items(df_items_m2, c_d, "미르의전설2")
            with sr: 
                st.markdown(f'<div class="dark-header-box"><h3>미르의전설3</h3></div>', unsafe_allow_html=True)
                render_items(df_items_m3, c_d, "미르의전설3")
        
        with tab2:
            # AI 분석 탭
            show_ai_analysis_tab(c_d, c_month, c_year, p_d, df_sum_m2, df_sum_m3, df_items_m2, df_items_m3, df_met_m2, df_met_m3, format_val)

    elif "상세" in menu:
        target_df = df_items_m2 if "2" in menu else df_items_m3
        if target_df is not None:
            st.markdown(f'<div class="section-title">📊 {menu} 데이터 ({c_d})</div>', unsafe_allow_html=True)
            st.dataframe(target_df[target_df['일자'] == c_d], use_container_width=True)
