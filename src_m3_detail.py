import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os

def to_num(v):
    """문자열을 숫자로 변환 (쉼표 제거)"""
    try:
        return float(str(v).replace(',', ''))
    except:
        return 0

def safe_read_csv(file_path):
    """안전하게 CSV 읽기 (인코딩 자동 감지)"""
    encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1']
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            df.columns = df.columns.str.strip()
            return df
        except:
            continue
    return None

def clean_item_name_for_map(name):
    """마지막 공백과 괄호(ID 숫자)만 제거"""
    name = str(name).strip()
    # 마지막에 붙은 공백 + (숫자) 형태만 제거
    # 예: " (450012000)", " (12345)" 등
    name = re.sub(r'\s+\(\d+\)$', '', name).strip()
    # 연속 공백 정리
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def normalize_level_date(date_str):  # ← 추가
    """날짜 정규화: '2023. 1. 1' → '202301'"""
    date_str = str(date_str).strip()
    parts = re.findall(r'\d+', date_str)
    if len(parts) >= 2:
        year = parts[0]
        month = parts[1].zfill(2)
        return year + month
    return None


def regenerate_item_map():
    """원본 CSV에서 item_map_m3.csv 생성"""
    try:
        df = safe_read_csv('data/items_m3_2026.csv')
        if df is None:
            return False
        
        if '아이템명' not in df.columns or '구분' not in df.columns:
            return False
        
        item_map = df[['아이템명', '구분']].drop_duplicates()
        item_map.columns = ['아이템', '구분']
        item_map.to_csv('item_map_m3.csv', index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"❌ item_map 생성 오류: {e}")
        return False

def load_item_map():
    """item_map_m3.csv 로드"""
    return safe_read_csv('item_map_m3.csv')

# 앱 시작 시 item_map 자동 생성
if not os.path.exists('item_map_m3.csv'):
    regenerate_item_map()

# 브랜드 컬러
BRAND_COLOR = "#3a3f47"
HEADER_COLOR = "#5a6370"
ACCENT_COLOR_RED = "#dc2626"
ACCENT_COLOR_BLUE = "#2563eb"

