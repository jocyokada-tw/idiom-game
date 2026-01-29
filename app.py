import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from pypinyin import pinyin, Style

# ==========================================
# 🛑 務必修改區：請填入您的 Google 試算表網址
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1kE47tRqR9YXT9C3Jn0nch4jKK8p4E6PqgFibhRcnNKA/edit?gid=0#gid=0"
# (⬆️ 請將上方 XXXXX... 換成您的真實網址！)

# --- 1. CSS 風格 ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Serif+TC:wght@400;700&display=swap');
    .stApp { background-color: #f8f5e6; font-family: 'Noto Serif TC', serif; }
    h1, h2, h3, .magic-font { font-family: 'Ma Shan Zheng', cursive; color: #740001; }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #262730; color: #ecf0f1; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { color: #f1c40f; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: bold; font-size: 1.1em; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span { color: #e0e0e0; }
    
    /* 進度條 */
    .progress-label { font-weight: bold; color: #ffffff !important; margin-bottom: -5px; margin-top: 10px; }
    
    /* 按鈕 */
    .stButton>button { 
        color: #d3a625; background-color: #740001; border: 2px solid #d3a625; 
        font-weight: bold; border-radius: 8px; font-family: 'Noto Serif TC', serif; width: 100%;
    }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    
    /* 訊息與卡片 */
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

            user_db[name] = {
                'password': str(get_val('Password', '')),
                'xp': int(get_val('XP', 0)),
                'hp': int(get_val('HP', 10)),
                'last_hp_time': float(get_val('Last_HP_Time', time.time())),
                'badges': str(get_val('Badges', '')).split(',') if get_val('Badges', '') else [],
                'wrong_list': eval(str(get_val('Wrong_List', '[]'))),
                'subject_stats': subject_stats
            }
        return user_db
        
    except Exception as e:
        # 這裡會捕捉 404 錯誤
        if "404" in str(e):
            st.error("❌ 找不到試算表！請檢查程式碼第 15 行的 SHEET_URL 是否正確。")
        else:
            st.error(f"⚠️ 讀取錯誤：{e}")
        return {}

def save_user_to_sheet(name, data):
    client = get_gsheet_client()
    if not client: return
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        stats_json = json.dumps(data['subject_stats'], ensure_ascii=False)
        row_data = [
            name,
            data['password'],
            data['xp'],
            data['hp'],
            data['last_hp_time'],
            ",".join(data['badges']),
            str(data['wrong_list']),
            stats_json
        ]
        
        try:
            cell = sheet.find(name)
            for i, val in enumerate(row_data):
                sheet.update_cell(cell.row, i+1, val)
        except gspread.exceptions.CellNotFound:
            sheet.append_row(row_data)
            
    except Exception as e:
        st.warning(f"存檔失敗: {e}")

# --- 4. 資料載入與分類 ---
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

# --- 5. Session State 初始化 ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = load_db_from_sheet()
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'waiting_for_next' not in st.session_state:
    st.session_state.waiting_for_next = False # 控制「下一題」按鈕狀態

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
    return True, "✅ 註冊成功！請至「登入」分頁使用新帳號登入。"

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
    q['zhuyin'] = get_zhuyin(row['成語'])
    
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

# --- 6. 介面邏輯 ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏰 霍格華茲</h1>", unsafe_allow_html=True)
    
    if not st.session_state.is_logged_in:
        st.write("### 🧙‍♂️ 登入 / 註冊")
        tab_login, tab_reg = st.tabs(["登入", "註冊"])
        
        with tab_login:
            # 重新從 DB 獲取名單，確保註冊後看得到
            users = ["請選擇..."] + list(st.session_state.user_db.keys())
            login_name = st.selectbox("巫師姓名", users)
            login_pw = st.text_input("通關密語", type="password", key="l_pw")
            if st.button("進入學院"):
                if login_name != "請選擇..." and login_pw:
                    u_data = st.session_state.user_db.get(login_name)
                    if u_data and str(u_data['password']) == str(login_pw):
                        st.session_state.current_user = login_name
                        st.session_state.is_logged_in = True
                        st.session_state.waiting_for_next = False
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
                    else:
                        st.error(msg)
    
    else:
        # 已登入
        ud = get_user_data()
        
        # 體力回復
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
        st.caption(f"HP: {hp}/10")
        if st.button("登出"):
            st.session_state.is_logged_in = False
            st.session_state.current_user = None
            st.rerun()

        st.markdown("---")
        
        subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
        if 'selected_subject' not in st.session_state: st.session_state.selected_subject = "全部學科"
        new_subject = st.selectbox("📚 選修課程", subjects, index=subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in subjects else 0)
        
        if new_subject != st.session_state.selected_subject:
            st.session_state.selected_subject = new_subject
            st.session_state.current_q = None
            st.session_state.waiting_for_next = False
            st.rerun()
            
        st.markdown("---")
        
        # 分科進度
        if st.session_state.selected_subject == "全部學科":
            st.warning("⚠️ 自由練習模式：不計入升級考核")
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
        
        # 狀態：顯示證書
        if st.session_state.show_cert:
            cert_type = st.session_state.get('cert_type')
            if cert_type == "level_up":
                title, body, btn = "✨ 升級證書 ✨", f"恭喜 {st.session_state.current_user} 晉升！", "晉升"
            else:
                title, body, btn = "🏆 宗師證書 🏆", f"恭喜成為 {subj} 大師！", "領取"
            
            st.markdown(f"""<div class="certificate-box"><div class="magic-font" style="font-size:3em;">{title}</div><p>{body}</p></div>""", unsafe_allow_html=True)
            if st.button(btn, use_container_width=True):
                s_stats = get_subject_stats(ud, subj)
                if cert_type == "level_up":
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
        
        # 狀態：等待下一題 (顯示結果卡)
        elif st.session_state.waiting_for_next and st.session_state.last_result:
            res = st.session_state.last_result
            row = res['row_data']
            
            if res['correct']:
                st.markdown(f'<div class="success-msg">✨ 咒語生效！</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="error-box">💥 錯誤...<br><div class="correct-ans">正確答案：{res['ans']}</div></div>""", unsafe_allow_html=True)
            
            with st.expander("📖 查看成語詳解", expanded=True):
                zhuyin_text = get_zhuyin(row['成語'])
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

        # 狀態：回答問題
        else:
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
                                update_subject_stats(ud, subj, s_stats)
                            else:
                                save_user_to_sheet(st.session_state.current_user, ud)
                        else:
                            if subj != "全部學科":
                                s_stats = get_subject_stats(ud, subj)
                                s_stats['streak'] = 0
                                update_subject_stats(ud, subj, s_stats)
                            
                            ud['wrong_list'].append({'成語': q['row']['成語'], '誤答': ans})
                            save_user_to_sheet(st.session_state.current_user, ud)
                        
                        st.session_state.last_result = {'correct': corr, 'ans': q['ans'], 'row_data': q['row']}
                        st.session_state.waiting_for_next = True # 進入等待下一題狀態
                        
                        # 檢查升級
                        if subj != "全部學科":
                            s_stats = get_subject_stats(ud, subj)
                            cfg = LEVELS[s_stats['level']]
                            if s_stats['level_correct'] >= cfg['target'] and s_stats['streak'] >= cfg['streak_req']:
                                st.session_state.show_cert = True
                                st.session_state.cert_type = "master" if s_stats['level'] == 4 else "level_up"
                                st.session_state.waiting_for_next = False # 如果升級，直接跳證書
                        
                        st.rerun()

with tab2:
    st.markdown("### 🏆 霍格華茲風雲榜")
    if st.button("🔄 更新排名"):
        st.session_state.user_db = load_db_from_sheet()
        
    db = st.session_state.user_db
    if db:
        data = []
        for name, s in db.items():
            total_level = 0
            if 'subject_stats' in s:
                for sub, stats in s['subject_stats'].items():
                    total_level += stats['level']
            data.append({"巫師": name, "總XP": s['xp'], "徽章數": len(s['badges'])})
        df_rank = pd.DataFrame(data).sort_values("總XP", ascending=False)
        st.dataframe(df_rank, hide_index=True, use_container_width=True)

with tab3:
    if st.session_state.is_logged_in:
        ud = get_user_data()
        if ud['wrong_list']:
            st.table(pd.DataFrame(ud['wrong_list']))
            if st.button("清除錯題"):
                ud['wrong_list'] = []
                save_user_to_sheet(st.session_state.current_user, ud)
                st.rerun()
        else: st.write("無錯題紀錄")
