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
# (請替換上面這行！)

# --- 1. 設定與風格 ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Serif+TC:wght@400;700&display=swap');
    .stApp { background-color: #f8f5e6; font-family: 'Noto Serif TC', serif; }
    h1, h2, h3, .magic-font { font-family: 'Ma Shan Zheng', cursive; color: #740001; }
    section[data-testid="stSidebar"] { background-color: #262730; color: #ecf0f1; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { color: #f1c40f; }
    .stButton>button { color: #d3a625; background-color: #740001; border: 2px solid #d3a625; font-weight: bold; border-radius: 8px; font-family: 'Noto Serif TC', serif; }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    .certificate-box { border: 5px double #d3a625; padding: 30px; background-color: #fffbf0; text-align: center; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .success-msg { padding:15px; background-color:#d4edda; color:#155724; border-left: 5px solid #28a745; font-weight:bold; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-left: 5px solid #dc3545; }
    .correct-ans { font-size: 1.5em; font-weight: bold; color: #c62828; margin-top: 5px; font-family: 'Ma Shan Zheng', cursive;}
</style>
""", unsafe_allow_html=True)

# --- 2. Google Sheets 連線管理 ---
@st.cache_resource
def get_gsheet_client():
    # 從 Secrets 讀取憑證
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"連線失敗，請檢查 Secrets 設定: {e}")
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
            # 資料轉換：字串轉回列表或數字
            user_db[name] = {
                'level': int(row['Level']),
                'xp': int(row['XP']),
                'hp': int(row['HP']),
                'last_hp_time': float(row['Last_HP_Time']),
                'level_correct': int(row['Level_Correct']),
                'streak': int(row['Streak']),
                'max_streak': int(row['Max_Streak']),
                'badges': row['Badges'].split(',') if row['Badges'] else [],
                'wrong_list': eval(row['Wrong_List']) if row['Wrong_List'] else []
            }
        return user_db
    except Exception as e:
        # 如果是新表可能是空的，回傳空字典
        return {}

def save_user_to_sheet(name, stats):
    client = get_gsheet_client()
    if not client: return
    
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        # 準備要寫入的資料
        row_data = [
            name,
            stats['level'],
            stats['xp'],
            stats['hp'],
            stats['last_hp_time'],
            stats['level_correct'],
            stats['streak'],
            stats['max_streak'],
            ",".join(stats['badges']),
            str(stats['wrong_list'])
        ]
        
        # 檢查使用者是否已存在
        cell = sheet.find(name)
        if cell:
            # 更新現有列 (row)
            # 注意：gspread 的 row 是從 1 開始，且我們標題是第一列，所以不用特別修正
            for col, val in enumerate(row_data, start=1):
                sheet.update_cell(cell.row, col, val)
        else:
            # 新增一列
            sheet.append_row(row_data)
            
    except Exception as e:
        st.warning(f"存檔失敗 (網路可能不穩): {e}")

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
    st.session_state.user_db = load_db_from_sheet() # 啟動時讀取雲端

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def get_user_data():
    if st.session_state.current_user:
        return st.session_state.user_db.get(st.session_state.current_user)
    return None

def init_user_local(name):
    # 先看記憶體有沒有，沒有看雲端，再沒有就新建
    if name not in st.session_state.user_db:
        # 重新從雲端拉一次確保最新
        st.session_state.user_db = load_db_from_sheet()
        
    if name not in st.session_state.user_db:
        new_user = {
            'level': 1, 'xp': 0, 'hp': 10, 'last_hp_time': time.time(),
            'level_correct': 0, 'streak': 0, 'max_streak': 0,
            'badges': [], 'wrong_list': []
        }
        st.session_state.user_db[name] = new_user
        save_user_to_sheet(name, new_user) # 立即存檔

def sync_data():
    """將當前使用者的資料寫入雲端"""
    name = st.session_state.current_user
    if name and name in st.session_state.user_db:
        save_user_to_sheet(name, st.session_state.user_db[name])

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏰 霍格華茲</h1>", unsafe_allow_html=True)
    
    input_name = st.text_input("巫師姓名 (輸入後按 Enter)", placeholder="請輸入名字...")
    if input_name:
        clean_name = input_name.strip()
        if clean_name and st.session_state.current_user != clean_name:
            init_user_local(clean_name)
            st.session_state.current_user = clean_name
            st.session_state.current_q = None
            st.toast(f"歡迎回來，{clean_name}！資料已同步。")
            st.rerun()

    if st.session_state.current_user:
        ud = get_user_data()
        
        # 回血邏輯
        now = time.time()
        elapsed = now - ud['last_hp_time']
        rec = int(elapsed // 1800)
        if rec > 0 and ud['hp'] < 10:
            ud['hp'] = min(10, ud['hp'] + rec)
            ud['last_hp_time'] = now - (elapsed % 1800)
            sync_data() # 狀態改變，存檔
            st.toast("體力已回復！")

        hp = ud['hp']
        st.markdown(f"### 🧙‍♂️ {st.session_state.current_user}")
        st.markdown(f"<div style='font-size:20px; color:#c62828'>{'❤️'*hp}{'🤍'*(10-hp)}</div>", unsafe_allow_html=True)
        st.caption(f"HP: {hp}/10")
        
        st.markdown("---")
        
        subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
        if 'selected_subject' not in st.session_state: st.session_state.selected_subject = "全部學科"
        new_subject = st.selectbox("📚 選修課程", subjects, index=subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in subjects else 0)
        
        if new_subject != st.session_state.selected_subject:
            st.session_state.selected_subject = new_subject
            st.session_state.current_q = None
            st.rerun()
            
        st.markdown("---")
        lvl = ud['level']
        cfg = LEVELS[lvl]
        st.write(f"🎓 **{cfg['name']}**")
        st.progress(min(1.0, ud['level_correct']/cfg['target']))
        if cfg['streak_req'] > 0:
            st.write(f"🔥 連對: {ud['streak']}/{cfg['streak_req']}")

# --- 6. 主程式 ---
def generate_question(subject):
    if df.empty: return None
    pool = df if subject == "全部學科" else df[df['魔法學科'] == subject]
    if pool.empty: pool = df
    
    ud = get_user_data()
    lvl_type = LEVELS[ud['level']]['type']
    
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
        st.info("請先在左側輸入姓名入學。")
    else:
        ud = get_user_data()
        
        # 證書顯示
        if st.session_state.show_cert:
            cert_type = st.session_state.get('cert_type')
            if cert_type == "level_up":
                title, body, btn = "✨ 升級證書 ✨", f"恭喜 {st.session_state.current_user} 晉升！", "晉升"
            else:
                title, body, btn = "🏆 宗師證書 🏆", f"恭喜成為 {st.session_state.selected_subject} 大師！", "領取"
            
            st.markdown(f"""<div class="certificate-box"><div class="magic-font" style="font-size:3em;">{title}</div><p>{body}</p></div>""", unsafe_allow_html=True)
            if st.button(btn, use_container_width=True):
                if cert_type == "level_up":
                    ud['level'] += 1
                    ud['level_correct'] = 0
                    ud['streak'] = 0
                else:
                    badge = f"{st.session_state.selected_subject}大師"
                    if badge not in ud['badges']: ud['badges'].append(badge)
                sync_data() # 重要：存檔
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
                if st.session_state.current_q is None:
                    st.session_state.current_q = generate_question(st.session_state.selected_subject)
                q = st.session_state.current_q
                
                if q:
                    st.markdown(f"### {q['text']}")
                    with st.form("ans"):
                        if q['type'] in ['def', 'sent']: ans = st.radio("選：", q['options'])
                        elif q['type'] == 'fill': ans = st.text_input("填字：", max_chars=1)
                        elif q['type'] == 'chal': ans = st.text_input("成語：")
                        sub = st.form_submit_button("🪄 施法")
                    
                    if sub:
                        ud['hp'] -= 1
                        corr = False
                        if ans and ans.strip() == q['ans']:
                            corr = True
                            ud['hp'] += 1
                            ud['xp'] += 10
                            ud['level_correct'] += 1
                            ud['streak'] += 1
                            if ud['streak'] > ud['max_streak']: ud['max_streak'] = ud['streak']
                        else:
                            ud['streak'] = 0
                            ud['wrong_list'].append({'成語': q['row']['成語'], '誤答': ans})
                        
                        sync_data() # 重要：每次作答都存檔
                        st.session_state.last_result = {'correct': corr, 'ans': q['ans']}
                        
                        cfg = LEVELS[ud['level']]
                        if ud['level_correct'] >= cfg['target'] and ud['streak'] >= cfg['streak_req']:
                            st.session_state.show_cert = True
                            st.session_state.cert_type = "master" if ud['level'] == 4 else "level_up"
                        
                        st.session_state.current_q = None
                        st.rerun()

with tab2: # 排名
    st.markdown("### 🏆 霍格華茲風雲榜")
    # 重新讀取確保排名最新
    if st.button("🔄 更新排名"):
        st.session_state.user_db = load_db_from_sheet()
        
    db = st.session_state.user_db
    if db:
        data = []
        for name, s in db.items():
            data.append({"巫師": name, "等級": LEVELS[s['level']]['name'], "XP": s['xp'], "徽章": len(s['badges'])})
        df_rank = pd.DataFrame(data).sort_values("XP", ascending=False)
        st.dataframe(df_rank, hide_index=True, use_container_width=True)

with tab3: # 錯題
    if st.session_state.current_user:
        ud = get_user_data()
        if ud['wrong_list']:
            st.table(pd.DataFrame(ud['wrong_list']))
            if st.button("清除"):
                ud['wrong_list'] = []
                sync_data()
                st.rerun()
        else: st.write("無錯題紀錄")
