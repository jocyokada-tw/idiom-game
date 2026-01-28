import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 設定：請將此網址換成你的 Google 試算表網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kE47tRqR9YXT9C3Jn0nch4jKK8p4E6PqgFibhRcnNKA/edit?gid=0#gid=0" 
# (記得替換上面這行！)

# --- 1. 設定與風格 ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Serif+TC:wght@400;700&display=swap');

    .stApp { background-color: #f8f5e6; font-family: 'Noto Serif TC', serif; }
    h1, h2, h3, .magic-font { font-family: 'Ma Shan Zheng', cursive; color: #740001; }
    
    /* 側邊欄樣式 */
    section[data-testid="stSidebar"] { background-color: #262730; color: #ecf0f1; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { color: #f1c40f; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: bold; font-size: 1.1em; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span { color: #e0e0e0; }
    .progress-label { font-weight: bold; color: #ffffff !important; margin-bottom: -5px; }

    /* 按鈕樣式 */
    .stButton>button { color: #d3a625; background-color: #740001; border: 2px solid #d3a625; font-weight: bold; border-radius: 8px; font-family: 'Noto Serif TC', serif; }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    
    /* 證書與訊息框 */
    .certificate-box { border: 5px double #d3a625; padding: 30px; background-color: #fffbf0; text-align: center; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .success-msg { padding:15px; background-color:#d4edda; color:#155724; border-left: 5px solid #28a745; font-weight:bold; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-left: 5px solid #dc3545; }
    .correct-ans { font-size: 1.5em; font-weight: bold; color: #c62828; margin-top: 5px; font-family: 'Ma Shan Zheng', cursive;}
</style>
""", unsafe_allow_html=True)

# --- 2. Google Sheets 連線管理 ---
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
        data = sheet.get_all_records()
        user_db = {}
        for row in data:
            name = str(row['Name'])
            # 兼容舊資料或空資料
            subj_data = row['Subject_Data']
            if isinstance(subj_data, str) and subj_data:
                parsed_subj = json.loads(subj_data.replace("'", '"')) # 簡易修正單引號
            else:
                parsed_subj = {}

            user_db[name] = {
                'password': str(row['Password']), # 新增密碼欄位
                'hp': int(row['HP']),
                'last_hp_time': float(row['Last_HP_Time']),
                'badges': row['Badges'].split(',') if row['Badges'] else [],
                'wrong_list': eval(row['Wrong_List']) if row['Wrong_List'] else [],
                'subject_data': parsed_subj # 核心改變：存放各科進度
            }
        return user_db
    except Exception as e:
        return {}

def save_user_to_sheet(name, stats):
    client = get_gsheet_client()
    if not client: return
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        row_data = [
            name, 
            stats['password'],
            stats['hp'], 
            stats['last_hp_time'],
            ",".join(stats['badges']), 
            str(stats['wrong_list']),
            json.dumps(stats['subject_data']) # 存成 JSON 字串
        ]
        cell = sheet.find(name)
        if cell:
            for col, val in enumerate(row_data, start=1):
                sheet.update_cell(cell.row, col, val)
        else:
            sheet.append_row(row_data)
    except Exception as e:
        st.warning(f"存檔失敗: {e}")

# --- 3. 基礎邏輯 ---
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
        "古代如尼文": "古舊昔史書文言字語論典籍",
        "占卜學": "夢想吉凶禍福命運測知未卜",
        "現影術": "隱顯出入來去蹤跡",
        "魔藥學": "水酒湯藥毒飲",
        "麻瓜研究": "門戶家室衣食住行市井路途人情世故",
        "魔法史": "朝代春秋戰國古今世事",
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

# --- 4. 初始化 Session State ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = load_db_from_sheet()

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def get_user_data():
    if st.session_state.current_user:
        return st.session_state.user_db.get(st.session_state.current_user)
    return None

# Helper: 取得特定科目的進度，若無則初始化
def get_subject_stats(user_data, subject):
    if subject not in user_data['subject_data']:
        user_data['subject_data'][subject] = {
            'level': 1, 'xp': 0, 'level_correct': 0, 'streak': 0, 'max_streak': 0
        }
    return user_data['subject_data'][subject]

def init_user_local(name, password):
    if name not in st.session_state.user_db:
        st.session_state.user_db = load_db_from_sheet()
        
    if name not in st.session_state.user_db:
        new_user = {
            'password': password,
            'hp': 10, 'last_hp_time': time.time(),
            'badges': [], 'wrong_list': [],
            'subject_data': {} # 初始化為空字典
        }
        st.session_state.user_db[name] = new_user
        save_user_to_sheet(name, new_user)
        return True
    return False

def sync_data():
    name = st.session_state.current_user
    if name and name in st.session_state.user_db:
        save_user_to_sheet(name, st.session_state.user_db[name])

# --- 5. 側邊欄：登入與狀態 ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏰 霍格華茲</h1>", unsafe_allow_html=True)
    
    # 登入/註冊區
    if not st.session_state.current_user:
        auth_mode = st.radio("入學手續", ["登入", "新生註冊"], horizontal=True)
        
        if auth_mode == "登入":
            existing_users = ["請選擇..."] + list(st.session_state.user_db.keys())
            login_name = st.selectbox("巫師姓名", existing_users)
            login_pwd = st.text_input("輸入密碼 (4-6位數字)", type="password", key="l_pwd")
            
            if st.button("進入學院"):
                if login_name != "請選擇...":
                    stored_pwd = st.session_state.user_db[login_name].get('password', '')
                    if login_pwd == stored_pwd:
                        st.session_state.current_user = login_name
                        st.session_state.current_q = None
                        st.toast(f"歡迎回來，{login_name}！")
                        st.rerun()
                    else:
                        st.error("密碼錯誤！")
        else: # 註冊
            reg_name = st.text_input("設定姓名")
            reg_pwd = st.text_input("設定密碼 (4-6位數字)", type="password", key="r_pwd", max_chars=6)
            
            if st.button("提交註冊"):
                if reg_name and len(reg_pwd) >= 4 and reg_pwd.isdigit():
                    if reg_name in st.session_state.user_db:
                        st.error("此名字已被註冊！")
                    else:
                        init_user_local(reg_name, reg_pwd)
                        st.session_state.current_user = reg_name
                        st.session_state.current_q = None
                        st.toast(f"註冊成功！歡迎 {reg_name} 入學。")
                        st.rerun()
                else:
                    st.warning("請輸入有效名字與 4-6 位數字密碼。")

    # 已登入狀態
    if st.session_state.current_user:
        if st.button("登出", type="secondary"):
            st.session_state.current_user = None
            st.rerun()
            
        ud = get_user_data()
        
        # 回血
        now = time.time()
        elapsed = now - ud['last_hp_time']
        rec = int(elapsed // 1800)
        if rec > 0 and ud['hp'] < 10:
            ud['hp'] = min(10, ud['hp'] + rec)
            ud['last_hp_time'] = now - (elapsed % 1800)
            sync_data()
            st.toast("體力已回復！")

        hp = ud['hp']
        st.markdown(f"## 🎓 {st.session_state.current_user}")
        st.markdown(f"<div style='font-size:20px; color:#c62828'>{'❤️'*hp}{'🤍'*(10-hp)}</div>", unsafe_allow_html=True)
        st.caption(f"HP: {hp}/10")
        st.markdown("---")
        
        # 選課系統
        subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
        if 'selected_subject' not in st.session_state: st.session_state.selected_subject = "全部學科"
        new_subject = st.selectbox("📚 選修課程", subjects, index=subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in subjects else 0)
        
        if new_subject != st.session_state.selected_subject:
            st.session_state.selected_subject = new_subject
            st.session_state.current_q = None
            st.rerun()
            
        st.markdown("---")
        
        # ★★★ 核心改變：讀取該科目的進度 ★★★
        curr_subj = st.session_state.selected_subject
        # 如果選全部學科，暫時顯示綜合等級或預設等級1，這裡簡化為顯示「綜合練習」不顯示詳細條，或預設符咒學
        if curr_subj == "全部學科":
            st.info("🔮 自由練習模式 (不計入特定學科進度)")
        else:
            subj_stats = get_subject_stats(ud, curr_subj)
            lvl = subj_stats['level']
            cfg = LEVELS[lvl]
            
            st.markdown(f"### 🎓 **{cfg['name']}**")
            st.caption(f"測驗內容：{cfg['desc']}")
            
            # 進度條
            c_total = subj_stats['level_correct']
            t_total = cfg['target']
            st.markdown(f"<p class='progress-label'>✅ 累積答對：{c_total} / {t_total}</p>", unsafe_allow_html=True)
            st.progress(min(1.0, c_total/t_total))
            
            req_streak = cfg['streak_req']
            if req_streak > 0:
                c_streak = subj_stats['streak']
                st.markdown(f"<p class='progress-label'>🔥 連續答對：{c_streak} / {req_streak}</p>", unsafe_allow_html=True)
                st.progress(min(1.0, c_streak/req_streak))
            else:
                st.info("🔥 此等級只需累積題數！")

# --- 6. 主程式 ---
def generate_question(subject):
    if df.empty: return None
    pool = df if subject == "全部學科" else df[df['魔法學科'] == subject]
    if pool.empty: pool = df
    
    # 取得當前等級 (從該科目)
    ud = get_user_data()
    if subject == "全部學科":
        lvl = 1 # 練習模式預設
    else:
        lvl = get_subject_stats(ud, subject)['level']
        
    lvl_type = LEVELS[lvl]['type']
    
    if lvl_type == 'sent': 
        pool = pool[pool['例句'] != '']
        if pool.empty: pool = df
        
    row = pool.sample(1).iloc[0]
    q = {'row': row, 'type': lvl_type, 'ans': row['成語'], 'options': []}
    
    if lvl_type == 'def':
        q['text'] = f"🔮 **【解釋】**：{row['解釋']}"
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

tab1, tab2, tab3 = st.tabs(["⚡ 咒語修練", "🏆 學院布告欄", "🔮 錯題儲思盆"])

if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'show_cert' not in st.session_state: st.session_state.show_cert = False

with tab1:
    if not st.session_state.current_user:
        st.info("👈 請在左側進行登入或註冊。")
    else:
        ud = get_user_data()
        
        # 證書系統 (需指定科目)
        if st.session_state.show_cert:
            cert_type = st.session_state.get('cert_type')
            subj = st.session_state.selected_subject
            
            if cert_type == "level_up":
                title, body, btn = "✨ 升級證書 ✨", f"恭喜 {st.session_state.current_user} 在 {subj} 晉升！", "晉升"
            else:
                title, body, btn = "🏆 宗師證書 🏆", f"恭喜成為 {subj} 大師！", "領取"
            
            st.markdown(f"""<div class="certificate-box"><div class="magic-font" style="font-size:3em;">{title}</div><p>{body}</p></div>""", unsafe_allow_html=True)
            if st.button(btn, use_container_width=True):
                # 更新該科進度
                s_stats = get_subject_stats(ud, subj)
                if cert_type == "level_up":
                    s_stats['level'] += 1
                    s_stats['level_correct'] = 0
                    s_stats['streak'] = 0
                else:
                    badge = f"{subj}大師"
                    if badge not in ud['badges']: ud['badges'].append(badge)
                
                sync_data()
                st.session_state.show_cert = False
                st.session_state.current_q = None
                st.rerun()
        
        else:
            if st.session_state.last_result:
                res = st.session_state.last_result
                if res['correct']:
                    st.markdown(f'<div class="success-msg">✨ 咒語生效！</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="error-box">💥 錯誤...<br><div class="correct-ans">正確答案：{res['ans']}</div></div>""", unsafe_allow_html=True)
                st.session_state.last_result = None

            if ud['hp'] <= 0:
                st.error("💀 體力耗盡！")
            else:
                curr_subj = st.session_state.selected_subject
                if st.session_state.current_q is None:
                    st.session_state.current_q = generate_question(curr_subj)
                q = st.session_state.current_q
                
                if q:
                    st.markdown(f"### {q['text']}")
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
                        
                        # 處理各科數據
                        if curr_subj != "全部學科":
                            s_stats = get_subject_stats(ud, curr_subj)
                        
                        if ans and ans.strip() == q['ans']:
                            corr = True
                            ud['hp'] += 1
                            
                            if curr_subj != "全部學科":
                                s_stats['xp'] += 10
                                s_stats['level_correct'] += 1
                                s_stats['streak'] += 1
                                if s_stats['streak'] > s_stats['max_streak']: s_stats['max_streak'] = s_stats['streak']
                        else:
                            if curr_subj != "全部學科":
                                s_stats['streak'] = 0
                            ud['wrong_list'].append({'成語': q['row']['成語'], '誤答': ans})
                        
                        sync_data()
                        st.session_state.last_result = {'correct': corr, 'ans': q['ans']}
                        
                        # 檢查升級 (僅限特定學科模式)
                        if curr_subj != "全部學科":
                            cfg = LEVELS[s_stats['level']]
                            if s_stats['level_correct'] >= cfg['target'] and s_stats['streak'] >= cfg['streak_req']:
                                st.session_state.show_cert = True
                                st.session_state.cert_type = "master" if s_stats['level'] == 4 else "level_up"
                        
                        st.session_state.current_q = None
                        st.rerun()

with tab2:
    st.markdown("### 🏆 霍格華茲風雲榜 (總積分)")
    if st.button("🔄 更新排名"):
        st.session_state.user_db = load_db_from_sheet()
        
    db = st.session_state.user_db
    if db:
        data = []
        for name, s in db.items():
            # 計算該名巫師所有學科的總 XP
            total_xp = sum([subj['xp'] for subj in s['subject_data'].values()])
            data.append({"巫師": name, "總 XP": total_xp, "徽章數": len(s['badges'])})
        df_rank = pd.DataFrame(data).sort_values("總 XP", ascending=False)
        st.dataframe(df_rank, hide_index=True, use_container_width=True)

with tab3:
    if st.session_state.current_user:
        ud = get_user_data()
        if ud['wrong_list']:
            st.table(pd.DataFrame(ud['wrong_list']))
            if st.button("清除"):
                ud['wrong_list'] = []
                sync_data()
                st.rerun()
        else: st.write("無錯題紀錄")
