import streamlit as st
import pandas as pd
import os
import re
import json
import bcrypt
import time
from datetime import datetime, timedelta

USERS_DIR = "users"
USERS_FILE = os.path.join(USERS_DIR, "allowed_users.json")

# 첫 관리자 생성 (한 번만 실행)
if not os.path.exists(USERS_FILE):
    os.makedirs(USERS_DIR, exist_ok=True)
    users_manager.add_user("admin", "admin123", "관리자", "관리자")
    print("✅ 첫 관리자 계정 생성됨")

# ============ 해시 기반 보안 함수 ============

def hash_password(password):
    """비밀번호를 bcrypt로 해시"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(password, hashed):
    """비밀번호와 해시 비교"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        return False

def is_account_locked(user_id):
    """계정이 잠금 상태인지 확인"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    if user_id in st.session_state.login_attempts:
        attempt_info = st.session_state.login_attempts[user_id]
        max_attempts = 5
        lockout_duration = 300
        
        if attempt_info['count'] >= max_attempts:
            lockout_time = attempt_info['last_attempt'] + timedelta(seconds=lockout_duration)
            if datetime.now() < lockout_time:
                return True, (lockout_time - datetime.now()).seconds
    return False, 0

def record_failed_login(user_id):
    """실패한 로그인 기록"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    if user_id not in st.session_state.login_attempts:
        st.session_state.login_attempts[user_id] = {'count': 0, 'last_attempt': datetime.now()}
    
    st.session_state.login_attempts[user_id]['count'] += 1
    st.session_state.login_attempts[user_id]['last_attempt'] = datetime.now()

