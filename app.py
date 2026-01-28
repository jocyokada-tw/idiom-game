import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# --- 1. 設定與風格 (CSS & Fonts) ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

# 引入 Ma Shan Zheng 字體 (Google Fonts) 作為書法風格替代，因為芫荽字體若無本地安裝無法在網頁顯示
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Serif+TC:wght@400;700&display=swap');

    /* 全局設定 */
    .stApp { 
        background-color: #f8f5e6; 
        font-family: 'Noto Serif TC', serif; 
    }
    
    /* 標題與魔法文字體 */
    h1, h2, h3, .magic-font { 
        font-family: 'Ma Shan Zheng', cursive; 
        color: #740001; 
    }
    
    /* --- 側邊欄樣式 (深色背景 + 淺色字) --- */
    section[data-testid="stSidebar"] {
        background-color: #262730;
        color: #ecf0f1;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #f1c40f; /* 金黃色標題 */
    }
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] div, 
    section[data-testid="stSidebar"] label {
        color: #ecf0f1; /* 淺灰白內文 */
    }
    
    /* 按鈕樣式 */
    .stButton>button { 
        color: #d3a625; 
        background-color: #740001; 
        border: 2px solid #d3a625; 
        font-weight: bold; 
        border-radius: 8px;
        font-family: 'Noto Serif TC', serif;
    }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    
    /* 證書樣式 */
    .certificate-box {
        border: 5px double #d3a625;
        padding: 30px;
        background-color: #fffbf0;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* 訊息框 */
    .success-msg { padding:15px; background-color:#d4edda; color:#155724; border-left: 5px solid #28a745; font-weight:bold; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-left: 5px solid #dc3545; }
    .correct-ans { font-size: 1.5em; font-weight: bold; color: #c62828; margin-top: 5px; font-family: 'Ma Shan Zheng', cursive;}
</style>
""", unsafe_allow_html=True)

# --- 2. 魔法分類帽演算法 ---
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
        if any(k in text for k in keys):
            return subject
    return "符咒學" # 預設分類

# --- 3. 資料處理 ---
@st.cache_data
def load_data():
    files = ['idioms.csv', '成語資料庫.xlsx - 工作表1 (2).csv', '成語資料庫.csv']
    df = None
    for f in files:
        try:
            df = pd.read_csv(f)
            break
        except: continue
    
    if df is None:
        st.error("⚠️ 找不到資料庫檔案。")
        return pd.DataFrame()
        
    df['例句'] = df['例句'].fillna('')
    df = df.dropna(subset=['成語', '解釋'])
    df['魔法學科'] = df.apply(sorting_hat, axis=1)
    return df

df = load_data()

# --- 4. 遊戲狀態與使用者管理 ---

LEVELS = {
    1: {"name": "一年級", "type": "def", "target": 90, "streak_req": 20, "desc": "解釋題"},
    2: {"name": "三年級", "type": "sent", "target": 70, "streak_req": 15, "desc": "例句題"},
    3: {"name": "五年級", "type": "fill", "target": 50, "streak_req": 10, "desc": "填空題"},
    4: {"name": "七年級", "type": "chal", "target": 50, "streak_req": 0, "desc": "挑戰題"}
}

# 多使用者資料庫 (模擬)
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# 初始化單一使用者結構
def init_user(name):
    if name not in st.session_state.user_db:
        st.session_state.user_db[name] = {
            'level': 1,
            'xp': 0,
            'hp': 10,
            'last_hp_time': time.time(),
            'level_correct': 0,
            'streak': 0,
            'max_streak': 0,
            'badges': [],
            'history': [],
            'wrong_list': []
        }

# 取得當前使用者資料的 Helper
def get_user_data():
    name = st.session_state.current_user
    if name:
        return st.session_state.user_db[name]
    return None

# 體力回復邏輯 (針對當前使用者)
def recover_hp_logic():
    ud = get_user_data()
    if ud:
        now = time.time()
        elapsed = now - ud['last_hp_time']
        rec = int(elapsed // 1800) # 30分鐘
        if rec > 0:
            if ud['hp'] < 10:
                ud['hp'] = min(10, ud['hp'] + rec)
                st.toast(f"💖 {st.session_state.current_user} 的體力回復了！")
            ud['last_hp_time'] = now - (elapsed % 1800)

# --- 5. 側邊欄：登入與狀態 ---

with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🏰 霍格華茲</h1>", unsafe_allow_html=True)
    
    # 使用者切換
    input_name = st.text_input("巫師姓名 (輸入後按 Enter)", placeholder="請輸入名字...")
    if input_name:
        clean_name = input_name.strip()
        if clean_name:
            if st.session_state.current_user != clean_name:
                init_user(clean_name)
                st.session_state.current_user = clean_name
                st.session_state.current_q = None # 切換人要重置題目
                st.rerun()

    # 如果已登入
    if st.session_state.current_user:
        ud = st.session_state.user_db[st.session_state.current_user]
        recover_hp_logic() # 檢查回血
        
        st.markdown(f"### 🧙‍♂️ {st.session_state.current_user}")
        
        # 體力顯示
        hp = ud['hp']
        hearts = "❤️" * hp + "🤍" * (10 - hp)
        st.markdown(f"<div style='font-size:20px;'>{hearts}</div>", unsafe_allow_html=True)
        st.caption(f"生命值: {hp}/10 (每30分回復1點)")
        
        st.markdown("---")
        
        # 選課系統
        subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
        
        # 初始化選課狀態
        if 'selected_subject' not in st.session_state:
            st.session_state.selected_subject = "全部學科"
            
        new_subject = st.selectbox("📚 選擇選修課程", subjects, index=subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in subjects else 0)
        
        # 偵測學科切換 -> 重置題目
        if new_subject != st.session_state.selected_subject:
            st.session_state.selected_subject = new_subject
            st.session_state.current_q = None
            st.rerun()
            
        st.markdown("---")
        
        # 進度
        lvl = ud['level']
        cfg = LEVELS[lvl]
        st.write(f"🎓 **{cfg['name']}** ({cfg['desc']})")
        
        # 進度條
        c_total = ud['level_correct']
        t_total = cfg['target']
        st.write(f"✅ 累積答對：{c_total}/{t_total}")
        st.progress(min(1.0, c_total/t_total))
        
        if cfg['streak_req'] > 0:
            c_streak = ud['streak']
            t_streak = cfg['streak_req']
            st.write(f"🔥 連續答對：{c_streak}/{t_streak}")
            st.progress(min(1.0, c_streak/t_streak))
            
    else:
        st.info("請先輸入姓名以開始入學。")
        st.stop() # 未登入則停止渲染主畫面

# --- 6. 題目生成邏輯 ---

def generate_question(subject):
    if df.empty: return None
    
    pool = df
    if subject != "全部學科":
        pool = df[df['魔法學科'] == subject]
        if pool.empty:
            pool = df # Fallback
            
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
            q['full'] = row['成語']
        else: return generate_question(subject)
    elif lvl_type == 'chal':
        q['text'] = f"🔥 **【終極挑戰】**：請寫出符合此解釋的成語\n{row['解釋']}"
        
    return q

# --- 7. 主畫面 ---

# 分頁
tab1, tab2, tab3 = st.tabs(["⚡ 咒語修練", "🏆 學院布告欄", "🔮 錯題儲思盆"])

if 'last_result' not in st.session_state: st.session_state.last_result = None
if 'show_cert' not in st.session_state: st.session_state.show_cert = False

# [Tab 1] 遊戲區
with tab1:
    ud = get_user_data()
    
    # 顯示證書
    if st.session_state.show_cert:
        cert_type = st.session_state.get('cert_type')
        if cert_type == "level_up":
            title = "✨ 升級證書 ✨"
            body = f"恭喜 {st.session_state.current_user} 通過 {LEVELS[ud['level']]['name']} 考驗！"
            btn = "晉升下一年級"
        else:
            title = "🏆 宗師證書 🏆"
            body = f"恭喜 {st.session_state.current_user} 成為 {st.session_state.selected_subject} 大師！"
            btn = "領取徽章"
            
        st.markdown(f"""<div class="certificate-box"><div class="magic-font" style="font-size:3em; color:#740001;">{title}</div><p style="font-size:1.5em;">{body}</p></div>""", unsafe_allow_html=True)
        
        if st.button(btn, use_container_width=True):
            if cert_type == "level_up":
                ud['level'] += 1
                ud['level_correct'] = 0
                ud['streak'] = 0
            else: # master
                badge = f"{st.session_state.selected_subject}大師"
                if badge not in ud['badges']: ud['badges'].append(badge)
                ud['level_correct'] = 0 # 重置七年級進度或保留皆可
                
            st.session_state.show_cert = False
            st.session_state.current_q = None
            st.rerun()

    else:
        # 回饋顯示區
        if st.session_state.last_result:
            res = st.session_state.last_result
            if res['correct']:
                st.markdown(f'<div class="success-msg">✨ 咒語生效！ (體力維持)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="error-box">
                    💥 魔杖逆火... (體力 -1)<br>
                    題目：{res['q_text']}<br>
                    <div class="correct-ans">正確答案：{res['ans']}</div>
                </div>
                """, unsafe_allow_html=True)
            st.session_state.last_result = None

        # 體力檢查
        if ud['hp'] <= 0:
            st.error("💀 體力耗盡！請休息一下。")
        else:
            # 題目生成
            if st.session_state.current_q is None:
                st.session_state.current_q = generate_question(st.session_state.selected_subject)
            
            q = st.session_state.current_q
            if q:
                st.markdown(f"### {q['text']}")
                
                with st.form("game_form"):
                    if q['type'] in ['def', 'sent']:
                        ans = st.radio("選擇：", q['options'])
                    elif q['type'] == 'fill':
                        ans = st.text_input("輸入缺字：", max_chars=1)
                    elif q['type'] == 'chal':
                        ans = st.text_input("輸入成語：")
                    
                    submitted = st.form_submit_button("🪄 施法 (消耗1體力)")
                    
                if submitted:
                    ud['hp'] -= 1
                    is_correct = False
                    if ans:
                        if ans.strip() == q['ans']:
                            is_correct = True
                            ud['hp'] += 1 # 補回
                            ud['xp'] += 10
                            ud['level_correct'] += 1
                            ud['streak'] += 1
                            if ud['streak'] > ud['max_streak']: ud['max_streak'] = ud['streak']
                        else:
                            ud['streak'] = 0
                            ud['wrong_list'].append({'成語': q['row']['成語'], '錯誤答案': ans})
                    
                    # 記錄回饋
                    st.session_state.last_result = {
                        'correct': is_correct,
                        'ans': q['ans'],
                        'q_text': q['row']['解釋'] if q['type'] == 'chal' else q['row']['成語']
                    }
                    
                    # 檢查升級
                    cfg = LEVELS[ud['level']]
                    if ud['level_correct'] >= cfg['target'] and ud['streak'] >= cfg['streak_req']:
                        st.session_state.show_cert = True
                        st.session_state.cert_type = "master" if ud['level'] == 4 else "level_up"
                    
                    st.session_state.current_q = None
                    st.rerun()

# [Tab 2] 排名
with tab2:
    st.markdown("<h2 class='magic-font'>🏆 霍格華茲風雲榜</h2>", unsafe_allow_html=True)
    if st.session_state.user_db:
        data = []
        for name, stats in st.session_state.user_db.items():
            data.append({
                "巫師": name,
                "年級": LEVELS[stats['level']]['name'],
                "總經驗 (XP)": stats['xp'],
                "最高連對": stats['max_streak'],
                "徽章數": len(stats['badges'])
            })
        rank_df = pd.DataFrame(data).sort_values(by="總經驗 (XP)", ascending=False)
        st.dataframe(rank_df, use_container_width=True, hide_index=True)
    else:
        st.write("目前還沒有學生入學。")

# [Tab 3] 錯題
with tab3:
    ud = get_user_data()
    if ud['wrong_list']:
        st.table(pd.DataFrame(ud['wrong_list']))
        if st.button("清空儲思盆"):
            ud['wrong_list'] = []
            st.rerun()
    else:
        st.write("你的儲思盆很乾淨！")
