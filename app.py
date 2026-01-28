import streamlit as st
import pandas as pd
import random

# --- 1. 設定與風格 (Configuration & Theming) ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="⚡", layout="wide")

# 哈利波特風格 CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8f5e6; 
        color: #2c2c2c;
        font-family: "Garamond", "Times New Roman", serif;
    }
    h1, h2, h3 { color: #740001; font-weight: bold; }
    .stButton>button {
        color: #d3a625; background-color: #740001;
        border-radius: 10px; border: 2px solid #d3a625; font-weight: bold;
    }
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    .stProgress > div > div > div > div { background-color: #d3a625; }
    section[data-testid="stSidebar"] { background-color: #1a1a1a; color: #f0f0f0; }
    .success-msg { color: #2e7d32; font-weight: bold; font-size: 1.2em; }
    .error-msg { color: #c62828; font-weight: bold; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)

# --- 2. 資料載入 (Data Loading) ---
@st.cache_data
def load_data():
    # 注意：這裡預設讀取 'idioms.csv'，請確保GitHub上的檔名一致
    possible_files = ['idioms.csv', '成語資料庫.xlsx - 工作表1 (2).csv', '成語資料庫.csv']
    
    df = None
    for f in possible_files:
        try:
            df = pd.read_csv(f)
            break
        except FileNotFoundError:
            continue
            
    if df is None:
        st.error("⚠️ 找不到資料庫檔案！請確認 CSV 檔案已上傳至 GitHub 且檔名正確 (建議改為 idioms.csv)。")
        return pd.DataFrame()

    # 資料清理
    if '例句' in df.columns:
        df['例句'] = df['例句'].fillna('')
    df = df.dropna(subset=['成語', '解釋'])
    return df

df = load_data()

# --- 3. 遊戲邏輯 (Game Logic) ---
if 'xp' not in st.session_state:
    st.session_state.xp = 0
    st.session_state.level = 1
    st.session_state.house = "葛來分多"
    st.session_state.history = []
    st.session_state.wrong_questions = []
    st.session_state.badges = []
    st.session_state.current_q = None
    st.session_state.user_answered = False

LEVEL_CONFIG = {
    1: {"name": "一年級：魔法石 (解釋題)", "type": "def", "xp_req": 0},
    2: {"name": "三年級：阿茲卡班 (例句題)", "type": "sent", "xp_req": 100},
    3: {"name": "五年級：鳳凰會 (填空題)", "type": "fill", "xp_req": 300},
    4: {"name": "七年級：死神的聖物 (挑戰題)", "type": "chal", "xp_req": 600}
}

def check_level_up():
    current_xp = st.session_state.xp
    old_level = st.session_state.level
    new_level = 1
    for lvl, config in LEVEL_CONFIG.items():
        if current_xp >= config['xp_req']:
            new_level = lvl
    if new_level > old_level:
        st.session_state.level = new_level
        st.balloons()
        st.toast(f"🎉 恭喜升級！現在是 {LEVEL_CONFIG[new_level]['name']}！")

def generate_question():
    if df.empty: return None
    lvl = st.session_state.level
    q_type = LEVEL_CONFIG[lvl]['type']
    
    if q_type == 'sent':
        pool = df[df['例句'] != '']
        if pool.empty: pool = df
    else:
        pool = df
        
    target = pool.sample(1).iloc[0]
    q_data = {'target': target, 'type': q_type, 'options': [], 'correct_ans': target['成語']}
    
    if q_type == 'def':
        q_data['question_text'] = f"🔮 **解釋**：{target['解釋']}"
        distractors = df[df['成語'] != target['成語']].sample(3)['成語'].tolist()
        options = distractors + [target['成語']]
        random.shuffle(options)
        q_data['options'] = options
    elif q_type == 'sent':
        sent = target['例句'].replace(target['成語'], '______')
        q_data['question_text'] = f"📜 **例句**：{sent}"
        distractors = df[df['成語'] != target['成語']].sample(3)['成語'].tolist()
        options = distractors + [target['成語']]
        random.shuffle(options)
        q_data['options'] = options
    elif q_type == 'fill':
        idiom = target['成語']
        if len(idiom) >= 4:
            mask_idx = random.randint(0, 3)
            chars = list(idiom)
            ans_char = chars[mask_idx]
            chars[mask_idx] = '❓'
            q_data['question_text'] = f"🧩 **填空**：{''.join(chars)}\n\n(提示：{target['解釋']})"
            q_data['correct_ans'] = ans_char
        else:
            return generate_question()
    elif q_type == 'chal':
        q_data['question_text'] = f"🔥 **挑戰**：請寫出符合解釋的成語\n\n{target['解釋']}"
        
    return q_data

# --- 4. 介面呈現 (UI) ---
with st.sidebar:
    st.title("🧙‍♂️ 學生檔案")
    st.write(f"🏠 學院：{st.session_state.house}")
    lvl = st.session_state.level
    next_xp = LEVEL_CONFIG[lvl+1]['xp_req'] if lvl < 4 else 9999
    current_base = LEVEL_CONFIG[lvl]['xp_req']
    
    if lvl < 4:
        # 避免分母為0
        denominator = max(1, next_xp - current_base)
        progress = (st.session_state.xp - current_base) / denominator
        st.progress(max(0.0, min(1.0, progress)))
        st.caption(f"XP: {st.session_state.xp} / {next_xp}")
    else:
        st.progress(1.0)
        st.caption(f"XP: {st.session_state.xp} (Max)")

    st.markdown("---")
    st.subheader("🏆 徽章")
    if st.session_state.badges:
        for b in st.session_state.badges: st.write(f"🏅 {b}")
    else: st.write("尚未獲得...")

tab1, tab2, tab3 = st.tabs(["⚡ 咒語修練", "📜 成績單", "🔮 儲思盆"])

with tab1:
    st.header(LEVEL_CONFIG[st.session_state.level]['name'])
    if st.session_state.current_q is None:
        st.session_state.current_q = generate_question()
        st.session_state.user_answered = False

    q = st.session_state.current_q
    if q:
        st.info(q['question_text'])
        user_input = None
        submit = False
        
        if q['type'] in ['def', 'sent']:
            user_input = st.radio("選擇：", q['options'], key="rad")
            submit = st.button("揮舞魔杖")
        elif q['type'] == 'fill':
            user_input = st.text_input("輸入一字：", max_chars=1)
            submit = st.button("填補")
        elif q['type'] == 'chal':
            user_input = st.text_input("輸入成語：")
            submit = st.button("施法")

        if submit and not st.session_state.user_answered:
            if user_input:
                st.session_state.user_answered = True
                if user_input.strip() == q['correct_ans']:
                    st.markdown('<div class="success-msg">✨ 正確！ (Correct)</div>', unsafe_allow_html=True)
                    st.session_state.xp += (10 * st.session_state.level)
                    st.session_state.history.append(1)
                    if st.session_state.xp >= 100 and "初級巫師" not in st.session_state.badges:
                        st.session_state.badges.append("初級巫師")
                else:
                    st.markdown(f'<div class="error-msg">💥 錯誤... 答案是：{q["correct_ans"]}</div>', unsafe_allow_html=True)
                    st.session_state.history.append(0)
                    st.session_state.wrong_questions.append({"題目": q['target']['成語'], "正確答案": q['target']['解釋']})
                check_level_up()
            else:
                st.warning("請輸入答案！")

        if st.session_state.user_answered:
            if st.button("下一題"):
                st.session_state.current_q = None
                st.rerun()

with tab2:
    st.subheader("📊 分析")
    if st.session_state.history:
        total = len(st.session_state.history)
        acc = (sum(st.session_state.history)/total)*100
        col1, col2 = st.columns(2)
        col1.metric("答題數", total)
        col2.metric("正確率", f"{acc:.0f}%")
        st.line_chart(pd.DataFrame({'正確': [sum(st.session_state.history[:i+1]) for i in range(total)]}))
    else: st.write("請先開始答題")

with tab3:
    st.subheader("🔮 錯題回顧")
    if st.session_state.wrong_questions:
        st.table(st.session_state.wrong_questions)