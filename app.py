import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from pypinyin import pinyin, Style
import re

# ==========================================
# 🛑 務必修改區
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kE47tRqR9YXT9C3Jn0nch4jKK8p4E6PqgFibhRcnNKA/edit?gid=0#gid=0"
# (⬆️ 請替換您的網址)

# --- 1. CSS 風格 ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Serif+TC:wght@400;700&display=swap');
    .stApp { background-color: #f8f5e6; font-family: 'Noto Serif TC', serif; }
    h1, h2, h3, .magic-font { font-family: 'Ma Shan Zheng', cursive; color: #740001; }
    
    section[data-testid="stSidebar"] { background-color: #262730; color: #ecf0f1; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { color: #f1c40f; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: bold; font-size: 1.1em; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span { color: #e0e0e0; }
    
    /* 下拉選單文字修正 */
    .stSelectbox div[data-baseweb="select"] div { color: #333333 !important; font-weight: bold; }
    
    /* 題目選項優化 */
    .stRadio label p { font-size: 20px !important; line-height: 1.15 !important; color: #2c2c2c !important; }
    .stRadio label { margin-bottom: 10px; }

    .progress-label { font-weight: bold; color: #ffffff !important; margin-bottom: -5px; margin-top: 10px; }
    
    .stButton>button { 
        color: #d3a625; background-color: #740001; border: 2px solid #d3a625; 
        font-weight: bold; border-radius: 8px; font-family: 'Noto Serif TC', serif; width: 100%;
    }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    
    .welcome-box {
        background-color: #fffbf0; border: 2px dashed #740001; padding: 30px; 
        text-align: center; border-radius: 15px; margin-bottom: 20px;
    }
    .stat-card {
        background-color: #fff; padding: 20px; border-radius: 10px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center;
    }
    .certificate-box { border: 5px double #d3a625; padding: 30px; background-color: #fffbf0; text-align: center; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .success-msg { padding:15px; background-color:#d4edda; color:#155724; border-left: 5px solid #28a745; font-weight:bold; font-size: 1.2em; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-left: 5px solid #dc3545; font-size: 1.2em;}
    .zhuyin { font-size: 0.9em; color: #555; font-family: sans-serif; }
</style>
""", unsafe_allow_html=True)

# --- 2. 工具函式 ---
def get_zhuyin(text):
    if not isinstance(text, str): return ""
    try:
        result = pinyin(text, style=Style.BOPOMOFO)
        return " ".join([item[0] for item in result])
    except: return ""

def is_valid_zhuyin(text):
    if not text or not isinstance(text, str): return False
    for char in text:
        if '\u4e00' <= char <= '\u9fa5': return False
    return True

# --- 3. Google Sheets 連線 ---
@st.cache_resource
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

def load_db_from_sheet():
    client = get_gsheet_client()
    if not client: return {}
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        all_values = sheet.get_all_values()
        if not all_values: return {}
        
        headers = all_values[0] 
        rows = all_values[1:]
        col_map = {h: i for i, h in enumerate(headers) if h.strip()}
        
        user_db = {}
        for row in rows:
            if 'Name' not in col_map: continue
            name_idx = col_map['Name']
            if name_idx >= len(row) or not row[name_idx]: continue
            name = str(row[name_idx]).strip()
            
            def get_val(col_name, default):
                if col_name not in col_map: return default
                idx = col_map[col_name]
                if idx < len(row) and row[idx] != "": return row[idx]
                return default

            stats_json = get_val('Subject_Stats', '{}')
            try: subject_stats = json.loads(stats_json)
            except: subject_stats = {}

            raw_pw = str(get_val('Password', ''))
            
            user_db[name] = {
                'password': raw_pw,
                'xp': int(get_val('XP', 0)),
                'hp': int(get_val('HP', 10)),
                'last_hp_time': float(get_val('Last_HP_Time', time.time())),
                'badges': str(get_val('Badges', '')).split(',') if get_val('Badges', '') else [],
                'wrong_list': eval(str(get_val('Wrong_List', '[]'))),
                'subject_stats': subject_stats
            }
        return user_db
    except Exception as e:
        if "404" in str(e):
            st.error("❌ 找不到試算表！請檢查程式碼第 15 行的 SHEET_URL。")
        else:
            st.error(f"⚠️ 讀取錯誤：{e}")
        return {}

def save_user_to_sheet(name, data):
    client = get_gsheet_client()
    if not client: return
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        stats_json = json.dumps(data['subject_stats'], ensure_ascii=False)
        pw_to_save = "'" + str(data['password'])
        row_data = [
            name, pw_to_save, data['xp'], data['hp'], data['last_hp_time'],
            ",".join(data['badges']), str(data['wrong_list']), stats_json
        ]
        try:
            name_list = sheet.col_values(1)
            if name in name_list:
                row_idx = name_list.index(name) + 1
                for i, val in enumerate(row_data):
                    sheet.update_cell(row_idx, i+1, val)
            else:
                sheet.append_row(row_data)
        except Exception as inner_e:
            st.warning(f"寫入錯誤: {inner_e}")
    except Exception as e:
        st.warning(f"連線錯誤: {e}")

# --- 4. Session State ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = load_db_from_sheet()
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'waiting_for_next' not in st.session_state:
    st.session_state.waiting_for_next = False
if 'current_q' not in st.session_state:
    st.session_state.current_q = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'show_cert' not in st.session_state:
    st.session_state.show_cert = False
if 'selected_subject' not in st.session_state:
    st.session_state.selected_subject = "全部學科"
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False

# --- 5. 資料與分類 ---
def sorting_hat(idiom_row):
    text = str(idiom_row['成語']) + str(idiom_row['解釋'])
    keywords = {
        "神奇動物保護": "龍虎豹狼狗犬雞猴猿馬牛羊豬鼠兔蛇鳥鶴鷹魚鳳凰鴉雀鴻鵠鱉龜麟獸蟬蠶象狐",
        "草藥學": "花草樹木林葉根種子果實荷柳桃李松柏",
        "天文學": "天日星辰月雲風雨雷電霜雪虹光影氣宇宙",
        "煉金術": "金銀銅鐵錫玉石珠寶劍刀槍弓鼎釜器皿",
        "算命學": "一二三四五六七八九十百千萬億數雙兩半倍",
        "黑魔法防禦術": "鬼魔死殺傷血痛毒惡害危險恐懼戰鬥兵甲",
        "飛行課": "飛騰雲駕霧跑走奔速快追逐",
        "變形學": "變改化形貌狀樣子假",
        "占卜學": "夢想吉凶禍福命運測知未卜",
        "現影術": "隱顯出入來去蹤跡",
        "魔藥學": "水酒湯藥毒飲",
        "麻瓜研究": "門戶家室衣食住行市井路途人情世故",
        "魔法史": "朝代春秋戰國古今世事書文言字語論典籍舊昔", 
    }
    for subject, keys in keywords.items():
        if any(k in text for k in keys): return subject
    return "符咒學"

@st.cache_data
def load_idioms():
    files = ['idioms.csv', '成語資料庫.xlsx - 工作表1 (2).csv', '成語資料庫.csv']
    df = None
    for f in files:
        try:
            df = pd.read_csv(f)
            break
        except: continue
    if df is None: return pd.DataFrame()
    
    df['例句'] = df['例句'].fillna('')
    if '近義詞' not in df.columns: df['近義詞'] = ''
    if '反義詞' not in df.columns: df['反義詞'] = ''
    df['近義詞'] = df['近義詞'].fillna('')
    df['反義詞'] = df['反義詞'].fillna('')
    df = df.dropna(subset=['成語', '解釋'])
    df['魔法學科'] = df.apply(sorting_hat, axis=1)
    return df

df = load_idioms()

LEVELS = {
    1: {"name": "一年級", "type": "def", "target": 90, "streak_req": 20, "desc": "解釋題"},
    2: {"name": "三年級", "type": "sent", "target": 70, "streak_req": 15, "desc": "例句題"},
    3: {"name": "五年級", "type": "fill", "target": 50, "streak_req": 10, "desc": "填空題"},
    4: {"name": "七年級", "type": "chal", "target": 50, "streak_req": 0, "desc": "挑戰題"}
}

def get_user_data():
    if st.session_state.current_user:
        return st.session_state.user_db.get(st.session_state.current_user)
    return None

def get_subject_stats(ud, subject):
    if 'subject_stats' not in ud: ud['subject_stats'] = {}
    if subject not in ud['subject_stats']:
        ud['subject_stats'][subject] = {'level': 1, 'level_correct': 0, 'streak': 0, 'max_streak': 0}
    return ud['subject_stats'][subject]

def update_subject_stats(ud, subject, new_stats):
    ud['subject_stats'][subject] = new_stats
    save_user_to_sheet(st.session_state.current_user, ud)

def register_user(name, password):
    if name in st.session_state.user_db:
        return False, "⚠️ 名字已被使用，請換一個。"
    if not (password.isdigit() and 4 <= len(password) <= 6):
        return False, "⚠️ 密碼格式錯誤 (請輸入 4-6 位數字)。"
    
    new_user = {
        'password': password,
        'xp': 0, 'hp': 10, 'last_hp_time': time.time(),
        'badges': [], 'wrong_list': [],
        'subject_stats': {} 
    }
    st.session_state.user_db[name] = new_user
    save_user_to_sheet(name, new_user)
    return True, "✅ 註冊成功！系統將自動整理，請稍候..."

def generate_question(subject):
    if df.empty: return None
    pool = df if subject == "全部學科" else df[df['魔法學科'] == subject]
    if pool.empty: pool = df
    
    ud = get_user_data()
    if subject == "全部學科":
        lvl = 1
        lvl_type = "def"
    else:
        stats = get_subject_stats(ud, subject)
        lvl = stats['level']
        lvl_type = LEVELS[lvl]['type']
    
    if lvl_type == 'sent': 
        pool = pool[pool['例句'] != '']
        if pool.empty: pool = df
        
    row = pool.sample(1).iloc[0]
    q = {'row': row, 'type': lvl_type, 'ans': row['成語'], 'options': [], 'level': lvl}
    
    db_zhuyin = str(row.get('注音', '')).strip()
    if is_valid_zhuyin(db_zhuyin):
        q['zhuyin'] = db_zhuyin
    else:
        q['zhuyin'] = get_zhuyin(row['成語'])
    
    if lvl_type == 'def':
        has_syn = '近義詞' in row and str(row['近義詞']).strip()
        has_ant = '反義詞' in row and str(row['反義詞']).strip()
        dice = random.randint(0, 100)
        
        if dice < 30 and has_syn:
            syns = str(row['近義詞']).replace('，', ',').split(',')
            target_syn = random.choice(syns).strip()
            q['text'] = f"🔄 **【近義詞】**：請找出與 **「{target_syn}」** 意思相近的成語："
            q['ans'] = row['成語']
        elif dice > 70 and has_ant:
            ants = str(row['反義詞']).replace('，', ',').split(',')
            target_ant = random.choice(ants).strip()
            q['text'] = f"⚡ **【反義詞】**：請找出與 **「{target_ant}」** 意思相反的成語："
            q['ans'] = row['成語']
        else:
            q['text'] = f"🔮 **【解釋】**：{row['解釋']}"
            q['ans'] = row['成語']

        opts = df[df['成語'] != row['成語']].sample(3)['成語'].tolist() + [row['成語']]
        random.shuffle(opts)
        q['options'] = opts

    elif lvl_type == 'sent':
        sent = row['例句'].replace(row['成語'], '______')
        q['text'] = f"📜 **【例句】**：{sent}"
        opts = df[df['成語'] != row['成語']].sample(3)['成語'].tolist() + [row['成語']]
        random.shuffle(opts)
        q['options'] = opts

    elif lvl_type == 'fill':
        chars = list(row['成語'])
        if len(chars) >= 4:
            mask = random.randint(0, 3)
            q['ans'] = chars[mask]
            chars[mask] = '❓'
            q['text'] = f"🧩 **【填空】**：{''.join(chars)}\n(提示：{row['解釋']})"
        else: return generate_question(subject)

    elif lvl_type == 'chal':
        q['text'] = f"🔥 **【終極挑戰】**：請寫出符合此解釋的成語\n{row['解釋']}"
        
    return q

# --- 6. 介面邏輯 ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏰 霍格華茲</h1>", unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.write("### 🧙‍♂️ 登入 / 註冊")
        tab_login, tab_reg = st.tabs(["登入", "註冊"])
        
        with tab_login:
            users = ["請選擇..."] + list(st.session_state.user_db.keys())
            login_name = st.selectbox("巫師姓名", users)
            login_pw = st.text_input("通關密語", type="password", key="l_pw")
            if st.button("進入學院"):
                if login_name != "請選擇..." and login_pw:
                    u_data = st.session_state.user_db.get(login_name)
                    if u_data and str(u_data['password']).replace("'", "") == str(login_pw):
                        st.session_state.current_user = login_name
                        st.session_state.is_logged_in = True
                        st.session_state.is_playing = False
                        st.toast(f"歡迎回來，{login_name}！")
                        st.rerun()
                    else:
                        st.error("密語錯誤！")
        
        with tab_reg:
            reg_name = st.text_input("設定姓名")
            reg_pw = st.text_input("設定密語 (4-6位數字)", type="password", key="r_pw")
            if st.button("申請入學"):
                if reg_name and reg_pw:
                    ok, msg = register_user(reg_name, reg_pw)
                    if ok:
                        st.success(msg)
                        st.session_state.user_db = load_db_from_sheet()
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(msg)
    
    else:
        ud = get_user_data()
        now = time.time()
        elapsed = now - ud['last_hp_time']
        rec = int(elapsed // 1800)
        if rec > 0 and ud['hp'] < 10:
            ud['hp'] = min(10, ud['hp'] + rec)
            ud['last_hp_time'] = now - (elapsed % 1800)
            save_user_to_sheet(st.session_state.current_user, ud)
            st.toast("體力已回復！")

        hp = ud['hp']
        st.markdown(f"## 🎓 {st.session_state.current_user}")
        st.markdown(f"<div style='font-size:20px; color:#c62828'>{'❤️'*hp}{'🤍'*(10-hp)}</div>", unsafe_allow_html=True)
        if hp < 10:
            mins = int((1800 - (elapsed % 1800)) // 60)
            st.caption(f"⏳ 下一點回復：約 {mins} 分鐘")
        else:
            st.caption("體力已滿")

        if st.button("登出"):
            st.session_state.is_logged_in = False
            st.session_state.current_user = None
            st.session_state.is_playing = False
            st.rerun()

        st.markdown("---")
        
        subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
        new_subject = st.selectbox("📚 選修課程", subjects, index=subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in subjects else 0)
        
        if new_subject != st.session_state.selected_subject:
            st.session_state.selected_subject = new_subject
            st.session_state.current_q = None
            st.session_state.waiting_for_next = False
            st.session_state.is_playing = False
            st.rerun()
            
        st.markdown("---")
        
        if st.session_state.selected_subject == "全部學科":
            st.warning("⚠️ 自由練習模式")
        else:
            s_stats = get_subject_stats(ud, st.session_state.selected_subject)
            lvl = s_stats['level']
            cfg = LEVELS[lvl]
            st.markdown(f"### 🎓 **{cfg['name']}**")
            st.caption(f"測驗內容：{cfg['desc']}")
            
            c_total = s_stats['level_correct']
            t_total = cfg['target']
            st.markdown(f"<p class='progress-label'>✅ 累積答對：{c_total} / {t_total}</p>", unsafe_allow_html=True)
            st.progress(min(1.0, c_total/t_total))
            
            req_streak = cfg['streak_req']
            if req_streak > 0:
                c_streak = s_stats['streak']
                st.markdown(f"<p class='progress-label'>🔥 連續答對：{c_streak} / {req_streak}</p>", unsafe_allow_html=True)
                st.progress(min(1.0, c_streak/req_streak))

# --- 7. 主畫面 ---
tab1, tab2, tab3 = st.tabs(["⚡ 咒語修練", "🏆 學院布告欄", "🔮 錯題儲思盆"])

if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'show_cert' not in st.session_state: st.session_state.show_cert = False

with tab1:
    if not st.session_state.is_logged_in:
        st.info("👈 請先在左側登入或註冊。")
    else:
        ud = get_user_data()
        subj = st.session_state.selected_subject
        
        if not st.session_state.is_playing:
            st.markdown(f"""
            <div class="welcome-box">
                <h1 class="magic-font">歡迎來到霍格華茲成語學院</h1>
                <h3>準備好開始今天的修練了嗎？</h3>
                <p>目前選修：<b>{subj}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="stat-card"><h4>總經驗值</h4><h2>✨ {}</h2></div>'.format(ud['xp']), unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="stat-card"><h4>擁有徽章</h4><h2>🏅 {}</h2></div>'.format(len(ud['badges'])), unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="stat-card"><h4>錯題待練</h4><h2>🔮 {}</h2></div>'.format(len(ud['wrong_list'])), unsafe_allow_html=True)
            
            st.write("")
            if st.button("🚀 開始上課", type="primary"):
                st.session_state.is_playing = True
                st.rerun()

        else:
            if st.session_state.show_cert:
                cert_type = st.session_state.get('cert_type')
                
                # ★★★ 新增：升級徽章邏輯 ★★★
                if cert_type == "level_up":
                    title, body, btn = "✨ 升級證書 ✨", f"恭喜 {st.session_state.current_user} 晉升！", "晉升"
                else:
                    title, body, btn = "🏆 宗師證書 🏆", f"恭喜成為 {subj} 大師！", "領取"
                
                st.markdown(f"""<div class="certificate-box"><div class="magic-font" style="font-size:3em;">{title}</div><p>{body}</p></div>""", unsafe_allow_html=True)
                if st.button(btn, use_container_width=True):
                    s_stats = get_subject_stats(ud, subj)
                    
                    if cert_type == "level_up":
                        # 頒發年級徽章
                        curr = s_stats['level']
                        new_badge = ""
                        if curr == 1: new_badge = "📜 初級咒語合格"
                        elif curr == 2: new_badge = "🦌 守護神召喚師"
                        elif curr == 3: new_badge = "🎓 O.W.L.s 傑出"
                        
                        if new_badge and new_badge not in ud['badges']:
                            ud['badges'].append(new_badge)
                            
                        s_stats['level'] += 1
                        s_stats['level_correct'] = 0
                        s_stats['streak'] = 0
                    else:
                        badge = f"{subj}大師"
                        if badge not in ud['badges']: ud['badges'].append(badge)
                    
                    update_subject_stats(ud, subj, s_stats)
                    st.session_state.show_cert = False
                    st.session_state.current_q = None
                    st.session_state.waiting_for_next = False
                    st.rerun()
            
            elif st.session_state.waiting_for_next and st.session_state.last_result:
                res = st.session_state.last_result
                row = res['row_data']
                
                if res['correct']:
                    st.markdown(f'<div class="success-msg">✨ 咒語生效！</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="error-box">💥 錯誤...<br><div class="correct-ans">正確答案：{res['ans']}</div></div>""", unsafe_allow_html=True)
                
                with st.expander("📖 查看成語詳解", expanded=True):
                    db_zhuyin = str(row.get('注音', '')).strip()
                    zhuyin_text = db_zhuyin if is_valid_zhuyin(db_zhuyin) else get_zhuyin(row['成語'])
                    
                    st.markdown(f"<h3 style='margin-bottom:0;'>{row['成語']} <span class='zhuyin'>{zhuyin_text}</span></h3>", unsafe_allow_html=True)
                    st.write(f"**解釋**：{row['解釋']}")
                    if row['例句']: st.write(f"**例句**：{row['例句']}")
                    c1, c2 = st.columns(2)
                    if row['近義詞']: c1.markdown(f"**近義詞**：`{row['近義詞']}`")
                    if row['反義詞']: c2.markdown(f"**反義詞**：`{row['反義詞']}`")
                
                st.write("---")
                if st.button("下一題 ➡️"):
                    st.session_state.last_result = None
                    st.session_state.current_q = None
                    st.session_state.waiting_for_next = False
                    st.rerun()

            else:
                if st.button("🔙 下課休息"):
                    st.session_state.is_playing = False
                    st.session_state.current_q = None
                    st.rerun()

                if ud['hp'] <= 0:
                    st.error("💀 體力耗盡！請休息一下。")
                else:
                    if st.session_state.current_q is None:
                        st.session_state.current_q = generate_question(subj)
                    q = st.session_state.current_q
                    
                    if q:
                        st.markdown(f"### {q['text']}")
                        
                        if q['type'] in ['fill', 'chal']:
                            with st.expander("💡 需要提示嗎？"):
                                if q['row']['近義詞']: st.write(f"近義詞：{q['row']['近義詞']}")
                                else: st.write("無提示")
                                if q['row']['反義詞']: st.write(f"反義詞：{q['row']['反義詞']}")

                        with st.form("ans"):
                            if q['type'] in ['def', 'sent']: 
                                ans = st.radio("選項：", q['options'])
                            elif q['type'] == 'fill': 
                                ans = st.text_input("填字：", max_chars=1)
                            elif q['type'] == 'chal': 
                                ans = st.text_input("成語：")
                            sub = st.form_submit_button("🪄 施法")
                        
                        if sub:
                            ud['hp'] -= 1
                            corr = False
                            if ans and ans.strip() == q['ans']:
                                corr = True
                                ud['hp'] += 1
                                ud['xp'] += 10
                                if subj != "全部學科":
                                    s_stats = get_subject_stats(ud, subj)
                                    s_stats['level_correct'] += 1
                                    s_stats['streak'] += 1
                                    if s_stats['streak'] > s_stats['max_streak']: s_stats['max_streak'] = s_stats['streak']
                                    
                                    # ★★★ 新增：連對30 徽章 ★★★
                                    if s_stats['streak'] == 30:
                                        streak_badge = "🔥 火閃電騎士"
                                        if streak_badge not in ud['badges']:
                                            ud['badges'].append(streak_badge)
                                            st.toast(f"🏅 獲得成就：{streak_badge}！")
                                            
                                    update_subject_stats(ud, subj, s_stats)
                                else:
                                    save_user_to_sheet(st.session_state.current_user, ud)
                            else:
                                if subj != "全部學科":
                                    s_stats = get_subject_stats(ud, subj)
                                    s_stats['streak'] = 0
                                    update_subject_stats(ud, subj, s_stats)
                                
                                found = False
                                for item in ud['wrong_list']:
                                    if item['成語'] == q['row']['成語']:
                                        item['count'] = item.get('count', 1) + 1
                                        item['誤答'] = ans 
                                        found = True
                                        break
                                if not found:
                                    ud['wrong_list'].append({'成語': q['row']['成語'], '誤答': ans, 'count': 1})

                                save_user_to_sheet(st.session_state.current_user, ud)
                            
                            st.session_state.last_result = {'correct': corr, 'ans': q['ans'], 'row_data': q['row']}
                            st.session_state.waiting_for_next = True
                            
                            if subj != "全部學科":
                                s_stats = get_subject_stats(ud, subj)
                                cfg = LEVELS[s_stats['level']]
                                if s_stats['level_correct'] >= cfg['target'] and s_stats['streak'] >= cfg['streak_req']:
                                    st.session_state.show_cert = True
                                    st.session_state.cert_type = "master" if s_stats['level'] == 4 else "level_up"
                                    st.session_state.waiting_for_next = False
                            st.rerun()

with tab2:
    st.markdown("### 🏆 霍格華茲風雲榜")
    if st.button("🔄 更新排名"):
        st.session_state.user_db = load_db_from_sheet()
        
    db = st.session_state.user_db
    if db:
        data = []
        for name, s in db.items():
            data.append({"巫師": name, "總XP": s['xp'], "徽章數": len(s['badges'])})
        df_rank = pd.DataFrame(data).sort_values("總XP", ascending=False)
        st.dataframe(df_rank, hide_index=True, use_container_width=True)

with tab3:
    if st.session_state.is_logged_in:
        ud = get_user_data()
        if ud['wrong_list']:
            display_list = []
            for w in ud['wrong_list']:
                display_list.append({
                    "成語": w['成語'],
                    "最近誤答": w['誤答'],
                    "錯誤次數": w.get('count', 1)
                })
            st.table(pd.DataFrame(display_list))
            if st.button("清除錯題"):
                ud['wrong_list'] = []
                save_user_to_sheet(st.session_state.current_user, ud)
                st.rerun()
        else: st.write("無錯題紀錄")