def show(year, month, df_sum_m3, df_items_m3, df_metrics_m3, hex_to_rgba, clean_item_name):
    c_d = f"{year}{month:02d}"
    l_d = f"{year-1}{month:02d}"
    c_month = month
    c_year = year
    
    # 전월 계산
    p_month = month - 1
    p_year = year
    if p_month <= 0:
        p_month = 12
        p_year -= 1
    p_d = f"{p_year}{p_month:02d}"

    # 작년 데이터 로드
    df_items_m3_l = safe_read_csv(f'data/items_m3_{c_year-1}.csv')
    if df_items_m3_l is not None and not df_items_m3_l.empty:
        if '일자' in df_items_m3_l.columns:
            df_items_m3_l['일자'] = df_items_m3_l['일자'].astype(str).str[:6]
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📈 매출 현황", "👥 접속캐릭터", "📋 아이템 상세"])
    
    # ========== TAB 1: 매출 현황 ==========
    with tab1:
        st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">💰 매출 및 주요지표</div>', unsafe_allow_html=True)
        
        if df_items_m3 is not None and not df_items_m3.empty and df_sum_m3 is not None and not df_sum_m3.empty:
            # 아이템을 정규화
            df_items_m3_temp = df_items_m3.copy()
            df_items_m3_temp['일자'] = df_items_m3_temp['일자'].astype(str).str[:6]
            df_items_m3_temp['아이템_정규화'] = df_items_m3_temp['아이템'].apply(clean_item_name_for_map)
            
            # 당월 계산
            c_items = df_items_m3_temp[(df_items_m3_temp['일자'] == c_d) & (df_items_m3_temp['아이템'] != 'TOTAL')]
            c_item_rev = c_items['합계_순매출'].apply(to_num).sum() if not c_items.empty else 0
            c_rev = c_item_rev
            
            # 전년동월 계산
            l_items = df_items_m3_temp[(df_items_m3_temp['일자'] == l_d) & (df_items_m3_temp['아이템'] != 'TOTAL')]
            l_item_rev = l_items['합계_순매출'].apply(to_num).sum() if not l_items.empty else 0
            l_rev = l_item_rev
            
            # 전월 계산
            p_items = df_items_m3_temp[(df_items_m3_temp['일자'] == p_d) & (df_items_m3_temp['아이템'] != 'TOTAL')]
            p_item_rev = p_items['합계_순매출'].apply(to_num).sum() if not p_items.empty else 0
            p_rev = p_item_rev
            
            # 변동율 계산
            yoy_change = c_rev - l_rev
            yoy_pct = (yoy_change / l_rev * 100) if l_rev > 0 else 0
            yoy_type = 'increase' if yoy_change >= 0 else 'decrease'
            
            mom_change = c_rev - p_rev
            mom_pct = (mom_change / p_rev * 100) if p_rev > 0 else 0
            mom_type = 'increase' if mom_change >= 0 else 'decrease'
            
            # 위: 매출 3개 카드
            col1, col2, col3 = st.columns(3)
            
            with col1:
                border_color = "#ef4444" if c_rev > 0 else "#3b82f6"
                st.markdown(f"""
                <div style="background:#ffffff; padding:24px; border-radius:8px; text-align:center; border-left:4px solid {border_color};">
                    <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>당월 매출</b></div>
                    <div style="color:#000; font-size:32px; font-weight:900;">₩{c_rev/1e8:.2f}억</div>
                    <div style="color:#999; font-size:12px; margin-top:5px;">₩{int(c_rev):,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                arrow_yoy = "▲" if yoy_type == "increase" else "▼"
                text_color = "#dc2626" if yoy_type == "increase" else "#2563eb"
                st.markdown(f"""
                <div style="background:#ffffff; padding:24px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                    <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>전년동기 대비</b></div>
                    <div style="color:{text_color}; font-size:32px; font-weight:900;">{arrow_yoy} {abs(yoy_pct):.1f}%</div>
                    <div style="color:#999; font-size:12px; margin-top:5px;">{arrow_yoy} ₩{int(abs(yoy_change)):,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                arrow_mom = "▲" if mom_type == "increase" else "▼"
                text_color = "#dc2626" if mom_type == "increase" else "#2563eb"
                st.markdown(f"""
                <div style="background:#ffffff; padding:24px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                    <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>전월 대비</b></div>
                    <div style="color:{text_color}; font-size:32px; font-weight:900;">{arrow_mom} {abs(mom_pct):.1f}%</div>
                    <div style="color:#999; font-size:12px; margin-top:5px;">{arrow_mom} ₩{int(abs(mom_change)):,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 간격
            st.markdown("<div style='margin:15px 0;'></div>", unsafe_allow_html=True)
            
            # 아래: 지표 4개 카드
            if df_metrics_m3 is not None and not df_metrics_m3.empty:
                c_metric = df_metrics_m3[df_metrics_m3['일자'].astype(str).str[:6] == c_d]
                if not c_metric.empty:
                    c_nru = to_num(c_metric['NRU'].values[0]) if 'NRU' in df_metrics_m3.columns else 0
                    c_mau = to_num(c_metric['MAU'].values[0]) if 'MAU' in df_metrics_m3.columns else 0
                    c_bu = to_num(c_metric['BU'].values[0]) if 'BU' in df_metrics_m3.columns else 0
                    c_arppu = to_num(c_metric['ARPPU'].values[0]) if 'ARPPU' in df_metrics_m3.columns else 0
                    
                    l_metric = df_metrics_m3[df_metrics_m3['일자'].astype(str).str[:6] == l_d]
                    l_nru = to_num(l_metric['NRU'].values[0]) if not l_metric.empty and 'NRU' in df_metrics_m3.columns else 0
                    l_mau = to_num(l_metric['MAU'].values[0]) if not l_metric.empty and 'MAU' in df_metrics_m3.columns else 0
                    l_bu = to_num(l_metric['BU'].values[0]) if not l_metric.empty and 'BU' in df_metrics_m3.columns else 0
                    l_arppu = to_num(l_metric['ARPPU'].values[0]) if not l_metric.empty and 'ARPPU' in df_metrics_m3.columns else 0
                    
                    p_metric = df_metrics_m3[df_metrics_m3['일자'].astype(str).str[:6] == p_d]
                    p_nru = to_num(p_metric['NRU'].values[0]) if not p_metric.empty and 'NRU' in df_metrics_m3.columns else 0
                    p_mau = to_num(p_metric['MAU'].values[0]) if not p_metric.empty and 'MAU' in df_metrics_m3.columns else 0
                    p_bu = to_num(p_metric['BU'].values[0]) if not p_metric.empty and 'BU' in df_metrics_m3.columns else 0
                    p_arppu = to_num(p_metric['ARPPU'].values[0]) if not p_metric.empty and 'ARPPU' in df_metrics_m3.columns else 0
                    
                    # 전월 대비 변동율
                    nru_pct = ((c_nru - p_nru) / p_nru * 100) if p_nru > 0 else 0
                    mau_pct = ((c_mau - p_mau) / p_mau * 100) if p_mau > 0 else 0
                    bu_pct = ((c_bu - p_bu) / p_bu * 100) if p_bu > 0 else 0
                    arppu_pct = ((c_arppu - p_arppu) / p_arppu * 100) if p_arppu > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        arrow = "▲" if nru_pct > 0 else "▼"
                        text_color = "#dc2626" if nru_pct > 0 else "#2563eb"
                        st.markdown(f"""
                        <div style="background:#ffffff; padding:20px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                            <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>NRU</b></div>
                            <div style="color:#000; font-size:28px; font-weight:900;">{int(c_nru):,}</div>
                            <div style="color:{text_color}; font-size:12px; font-weight:900; margin-top:8px;">{arrow} {abs(nru_pct):.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        arrow = "▲" if mau_pct > 0 else "▼"
                        text_color = "#dc2626" if mau_pct > 0 else "#2563eb"
                        st.markdown(f"""
                        <div style="background:#ffffff; padding:20px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                            <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>MAU</b></div>
                            <div style="color:#000; font-size:28px; font-weight:900;">{int(c_mau):,}</div>
                            <div style="color:{text_color}; font-size:12px; font-weight:900; margin-top:8px;">{arrow} {abs(mau_pct):.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        arrow = "▲" if bu_pct > 0 else "▼"
                        text_color = "#dc2626" if bu_pct > 0 else "#2563eb"
                        st.markdown(f"""
                        <div style="background:#ffffff; padding:20px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                            <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>BU</b></div>
                            <div style="color:#000; font-size:28px; font-weight:900;">{int(c_bu):,}</div>
                            <div style="color:{text_color}; font-size:12px; font-weight:900; margin-top:8px;">{arrow} {abs(bu_pct):.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        arrow = "▲" if arppu_pct > 0 else "▼"
                        text_color = "#dc2626" if arppu_pct > 0 else "#2563eb"
                        st.markdown(f"""
                        <div style="background:#ffffff; padding:20px; border-radius:8px; text-align:center; border-left:4px solid {text_color};">
                            <div style="color:#666; font-size:13px; margin-bottom:8px;"><b>ARPPU</b></div>
                            <div style="color:#000; font-size:28px; font-weight:900;">₩{int(c_arppu):,}</div>
                            <div style="color:{text_color}; font-size:12px; font-weight:900; margin-top:8px;">{arrow} {abs(arppu_pct):.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("📊 데이터가 없습니다.")
        
        # ===== 분류별 매출 (상시 + 한정 + 몽환) =====
        st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:30px 0 15px;">🏷️ 분류별 매출</div>', unsafe_allow_html=True)        
      
        item_map = load_item_map()
        
        if item_map is None or item_map.empty:
            st.info("📊 item_map_m3.csv 파일이 필요합니다.")
        elif df_items_m3 is None or df_items_m3.empty:
            st.info("📊 아이템 데이터가 없습니다.")
        else:
            try:
                item_map["구분_정규화"] = item_map["구분"].astype(str).str.strip()
                item_map["아이템_정규화"] = item_map["아이템"].apply(clean_item_name_for_map)
                
                target_items = df_items_m3[(df_items_m3['일자'].astype(str).str[:6] == c_d)].copy()
                target_items = target_items[target_items['아이템'] != 'TOTAL'].copy()
                target_items['아이템_정규화'] = target_items['아이템'].apply(clean_item_name_for_map)
                
                if target_items.empty:
                    st.info("📊 해당 월의 데이터가 없습니다.")
                elif "구분" not in item_map.columns:
                    st.error("❌ item_map_m3.csv에 '구분' 컬럼이 필요합니다.")
                else:
                    
                    # ===== 분류별 매출 계산 =====
                    category_mapping = {
                        "상시": "상시판매",
                        "한정": "한정상품",
                        "몽환": "몽환서버"
                    }
                    
                    cat_data = []
                    total_revenue = 0
                    
                    for item_map_category, display_name in category_mapping.items():
                        category_item_names = item_map[item_map["구분_정규화"] == item_map_category]["아이템_정규화"].tolist()
                        matched_items = target_items[target_items["아이템_정규화"].isin(category_item_names)]
                        category_revenue = matched_items['합계_순매출'].apply(to_num).sum()
                        total_revenue += category_revenue
                        
                        cat_data.append({
                            "분류": display_name,
                            "매출": int(category_revenue),
                            "매출_str": f"₩{int(category_revenue):,}"
                        })
                    
                    cat_data.append({
                        "분류": "총합",
                        "매출": int(total_revenue),
                        "매출_str": f"₩{int(total_revenue):,}"
                    })
                    
                    html_table = f'<table style="width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1);"><thead><tr style="background:{HEADER_COLOR}; color:#ffffff;"><th style="padding:16px; text-align:center; font-weight:900; font-size:14px; border:none;">분류</th><th style="padding:16px; text-align:center; font-weight:900; font-size:14px; border:none;">매출</th><th style="padding:16px; text-align:center; font-weight:900; font-size:14px; border:none;">비율(%)</th></tr></thead><tbody>'
                    
                    for idx, row in enumerate(cat_data):
                        if row["분류"] == "총합":
                            row_bg = "#f0f4ff"
                            text_weight = "font-weight:900;"
                            border_style = f"border-top:2px solid {BRAND_COLOR};"
                        else:
                            row_bg = "#ffffff" if idx % 2 == 0 else "#f8f9ff"
                            text_weight = "font-weight:700;"
                            border_style = "border-bottom:1px solid #e5e7eb;"
                        
                        ratio = f"{(row['매출']/total_revenue*100):.1f}%" if row["분류"] != "총합" and total_revenue > 0 else "-"
                        
                        html_table += f"<tr style=\"background:{row_bg}; {border_style}\"><td style=\"padding:14px; text-align:center; {text_weight} color:#333;\">{row['분류']}</td><td style=\"padding:14px; text-align:center; {text_weight} color:#333;\">{row['매출_str']}</td><td style=\"padding:14px; text-align:center; {text_weight} color:#333;\">{ratio}</td></tr>"
                    
                    html_table += """</tbody></table>"""
                    
                    col_table, col_pie = st.columns([3, 2])
                    
                    with col_table:
                        st.markdown(html_table, unsafe_allow_html=True)
                    
                    with col_pie:
                        st.markdown(f'<div style="background:#f8f9ff; padding:12px; border-radius:6px; font-weight:600; margin-bottom:12px; color:{BRAND_COLOR}; font-size:14px; text-align:center;">📊 분류별 비중</div>', unsafe_allow_html=True)
                        
                        if cat_data and total_revenue > 0:
                            pie_data = [row for row in cat_data if row['분류'] != '총합']
                            pie_labels = [row['분류'] for row in pie_data]
                            pie_values = [row['매출'] for row in pie_data]
                            
                            colors_pie = ['#7C3AED', '#dc2626', '#2563eb']
                            
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=pie_labels,
                                values=pie_values,
                                marker=dict(colors=colors_pie[:len(pie_labels)], line=dict(color='#ffffff', width=3)),
                                hovertemplate='<b>%{label}</b><br>₩%{value:,.0f}<br>%{percent}<extra></extra>',
                                textposition='inside',
                                textinfo='label+percent',
                                textfont=dict(size=12, color='white', family='Arial Black')
                            )])
                            
                            fig_pie.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=320,
                                margin=dict(l=0, r=0, t=0, b=0),
                                font=dict(color='#000000', size=11),
                                showlegend=False
                            )
                            
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            st.info("분류별 데이터가 없습니다.")

            except Exception as e:
                st.error(f"❌ 분류별 매출 계산 중 오류 발생: {str(e)}")

      
        # ===== 누적 매출 추이 비교 그래프 =====
        st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:30px 0 15px;">📈 누적 매출 추이 (당년 vs 전년)</div>', unsafe_allow_html=True)
        
        if df_items_m3 is not None and not df_items_m3.empty and df_items_m3_l is not None and not df_items_m3_l.empty:
            try:
                x_m = [f"{i:02d}월" for i in range(1, 13)]
                c_idx = int(c_d[4:])
                
                df_items_m3_temp = df_items_m3.copy()
                df_items_m3_temp['일자'] = df_items_m3_temp['일자'].astype(str).str[:6]
                
                cum_current = []
                cum_prior = []
                cum_c = 0
                cum_p = 0
                
                for i in range(1, 13):
                    # 현재연도
                    m_d = f"{c_year}{i:02d}"
                    m_items = df_items_m3_temp[(df_items_m3_temp['일자'] == m_d) & (df_items_m3_temp['아이템'] != 'TOTAL')]
                    m_rev = m_items['합계_순매출'].apply(to_num).sum() if not m_items.empty else 0
                    cum_c += m_rev
                    cum_current.append(cum_c)
                    
                    # 전년도
                    pm_d = f"{c_year-1}{i:02d}"
                    pm_items = df_items_m3_l[(df_items_m3_l['일자'] == pm_d) & (df_items_m3_l['아이템'] != 'TOTAL')]
                    pm_rev = pm_items['합계_순매출'].apply(to_num).sum() if not pm_items.empty else 0
                    cum_p += pm_rev
                    cum_prior.append(cum_p)
                
                fig_cum = go.Figure()
                
                fig_cum.add_trace(go.Scatter(
                    x=x_m, y=cum_prior,
                    name=f'{c_year-1}년',
                    line=dict(color='#94a3b8', width=2, dash='dot'),
                    mode='lines+markers',
                    hovertemplate='<b>%{x}</b><br>누적: ₩%{y:,.0f}<extra></extra>'
                ))
                
                fig_cum.add_trace(go.Scatter(
                    x=x_m[:c_idx], y=cum_current[:c_idx],
                    name=f'{c_year}년',
                    line=dict(color='#3a3f47', width=4),
                    mode='lines+markers',
                    hovertemplate='<b>%{x}</b><br>누적: ₩%{y:,.0f}<extra></extra>'
                ))
                
                fig_cum.update_layout(
                    paper_bgcolor='#ffffff',
                    plot_bgcolor='#f8fafc',
                    height=350,
                    margin=dict(l=40, r=20, t=10, b=20),
                    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1, font=dict(color='black')),
                    xaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickfont=dict(color='black'), side='bottom'),
                    yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickformat=',.0f', tickfont=dict(color='black'), rangemode='tozero'),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_cum, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ 누적 매출 추이 차트 생성 오류: {str(e)}")
        else:
            st.info("📊 작년 데이터가 없습니다.")

    # ===== TAB 2: 접속캐릭터 =====
    with tab2:
        st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">👥 접속캐릭터</div>', unsafe_allow_html=True)
        
        # level_m3.csv 로드
        df_level = safe_read_csv('data/level_m3.csv')
        
        if df_level is None or df_level.empty:
            st.info("📊 접속캐릭터 데이터를 불러올 수 없습니다.")
        else:
            # 날짜 형식 정규화: '2023. 1. 1' → '202301'
            df_level['일자_정규화'] = df_level['일자'].apply(normalize_level_date)
            df_level['일자_전체'] = df_level['일자'].astype(str)
            
            level_columns = [col for col in df_level.columns if col not in ['일자', '일자_정규화', '일자_전체']]
            
            # 컬럼을 숫자로 변환
            for col in level_columns:
                df_level[col] = pd.to_numeric(df_level[col], errors='coerce').fillna(0)
            
            # 월단위 집계 (평균)
            df_level_monthly = df_level.groupby('일자_정규화')[level_columns].mean().reset_index()
            
            c_level_monthly = df_level_monthly[df_level_monthly['일자_정규화'] == c_d]
            l_level_monthly = df_level_monthly[df_level_monthly['일자_정규화'] == l_d]
            
            # ===== 섹션 1: 당월 vs 전년동월 비교 =====
            st.markdown(f'<div style="background:#f8f9ff; padding:12px; border-radius:6px; font-weight:600; margin-bottom:12px; color:{BRAND_COLOR}; font-size:14px; text-align:center;">📊 당월 vs 전년동월 레벨별 접속캐릭터 현황 (월 평균)</div>', unsafe_allow_html=True)
            
            if not c_level_monthly.empty and not l_level_monthly.empty:
                c_level_data = c_level_monthly.iloc[0]
                l_level_data = l_level_monthly.iloc[0]
                
                # 비교 테이블
                html_level_table = f'<table style="width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1);"><thead><tr style="background:{HEADER_COLOR}; color:#ffffff;">'
                html_level_table += '<th style="padding:12px; text-align:center; font-weight:900; font-size:12px; border:none;">레벨</th>'
                html_level_table += '<th style="padding:12px; text-align:center; font-weight:900; font-size:12px; border:none;">당월</th>'
                html_level_table += '<th style="padding:12px; text-align:center; font-weight:900; font-size:12px; border:none;">전년동월</th>'
                html_level_table += '<th style="padding:12px; text-align:center; font-weight:900; font-size:12px; border:none;">증감(캐릭터수)</th>'
                html_level_table += '<th style="padding:12px; text-align:center; font-weight:900; font-size:12px; border:none;">증감(%)</th>'
                html_level_table += '</tr></thead><tbody>'
                
                total_c = 0
                total_l = 0
                
                for idx, col in enumerate(level_columns):
                    c_val = c_level_data[col]
                    l_val = l_level_data[col]
                    diff = c_val - l_val
                    pct = (diff / l_val * 100) if l_val > 0 else 0
                    
                    total_c += c_val
                    total_l += l_val
                    
                    row_bg = '#ffffff' if idx % 2 == 0 else '#f8f9ff'
                    
                    if diff > 0:
                        diff_color = ACCENT_COLOR_RED
                        diff_symbol = '▲'
                    elif diff < 0:
                        diff_color = ACCENT_COLOR_BLUE
                        diff_symbol = '▼'
                    else:
                        diff_color = '#666'
                        diff_symbol = '-'
                    
                    html_level_table += f'<tr style="background:{row_bg}; border-bottom:1px solid #e5e7eb;"><td style="padding:12px; text-align:center; font-weight:700; color:#333;">레벨 {col}</td><td style="padding:12px; text-align:center; font-weight:700; color:#333;">{int(c_val):,}</td><td style="padding:12px; text-align:center; font-weight:700; color:#333;">{int(l_val):,}</td><td style="padding:12px; text-align:center; font-weight:700; color:{diff_color};">{diff_symbol} {int(abs(diff)):,}</td><td style="padding:12px; text-align:center; font-weight:700; color:{diff_color};">{diff_symbol} {abs(pct):.1f}%</td></tr>'
                
                total_diff = total_c - total_l
                total_pct = (total_diff / total_l * 100) if total_l > 0 else 0
                total_diff_color = ACCENT_COLOR_RED if total_diff > 0 else ACCENT_COLOR_BLUE if total_diff < 0 else '#666'
                total_diff_symbol = '▲' if total_diff > 0 else '▼' if total_diff < 0 else '-'
                
                html_level_table += f'<tr style="background:#f0f4ff; border-top:2px solid {BRAND_COLOR};"><td style="padding:12px; text-align:center; font-weight:900; color:#333;">총합</td><td style="padding:12px; text-align:center; font-weight:900; color:#333;">{int(total_c):,}</td><td style="padding:12px; text-align:center; font-weight:900; color:#333;">{int(total_l):,}</td><td style="padding:12px; text-align:center; font-weight:900; color:{total_diff_color};">{total_diff_symbol} {int(abs(total_diff)):,}</td><td style="padding:12px; text-align:center; font-weight:900; color:{total_diff_color};">{total_diff_symbol} {abs(total_pct):.1f}%</td></tr>'
                
                html_level_table += '</tbody></table>'
                st.markdown(html_level_table, unsafe_allow_html=True)
                
                st.markdown('<div style="margin:20px 0;"></div>', unsafe_allow_html=True)
                
                # ===== 섹션 2: 파이 차트 (당월 레벨 분포) =====
                st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">📊 당월 레벨별 접속캐릭터 분포 (월 평균)</div>', unsafe_allow_html=True)
                
                pie_labels = [f"레벨 {col}" for col in level_columns]
                pie_values = [int(c_level_data[col]) for col in level_columns]
                
                colors_level = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#f87171', '#8b5cf6', '#ec4899', '#f43f5e', '#6366f1', '#14b8a6', '#0891b2', '#0ea5e9', '#1e40af', '#f59e0b']
                
                # 파이 차트 왼쪽 표 생성
                pie_table_html = f'<table style="width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1);"><thead><tr style="background:{HEADER_COLOR}; color:#ffffff;">'
                pie_table_html += '<th style="padding:10px; text-align:center; font-weight:900; font-size:12px; border:none;">레벨</th>'
                pie_table_html += '<th style="padding:10px; text-align:center; font-weight:900; font-size:12px; border:none;">캐릭터수</th>'
                pie_table_html += '<th style="padding:10px; text-align:center; font-weight:900; font-size:12px; border:none;">비율(%)</th>'
                pie_table_html += '</tr></thead><tbody>'
                
                total_pie = sum(pie_values)
                
                for idx, (label, value) in enumerate(zip(pie_labels, pie_values)):
                    pct = (value / total_pie * 100) if total_pie > 0 else 0
                    row_bg = '#ffffff' if idx % 2 == 0 else '#f8f9ff'
                    pie_table_html += f'<tr style="background:{row_bg}; border-bottom:1px solid #e5e7eb;"><td style="padding:10px; text-align:center; font-weight:600; color:#333; font-size:12px;">{label}</td><td style="padding:10px; text-align:center; font-weight:600; color:#333; font-size:12px;">{int(value):,}</td><td style="padding:10px; text-align:center; font-weight:600; color:#333; font-size:11px;">{pct:.1f}%</td></tr>'
                
                pie_table_html += f'<tr style="background:#f0f4ff; border-top:2px solid {BRAND_COLOR};"><td style="padding:10px; text-align:center; font-weight:900; color:#333; font-size:12px;">총합</td><td style="padding:10px; text-align:center; font-weight:900; color:#333; font-size:12px;">{int(total_pie):,}</td><td style="padding:10px; text-align:center; font-weight:900; color:#333; font-size:11px;">100.0%</td></tr>'
                pie_table_html += '</tbody></table>'
                
                # 좌우 레이아웃으로 표와 파이 차트 배치
                col_table, col_pie = st.columns([1, 1.5])
                
                with col_table:
                    st.markdown(pie_table_html, unsafe_allow_html=True)
                
                with col_pie:
                    st.markdown(f'<div style="background:#f8f9ff; padding:12px; border-radius:6px; font-weight:600; margin-bottom:12px; color:{BRAND_COLOR}; font-size:14px; text-align:center;">📊 접속캐릭터 비중</div>', unsafe_allow_html=True)
                    
                    fig_level_pie = go.Figure(data=[go.Pie(
                        labels=pie_labels,
                        values=pie_values,
                        marker=dict(colors=colors_level[:len(pie_labels)], line=dict(color='#ffffff', width=2)),
                        hovertemplate='<b>%{label}</b><br>%{value:,}명<br>%{percent}<extra></extra>',
                        textposition='inside',
                        textinfo='label+percent',
                        textfont=dict(size=11, color='white', family='Arial Black')
                    )])
                    
                    fig_level_pie.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=500,
                        margin=dict(l=0, r=50, t=0, b=0),
                        font=dict(color='#000000', size=11),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_level_pie, use_container_width=True)
                
                st.markdown('<div style="margin:20px 0;"></div>', unsafe_allow_html=True)
                
                # ===== 섹션 3: 월별 추이 그래프 (2023년 1월 ~ 당월까지) =====
                st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">📈 레벨별 접속캐릭터 월별 추이 (2023년 1월 ~ 당월)</div>', unsafe_allow_html=True)
                
                # 2023년 1월부터 당월까지의 모든 월을 생성
                all_months = []
                start_year, start_month = 2023, 1
                end_year, end_month = int(c_d[:4]), int(c_d[4:])
                
                current_year, current_month = start_year, start_month
                while (current_year, current_month) <= (end_year, end_month):
                    all_months.append(f"{current_year}{current_month:02d}")
                    current_month += 1
                    if current_month > 12:
                        current_month = 1
                        current_year += 1
                
                x_m_full = [f"{m[4:]}/'{m[2:4]}" for m in all_months]  # 월/년 형식
                
                fig_level_monthly_trend = go.Figure()
                colors_trend = colors_level
                
                for idx, col in enumerate(level_columns):
                    monthly_values = []
                    for month_d in all_months:
                        month_data = df_level_monthly[df_level_monthly['일자_정규화'] == month_d]
                        monthly_values.append(int(month_data[col].values[0]) if not month_data.empty else 0)
                    
                    fig_level_monthly_trend.add_trace(go.Scatter(
                        x=x_m_full,
                        y=monthly_values,
                        name=f"레벨 {col}",
                        line=dict(color=colors_trend[idx % len(colors_trend)], width=2),
                        mode='lines+markers',
                        marker=dict(size=4),
                        hovertemplate=f'<b>레벨 {col}</b><br>%{{y:,}}명<extra></extra>'
                    ))
                
                fig_level_monthly_trend.update_layout(
                    paper_bgcolor='#ffffff',
                    plot_bgcolor='#f8fafc',
                    height=500,
                    margin=dict(l=50, r=0, t=10, b=50),
                    legend=dict(
                        orientation='v',
                        yanchor='top',
                        y=0.99,
                        xanchor='left',
                        x=1.01,
                        font=dict(color='#000000', size=11),
                        bgcolor='rgba(255,255,255,0.95)',
                        bordercolor='#e5e7eb',
                        borderwidth=1,
                        tracegroupgap=3
                    ),
                    xaxis=dict(
                        showgrid=True, 
                        gridcolor='#e2e8f0', 
                        tickfont=dict(color='black', size=10),
                        tickangle=-45
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='#e2e8f0', 
                        tickformat=',', 
                        tickfont=dict(color='black', size=10), 
                        rangemode='tozero'
                    ),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_level_monthly_trend, use_container_width=True)
                
                st.markdown('<div style="margin:20px 0;"></div>', unsafe_allow_html=True)
                
                # ===== 섹션 4: 당월 일단위 상세 데이터 =====
                st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">📈 당월 레벨별 접속캐릭터 일단위 추이</div>', unsafe_allow_html=True)
                
                df_level_current = df_level[df_level['일자_정규화'] == c_d].copy()
                df_level_current['일차'] = range(1, len(df_level_current) + 1)
                
                if not df_level_current.empty:
                    fig_level_daily = go.Figure()
                    
                    for idx, col in enumerate(level_columns):
                        fig_level_daily.add_trace(go.Scatter(
                            x=df_level_current['일차'],
                            y=df_level_current[col].astype(int),
                            name=f"레벨 {col}",
                            line=dict(color=colors_trend[idx % len(colors_trend)], width=2),
                            mode='lines+markers',
                            marker=dict(size=5),
                            hovertemplate=f'<b>레벨 {col}</b><br>%{{y:,}}명<extra></extra>'
                        ))
                    
                    fig_level_daily.update_layout(
                        paper_bgcolor='#ffffff',
                        plot_bgcolor='#f8fafc',
                        height=550,
                        margin=dict(l=50, r=0, t=10, b=40),
                        legend=dict(
                            orientation='v',
                            yanchor='top',
                            y=0.99,
                            xanchor='left',
                            x=1.01,
                            font=dict(color='#000000', size=12),
                            bgcolor='rgba(255,255,255,0.95)',
                            bordercolor='#e5e7eb',
                            borderwidth=1,
                            tracegroupgap=4
                        ),
                        xaxis=dict(
                            title='일자',
                            showgrid=True, 
                            gridcolor='#e2e8f0', 
                            tickfont=dict(color='black', size=10), 
                            side='bottom'
                        ),
                        yaxis=dict(
                            showgrid=True, 
                            gridcolor='#e2e8f0', 
                            tickformat=',', 
                            tickfont=dict(color='black', size=10), 
                            rangemode='tozero'
                        ),
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig_level_daily, use_container_width=True)
                    
                    st.markdown('<div style="margin:20px 0;"></div>', unsafe_allow_html=True)
                    
                    # ===== 섹션 5: 당월 일단위 상세 테이블 =====
                    st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">📊 당월 일단위 상세 데이터</div>', unsafe_allow_html=True)
                    
                    df_level_display = df_level_current[['일자_전체', '일차'] + level_columns].copy()
                    df_level_display.columns = ['날짜', '일차'] + [f"레벨 {col}" for col in level_columns]
                    
                    st.dataframe(
                        df_level_display.sort_values('일차', ascending=True),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("📊 당월 일단위 데이터가 없습니다.")
            else:
                st.info("📊 해당 월의 데이터가 없습니다.")

    # ========== TAB 3: 아이템 매출 상세 ==========
    with tab3:
        st.markdown(f'<div style="background:{BRAND_COLOR}; color:white; padding:12px; border-radius:6px; font-weight:600; margin:20px 0 15px;">📋 아이템 매출 상세</div>', unsafe_allow_html=True)
        
        if df_items_m3 is None or df_items_m3.empty:
            st.error("❌ 아이템 데이터를 불러올 수 없습니다.")
        else:
            # 현재 월 데이터 필터링
            target_month = f"{c_year}{c_month:02d}"
            filtered_df = df_items_m3[df_items_m3['일자'].astype(str).str.strip().str[:6] == target_month].copy()
            
            if filtered_df.empty:
                st.warning(f"📅 {c_year}-{c_month:02d}에 해당하는 데이터가 없습니다.")
            else:
                # 필요한 컬럼만 선택
                display_df = filtered_df[['아이템', '합계_고유계정수', '합계_구매횟수', '합계_순매출']].copy()
                
                # 아이템명 정리 (뒤의 ID 제거)
                display_df['아이템명'] = display_df['아이템'].apply(lambda x: re.sub(r'\s+\(\d+\)$', '', str(x).strip()))
                
                # 매출을 숫자로 변환하여 정렬
                display_df['합계_순매출_n'] = display_df['합계_순매출'].apply(to_num)
                display_df = display_df.sort_values('합계_순매출_n', ascending=False).reset_index(drop=True)
                
                # 상단 검색창
                st.markdown(f'<div style="background:#f8f9ff; padding:12px; border-radius:6px; margin-bottom:15px; font-size:13px; color:{BRAND_COLOR};"><b>🔍 아이템 검색</b></div>', unsafe_allow_html=True)
                search_term = st.text_input("", placeholder="아이템 이름을 입력하세요...", label_visibility="collapsed")
                
                # 검색 필터링
                if search_term:
                    filtered_display_df = display_df[
                        display_df['아이템명'].str.contains(search_term, case=False, na=False)
                    ].reset_index(drop=True)
                else:
                    filtered_display_df = display_df
                
                # 표시용 데이터프레임 생성 (포맷팅)
                output_df = filtered_display_df.copy()
                output_df['고유 계정 수'] = output_df['합계_고유계정수'].apply(to_num).apply(lambda x: f"{int(x):,}")
                output_df['구매 횟수'] = output_df['합계_구매횟수'].apply(to_num).apply(lambda x: f"{int(x):,}")
                output_df['총 매출'] = output_df['합계_순매출'].apply(to_num).apply(lambda x: f"₩{int(x):,}")
                
                # 최종 표시 컬럼
                final_df = output_df[['아이템명', '고유 계정 수', '구매 횟수', '총 매출']].copy()
                
                if not final_df.empty:
                    # HTML 테이블로 렌더링
                    html_table_tab3 = f'<table style="width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1);"><thead><tr style="background:{HEADER_COLOR}; color:#ffffff;">'
                    html_table_tab3 += '<th style="padding:14px; text-align:center; font-weight:900; font-size:13px; border:none;">아이템명</th>'
                    html_table_tab3 += '<th style="padding:14px; text-align:center; font-weight:900; font-size:13px; border:none;">고유 계정 수</th>'
                    html_table_tab3 += '<th style="padding:14px; text-align:center; font-weight:900; font-size:13px; border:none;">구매 횟수</th>'
                    html_table_tab3 += '<th style="padding:14px; text-align:center; font-weight:900; font-size:13px; border:none;">총 매출</th>'
                    html_table_tab3 += '</tr></thead><tbody>'
                    
                    for idx, row in final_df.iterrows():
                        row_bg = '#ffffff' if idx % 2 == 0 else '#f8f9ff'
                        html_table_tab3 += f'<tr style="background:{row_bg}; border-bottom:1px solid #e5e7eb;"><td style="padding:12px; text-align:center; font-weight:600; color:#333;">{row["아이템명"]}</td><td style="padding:12px; text-align:center; font-weight:600; color:#333;">{row["고유 계정 수"]}</td><td style="padding:12px; text-align:center; font-weight:600; color:#333;">{row["구매 횟수"]}</td><td style="padding:12px; text-align:center; font-weight:700; color:{ACCENT_COLOR_RED};">{row["총 매출"]}</td></tr>'
                    
                    html_table_tab3 += '</tbody></table>'
                    
                    st.markdown(html_table_tab3, unsafe_allow_html=True)
                    
                    st.markdown('<div style="margin:15px 0;"></div>', unsafe_allow_html=True)
                    st.info(f"✅ 총 {len(final_df)}개 아이템 (매출 기준 정렬)")
                else:
                    st.warning("❌ 검색 결과가 없습니다.")


if __name__ == "__main__":
    print("src_m3_detail.py 구문 검사 OK")