def reset_login_attempts(user_id):
    """로그인 시도 초기화"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    
    if user_id in st.session_state.login_attempts:
        del st.session_state.login_attempts[user_id]

# ============ 로그인 설정 ============

# 작업 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, 'users')
USERS_FILE = os.path.join(USERS_DIR, 'allowed_users.json')

class UsersManager:
    def __init__(self):
        self.file_path = USERS_FILE
        os.makedirs(USERS_DIR, exist_ok=True)
    
    def load(self):
        """파일에서 사용자 정보 로드"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('users', {})
        except Exception as e:
            print(f"파일 읽기 오류: {e}")
        return {}
    
    def save(self, users):
        """파일에 사용자 정보 저장"""
        try:
            os.makedirs(USERS_DIR, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({'users': users}, f, ensure_ascii=False, indent=2)
            print(f"✅ 저장 완료: {self.file_path}")
        except Exception as e:
            print(f"❌ 저장 오류: {e}")
    
    def get_users(self):
        """사용자 정보 반환"""
        return self.load()
    
    def add_user(self, user_id, password, name, position):
        """새 사용자 추가 (비밀번호 해시)"""
        users = self.load()
        if user_id not in users:
            users[user_id] = {
                "password": hash_password(password),  # 해시 적용
                "name": name,
                "position": position,
                "first_login": True
            }
            self.save(users)
            return True
        return False
    
    def update_user(self, user_id, **kwargs):
        """사용자 정보 업데이트 (비밀번호 해시)"""
        users = self.load()
        if user_id in users:
            # 비밀번호가 포함되면 해시
            if 'password' in kwargs:
                kwargs['password'] = hash_password(kwargs['password'])
            users[user_id].update(kwargs)
            self.save(users)
            return True
        return False
    
    def delete_user(self, user_id):
        """사용자 삭제"""
        users = self.load()
        if user_id in users and user_id != "admin":
            del users[user_id]
            self.save(users)
            return True
        return False

# 사용자 관리자 초기화
users_manager = UsersManager()

ADMIN_ID = "admin"
ADMIN_PASSWORD_HASH = hash_password("admin123")  # 관리자 비밀번호 해시

# 브랜드 컬러
BRAND_COLOR = "#3a3f47"
BRAND_COLOR_LIGHT = "#4a5058"

# 세션 상태 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.session_state.user_position = None
    st.session_state.show_password_change = False
    st.session_state.is_admin = False
    st.session_state.show_admin = False

# ============ 비밀번호 변경 팝업 ============
def show_password_change_modal():
    """비밀번호 변경 모달"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="margin-top:50px; padding:30px; background:#ffffff; border-radius:12px; border:2px solid #3a3f47; text-align:center;">
            <h2 style="color:#333; margin-bottom:10px; line-height:1.4;">🔐 새 비밀번호<br>설정</h2>
            <p style="color:#666; font-size:14px; margin-bottom:30px;">
                첫 로그인입니다.<br>
                새로운 비밀번호를 설정해주세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        new_password = st.text_input("새 비밀번호", type="password", key="new_pwd1")
        confirm_password = st.text_input("비밀번호 확인", type="password", key="new_pwd2")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("취소", use_container_width=True):
                st.session_state.show_password_change = False
                st.rerun()
        
        with col_b:
            if st.button("변경", use_container_width=True, type="primary"):
                if not new_password:
                    st.error("새 비밀번호를 입력하세요")
                elif new_password != confirm_password:
                    st.error("비밀번호가 일치하지 않습니다")
                elif len(new_password) < 4:
                    st.error("비밀번호는 4자 이상이어야 합니다")
                else:
                    # 비밀번호 변경 저장 (자동 해시됨)
                    users_manager.update_user(
                        st.session_state.user_id,
                        password=new_password,
                        first_login=False
                    )
                    st.success("✅ 비밀번호가 변경되었습니다!")
                    st.session_state.show_password_change = False
                    st.rerun()

# ============ 관리자 페이지 ============
def admin_page():
    """관리자 비밀번호 관리 페이지"""
    st.set_page_config(page_title="관리자 페이지", layout="wide")
    
    # 상단 뒤로가기 버튼
    col_spacer, col_logout = st.columns([11, 1])
    with col_logout:
        if st.button("◀", key="admin_back"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.rerun()
    
    st.title("🛠️ 관리자 페이지")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👥 사용자 관리")
        
        # 사용자 목록
        st.markdown("#### 등록된 사용자")
        user_data = []
        for uid, info in users_manager.get_users().items():
            user_data.append({
                "사번": uid,
                "이름": info['name'],
                "직급": info.get('position', '-'),
                "상태": "🔓 첫로그인" if info.get('first_login', False) else "🔐 정상"
            })
        
        if user_data:
            df_users = pd.DataFrame(user_data)
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 사용자 추가
        st.markdown("#### 새 사용자 추가")
        new_user_id = st.text_input("사번", key="new_uid")
        new_user_name = st.text_input("이름", key="new_name")
        new_user_position = st.text_input("직급", key="new_pos")
        new_user_password = st.text_input("초기 비밀번호", type="password", key="new_pwd")
        
        if st.button("추가", use_container_width=True, type="primary"):
            if not new_user_id or not new_user_name or not new_user_position or not new_user_password:
                st.error("모든 항목을 입력하세요")
            elif new_user_id in users_manager.get_users():
                st.error("이미 존재하는 사번입니다")
            elif len(new_user_password) < 4:
                st.error("비밀번호는 4자 이상이어야 합니다")
            else:
                if users_manager.add_user(new_user_id, new_user_password, new_user_name, new_user_position):
                    st.success(f"✅ {new_user_name}({new_user_id})이 추가되었습니다")
                    st.rerun()
                else:
                    st.error("사용자 추가에 실패했습니다")
    
    with col2:
        st.markdown("### 🔑 사용자 관리")
        
        # 탭으로 구분
        tab1, tab2 = st.tabs(["비밀번호 초기화", "사용자 삭제"])
        
        with tab1:
            st.write("사용자의 비밀번호를 초기화합니다. 초기화 후 첫 로그인 시 비밀번호 변경을 요구합니다.")
            st.markdown("---")
            
            users = users_manager.get_users()
            if users:
                user_options = {f"{uid} - {info['name']} ({info.get('position', '-')})": uid for uid, info in users.items() if uid != ADMIN_ID}
                
                if user_options:
                    selected_user = st.selectbox("사용자 선택", options=user_options.keys(), key="reset_user")
                    reset_user_id = user_options[selected_user]
                    
                    st.warning(f"⚠️ {selected_user}의 비밀번호를 초기화하시겠습니까?")
                    st.write(f"초기화 후 비밀번호: **{reset_user_id}** (사번과 동일)")
                    
                    if st.button("비밀번호 초기화", use_container_width=True, type="primary", key="reset_btn"):
                        # 비밀번호 초기화 (자동 해시됨)
                        users_manager.update_user(
                            reset_user_id,
                            password=reset_user_id,
                            first_login=True
                        )
                        st.success(f"✅ {selected_user}의 비밀번호가 초기화되었습니다\n초기 비밀번호: {reset_user_id}")
                        st.rerun()
                else:
                    st.info("초기화할 사용자가 없습니다")
        
        with tab2:
            st.write("선택한 사용자를 시스템에서 삭제합니다. (관리자는 삭제할 수 없습니다)")
            st.markdown("---")
            
            users = users_manager.get_users()
            if users:
                user_options = {f"{uid} - {info['name']} ({info.get('position', '-')})": uid for uid, info in users.items() if uid != ADMIN_ID}
                
                if user_options:
                    selected_user = st.selectbox("사용자 선택", options=user_options.keys(), key="delete_user")
                    delete_user_id = user_options[selected_user]
                    
                    st.error(f"⚠️ {selected_user}를 삭제하시겠습니까?")
                    st.write("**⚠️ 주의: 이 작업은 되돌릴 수 없습니다.**")
                    
                    # 확인 체크박스
                    confirm = st.checkbox(f"'{selected_user}'을(를) 삭제하겠습니다.", key="delete_confirm")
                    
                    if confirm:
                        if st.button("삭제", use_container_width=True, type="primary", key="delete_btn"):
                            if users_manager.delete_user(delete_user_id):
                                st.success(f"✅ {selected_user}가 삭제되었습니다")
                                st.rerun()
                            else:
                                st.error("사용자 삭제에 실패했습니다")
                else:
                    st.info("삭제할 사용자가 없습니다")

# ============ 로그인 페이지 ============
if not st.session_state.authenticated:
    st.set_page_config(page_title="전기아이피 종합 매출 리포트 - 로그인", layout="centered", initial_sidebar_state="collapsed")
    
    # 사이드바 숨기기
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none}
    </style>
    """, unsafe_allow_html=True)
    
    # 로그인 페이지 스타일 (가운데 정렬 + 관리자 버튼 우측 상단)
    st.markdown("""
    <style>
        .stApp {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        
        .main .block-container {
            width: 100%;
            max-width: 500px !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 0 !important;
        }
        
        .admin-btn {
            position: fixed;
            top: 20px;
            right: 30px;
            z-index: 999;
        }
        
        .admin-btn button {
            width: 45px;
            height: 45px;
            padding: 0 !important;
            border-radius: 8px;
            background-color: rgba(58, 63, 71, 0.4) !important;
            color: rgba(58, 63, 71, 0.9) !important;
            border: 1.5px solid rgba(58, 63, 71, 0.6) !important;
            font-size: 20px !important;
            transition: all 0.3s ease !important;
        }
        
        .admin-btn button:hover {
            background-color: rgba(58, 63, 71, 0.6) !important;
            border-color: rgba(58, 63, 71, 0.8) !important;
            transform: scale(1.05);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 관리자 버튼 (우측 상단)
    st.markdown('<div class="admin-btn">', unsafe_allow_html=True)
    if st.button("⚙️", key="admin_btn_main", help="관리자"):
        st.session_state.show_admin = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 관리자 로그인
    if st.session_state.show_admin:
        st.markdown("""
        <div style="text-align:center; margin-bottom:40px;">
            <h1 style="font-size:36px; margin:0; color:#ffffff; font-weight:900;">🛠️ 관리자 로그인</h1>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            admin_id = st.text_input("관리자 사번", placeholder="admin")
            admin_password = st.text_input("관리자 비밀번호", type="password", placeholder="비밀번호")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("뒤로가기", use_container_width=True):
                    st.session_state.show_admin = False
                    st.rerun()
            
            with col_b:
                if st.button("로그인", use_container_width=True, type="primary"):
                    if admin_id == ADMIN_ID and verify_password(admin_password, ADMIN_PASSWORD_HASH):
                        st.session_state.authenticated = True
                        st.session_state.is_admin = True
                        st.session_state.user_id = admin_id
                        st.session_state.user_name = "관리자"
                        st.rerun()
                    else:
                        st.error("❌ 관리자 사번 또는 비밀번호가 잘못되었습니다")
        st.stop()
    
    # 일반 사용자 로그인
    st.markdown("""
    <div style="text-align:center; margin-bottom:50px;">
        <h1 style="font-size:52px; margin:0; color:#ffffff; font-weight:900; line-height:1.3;">전기아이피<br>종합 매출 리포트</h1>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔑 로그인")
        
        user_id = st.text_input("사번", placeholder="사번 입력")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
        
        if st.button("로그인", use_container_width=True, type="primary"):
            # 계정 잠금 확인
            locked, remaining_time = is_account_locked(user_id)
            if locked:
                st.error(f"❌ 계정이 잠겼습니다. {remaining_time}초 후 다시 시도하세요.")
            else:
                users = users_manager.get_users()
                if user_id in users and verify_password(password, users[user_id]['password']):
                    # 로그인 성공
                    reset_login_attempts(user_id)
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.user_name = users[user_id]['name']
                    st.session_state.user_position = users[user_id].get('position', '')
                    
                    # 첫 로그인이면 비밀번호 변경 요청
                    if users[user_id].get('first_login', False):
                        st.session_state.show_password_change = True
                    
                    st.rerun()
                else:
                    # 로그인 실패
                    record_failed_login(user_id)
                    st.error("❌ 사번 또는 비밀번호가 잘못되었습니다")
    
    st.stop()

# ============ 비밀번호 변경 필요시 표시 ============
if st.session_state.show_password_change:
    st.set_page_config(page_title="비밀번호 변경", layout="centered")
    show_password_change_modal()
    st.stop()

# ============ 관리자 페이지 ============
if st.session_state.get('is_admin', False):
    admin_page()
    st.stop()

# ============ 이 아래부터 인증된 일반 사용자만 접근 가능 ============

# 페이지 설정
st.set_page_config(page_title="WEMADE MIR 통합 대시보드", layout="wide", initial_sidebar_state="expanded")

# 유틸리티 함수
def hex_to_rgba(hex_str, opacity=0.15):
    hex_str = hex_str.lstrip('#')
    r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def format_val(val): 
    try: return f"₩{float(val):,.0f}"
    except: return "₩0"

def get_colored_html(val, is_pct=False, is_rev=False):
    if val > 0: cls, sign = "inc", "▲ "
    elif val < 0: cls, sign = "dec", "▼ "
    else: cls, sign = "", ""
    txt = f"{abs(val):.1f}%" if is_pct else (f"₩{abs(val):,.0f}" if is_rev else f"{abs(val):,.0f}")
    return f'<span class="{cls}">{sign}{txt}</span>'

def clean_item_name(name): 
    return re.sub(r'\s*\(\d+\)', '', str(name)).strip()

def safe_read_csv(file_path):
    for enc in ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']:
        try: 
            df = pd.read_csv(file_path, encoding=enc)
            return df
        except: continue
    return None

def load_data(directory, prefix):
    if not os.path.exists(directory): return None
    files = [f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith('.csv')]
    dfs = []
    for f in files:
        df = safe_read_csv(os.path.join(directory, f))
        if df is not None: dfs.append(df)
    if not dfs: return None
    combined = pd.concat(dfs, ignore_index=True)
    combined['일자'] = combined['일자'].astype(str).str.strip().str.replace('.0', '', regex=False)
    return combined

MIR_RED = "#dc2626" 

# CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    
    .stApp {{ background-color: #e5e7eb !important; font-family: 'Noto Sans KR', sans-serif; }}
    
    /* 사이드바 펼치기 버튼 스타일 */
    button[kind="header"] {{
        background-color: {BRAND_COLOR} !important;
        color: #ffffff !important;
        border: 2px solid {BRAND_COLOR} !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
    }}
    
    button[kind="header"] > svg {{
        fill: #ffffff !important;
        stroke: #ffffff !important;
    }}
    
    [data-testid="stSidebarCollapseButton"] {{
        background-color: {BRAND_COLOR} !important !important;
        border: 2px solid {BRAND_COLOR} !important !important;
    }}
    
    [data-testid="stSidebarCollapseButton"] svg {{
        fill: #ffffff !important !important;
        stroke: #ffffff !important !important;
    }}

    header[data-testid="stHeader"] {{ background-color: rgba(0,0,0,0) !important; border-bottom: none !important; }}
    .main .block-container {{ max-width: 1200px !important; margin: 0 auto !important; padding-top: 0.5rem !important; }}
    h1 {{ margin-top: -1.0rem !important; padding-bottom: 1rem !important; color: #000000 !important; font-weight: 900 !important; }}

    [data-testid="stSidebar"] h3 {{
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        margin-top: 10px !important;
        margin-bottom: -5px !important;
    }}

    div[data-baseweb="select"] > div {{ background-color: #ffffff !important; color: #000000 !important; border-radius: 4px !important; }}
    
    div[data-testid="stRadio"] > div {{
        gap: 15px !important;
    }}
    div[data-testid="stRadio"] label p {{
        font-size: 16px !important;
        font-weight: 400 !important;
        color: #ffffff !important;
    }}

    [data-testid="stSidebar"] {{ background-color: {BRAND_COLOR} !important; }}
    .sidebar-brand {{ font-size: 24px !important; color: #ffffff !important; font-weight: 900 !important; margin-bottom: 8px !important; text-align: center; display: block; }}
    
    .sidebar-welcome {{ 
        font-size: 16px !important;
        color: #ffffff !important;
        text-align: center !important;
        margin-bottom: 15px !important;
        margin-top: 0 !important;
        line-height: 1.3 !important;
    }}
    .sidebar-welcome b {{ 
        font-weight: 900 !important;
        display: inline !important;
    }}
    
    .section-title {{ font-size: 22px; border-left: 8px solid {BRAND_COLOR}; padding-left: 15px; margin: 40px 0 15px 0 !important; color: #000000 !important; font-weight: 900 !important; }}
    .dark-header-box {{ background-color: #cbd5e1 !important; padding: 10px 15px !important; border-radius: 8px 8px 0 0 !important; text-align: center !important; border: 1px solid #94a3b8; border-bottom: none; }}
    .dark-header-box h3 {{ color: #000000 !important; font-weight: 800 !important; margin: 0 !important; font-size: 17px !important; }}

    .styled-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; background-color: #ffffff !important; }}
    .styled-table th {{ background-color: #cbd5e1; color: #000000 !important; font-weight: 800; padding: 12px; border: 1px solid #94a3b8; text-align: center; }}
    .styled-table td {{ padding: 12px; text-align: center; border: 1px solid #94a3b8; font-size: 15px; color: #000000 !important; font-weight: 700; }}
    
    .analysis-header {{ background-color: {BRAND_COLOR} !important; color: #ffffff !important; padding: 12px 20px; border-radius: 8px 8px 0 0; font-weight: 800; font-size: 16px; margin-top: 20px; }}
    .analysis-body {{ background-color: #ffffff; padding: 20px; border: 1px solid #94a3b8; border-top: none; border-radius: 0 0 8px 8px; display: flex; gap: 20px; }}
    .analysis-col {{ flex: 1; }}
    .col-label {{ color: #000000 !important; font-weight: 900; font-size: 14px; margin-bottom: 8px; }}
    .col-content {{ color: #334155; font-size: 14px; line-height: 1.6; background: #f8fafc; padding: 12px; border-radius: 5px; min-height: 80px; border: 1px solid #e2e8f0; }}
    
    .inc {{ color: #e11d48 !important; font-weight: 900; }}
    .dec {{ color: #2563eb !important; font-weight: 900; }}
    [data-testid="stTabs"] [role="tablist"] button {{ color: #000000 !important; }}
    [data-testid="stTabs"] [role="tablist"] button:hover {{ color: #000000 !important; }}
    [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"] {{ color: #000000 !important; }}
    </style>
    """, unsafe_allow_html=True)

# 데이터 로드
DATA_DIR = "data"
df_sum_m2 = load_data(DATA_DIR, "summary_m2_")
df_sum_m3 = load_data(DATA_DIR, "summary_m3_")
df_items_m2 = load_data(DATA_DIR, "items_m2_")
df_items_m3 = load_data(DATA_DIR, "items_m3_")
df_met_m2 = load_data(DATA_DIR, "metrics_m2_")
df_met_m3 = load_data(DATA_DIR, "metrics_m3_")

all_dates = []
for d in [df_sum_m2, df_sum_m3]:
    if d is not None: all_dates.extend(d['일자'].unique())

if not all_dates:
    st.warning("데이터 파일을 찾을 수 없습니다.")
    st.stop()

opts = sorted(list(set([f"{d[:4]}_{d[4:]}" for d in all_dates if len(d) >= 6])), reverse=True)

# 사이드바
with st.sidebar:
    st.markdown('<span class="sidebar-brand">전기아이피</span>', unsafe_allow_html=True)
    st.markdown(f'<p class="sidebar-welcome"><b>{st.session_state.user_name} {st.session_state.user_position}</b>님, 환영합니다.</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📅 분석 기간") 
    
    # 2026년 01월부터만 필터링
    filtered_opts = [o for o in opts if int(o.split('_')[0]) >= 2026]
    
    if not filtered_opts:
        st.warning("2026년 이후의 데이터가 없습니다.")
        st.stop()
    
    sel_label = st.selectbox("", options=[f"{o.split('_')[0]}년 {o.split('_')[1]}월" for o in filtered_opts], label_visibility="collapsed")
    c_d = filtered_opts[[f"{o.split('_')[0]}년 {o.split('_')[1]}월" for o in filtered_opts].index(sel_label)].replace('_', '')
    c_month, c_year = int(c_d[4:]), int(c_d[:4])
    p_d = f"{c_year-1}12" if c_month == 1 else f"{c_year}{c_month-1:02d}"
    l_d = str(int(c_d) - 100)
    
    st.markdown("---")
    st.markdown("### 📋 리포트 종류") 
    menu = st.radio("", ["미르의전설2/3 종합 리포트", "미르의전설2 상세", "미르의전설3 상세"], label_visibility="collapsed")
    
    st.markdown("---")
    
    if st.button("🔑 비밀번호 변경", use_container_width=True):
        st.session_state.show_password_change = True
        st.rerun()
    
    if st.button("🔓 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.user_position = None
        st.rerun()

# 메인 화면
if menu == "미르의전설2 상세":
    st.title("미르의전설2 상세 리포트")
elif menu == "미르의전설3 상세":
    st.title("미르의전설3 상세 리포트")
else:
    st.title(f"{menu}")

# src_summary 임포트
import sys
sys.path.insert(0, os.path.dirname(__file__))
import importlib

# 메뉴에 따라 다른 모듈 호출
if menu == "미르의전설2/3 종합 리포트":
    import src_summary
    importlib.reload(src_summary)
    src_summary.show(
        menu=menu,
        c_d=c_d,
        c_month=c_month,
        c_year=c_year,
        p_d=p_d,
        l_d=l_d,
        df_sum_m2=df_sum_m2,
        df_sum_m3=df_sum_m3,
        df_items_m2=df_items_m2,
        df_items_m3=df_items_m3,
        df_met_m2=df_met_m2,
        df_met_m3=df_met_m3,
        format_val=format_val,
        get_colored_html=get_colored_html,
        hex_to_rgba=hex_to_rgba,
        clean_item_name=clean_item_name
    )

elif menu == "미르의전설2 상세":
    import src_m2_detail
    importlib.reload(src_m2_detail)
    src_m2_detail.show(
        year=c_year,
        month=c_month,
        df_sum_m2=df_sum_m2,
        df_items_m2=df_items_m2,
        df_metrics_m2=df_met_m2,
        hex_to_rgba=hex_to_rgba,
        clean_item_name=clean_item_name
    )

elif menu == "미르의전설3 상세":
    import src_m3_detail
    importlib.reload(src_m3_detail)
    src_m3_detail.show(
        year=c_year,
        month=c_month,
        df_sum_m3=df_sum_m3,
        df_items_m3=df_items_m3,
        df_metrics_m3=df_met_m3,
        hex_to_rgba=hex_to_rgba,
        clean_item_name=clean_item_name
    )
