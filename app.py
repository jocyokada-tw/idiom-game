import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime, timedelta

# --- 1. 設定與風格 ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8f5e6; color: #2c2c2c; font-family: "Garamond", serif; }
    h1, h2, h3 { color: #740001; font-weight: bold; }
    /* 按鈕與進度條 */
    .stButton>button { color: #d3a625; background-color: #740001; border: 2px solid #d3a625; font-weight: bold; border-radius: 8px;}
    .stButton>button:hover { background-color: #5d0000; border-color: #ffcc00; }
    .stProgress > div > div > div > div { background-color: #d3a625; }
    /* 生命值樣式 */
    .hp-bar { font-size: 1.5em; color: #c62828; font-weight: bold; margin-bottom: 10px; }
    .hp-recover { font-size: 0.8em; color: #555; font-style: italic; }
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #1a1a1a; color: #f0f0f0; }
    /* 訊息框 */
    .success-msg { padding:10px; background-color:#d4edda; color:#155724; border-radius:5px; border:1px solid #c3e6cb; font-weight:bold; }
    .error-msg { padding:10px; background-color:#f8d7da; color:#721c24; border-radius:5px; border:1px solid #f5c6cb; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 魔法分類帽演算法 (自動分類) ---
def sorting_hat(idiom):
    # 關鍵字庫
    animals = "龍虎豹狼狗犬雞猴猿馬牛羊豬鼠兔蛇鳥鶴鷹魚鳳凰鴉雀鴻鵠鱉龜麟獸蟬蠶"
    nature = "花草樹木林葉根山川河海水火風雨雲雷電雪霜天地日月星"
    alchemy = "金銀銅鐵錫玉石珠寶劍刀槍弓鼎釜"
    
    if any(c in animals for c in idiom):
        return "🐉 奇獸飼育學 (動物系)"
    elif any(c in alchemy for c in idiom):
        return "⚗️ 煉金術 (物質系)"
    elif any(c in nature for c in idiom):
        return "🌊 自然元素學 (自然系)"
    else:
        return "✨ 符咒學 (一般系)"

# --- 3. 資料載入與處理 ---
@st.cache_data
def load_data():
    possible_files = ['idioms.csv', '成語資料庫.xlsx - 工作表1 (2).csv', '成語資料庫.csv']
    df = None
    for f in possible_files:
        try:
            df = pd.read_csv(f)
            break
        except FileNotFoundError:
            continue
            
    if df is None:
        st.error("⚠️ 找不到資料庫檔案！")
        return pd.DataFrame()

    if '例句' in df.columns:
        df['例句'] = df['例句'].fillna('')
    df = df.dropna(subset=['成語', '解釋'])
    
    # 應用分類帽
    df['魔法屬性'] = df['成語'].apply(sorting_hat)
    return df

df = load_data()

# --- 4. 遊戲核心邏輯 ---

# 初始化狀態
if 'xp' not in st.session_state:
    st.session_state.xp = 0
    st.session_state.level = 1
    st.session_state.house = "葛來分多"
    st.session_state.history = []
    st.session_state.wrong_questions = []
    st.session_state.badges = []
    st.session_state.current_q = None
    st.session_state.user_answered = False
    
    # 生命值系統
    st.session_state.hp = 10
    st.session_state.max_hp = 10
    st.session_state.last_hp_update = time.time() 

LEVEL_CONFIG = {
    1: {"name": "一年級：魔法石 (解釋題)", "type": "def", "xp_req": 0},
    2: {"name": "三年級：阿茲卡班 (例句題)", "type": "sent", "xp_req": 100},
    3: {"name": "五年級：鳳凰會 (填空題)", "type": "fill", "xp_req": 300},
    4: {"name": "七年級：死神的聖物 (挑戰題)", "type": "chal", "xp_req": 600}
}

# 生命值回復邏輯
def update_hp():
    now = time.time()
    elapsed = now - st.session_state.last_hp_update
    # 每 1800 秒 (30分鐘) 回復 1 點
    recover_amount = int(elapsed // 1800)
    
    if recover_amount > 0:
        if st.session_state.hp < st.session_state.max_hp:
            st.session_state.hp = min(st.session_state.max_hp, st.session_state.hp + recover_amount)
            st.toast(f"💖 體力恢復了 {recover_amount} 點！")
        # 更新時間戳 (保留餘數時間)
        st.session_state.last_hp_update = now - (elapsed % 1800)

update_hp()

def check_badges():
    new_badges = []
    # 條件 1: 經驗值達標
    if st.session_state.xp >= 100 and "初級巫師" not in st.session_state.badges:
        new_badges.append("初級巫師")
    if st.session_state.xp >= 500 and "黑魔法防禦大師" not in st.session_state.badges:
        new_badges.append("黑魔法防禦大師")
    
    # 條件 2: 連續答對 (簡單判斷最近5題)
    if len(st.session_state.history) >= 5 and sum(st.session_state.history[-5:]) == 5:
        if "神鋒無影 (五連殺)" not in st.session_state.badges:
            new_badges.append("神鋒無影 (五連殺)")
            
    # 條件 3: 完美主義 (沒錯過)
    if st.session_state.xp >= 200 and not st.session_state.wrong_questions:
        if "純種榮耀 (完美無缺)" not in st.session_state.badges:
            new_badges.append("純種榮耀 (完美無缺)")

    for b in new_badges:
        st.session_state.badges.append(b)
        st.toast(f"🏆 恭喜獲得成就徽章：{b}", icon="🎉")

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

def generate_question(category_filter="全部"):
    if df.empty: return None
    
    # 根據分類篩選
    pool = df
    if category_filter != "全部":
        pool = df[df['魔法屬性'] == category_filter]
        if pool.empty:
            st.warning(f"此分類 ({category_filter}) 中沒有足夠的題目，已切換回全部題庫。")
            pool = df

    lvl = st.session_state.level
    q_type = LEVEL_CONFIG[lvl]['type']
    
    if q_type == 'sent':
        pool = pool[pool['例句'] != '']
        if pool.empty: pool = df # Fallback
        
    target = pool.sample(1).iloc[0]
    q_data = {'target': target, 'type': q_type, 'options': [], 'correct_ans': target['成語']}
    
    # 題型邏輯
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
            return generate_question(category_filter)
    elif q_type == 'chal':
        q_data['question_text'] = f"🔥 **挑戰**：請寫出符合解釋的成語\n\n{target['解釋']}"
        
    return q_data

# --- 5. 介面呈現 ---

# 側邊欄
with st.sidebar:
    st.title("🧙‍♂️ 巫師檔案")
    st.write(f"🏠 學院：{st.session_state.house}")
    
    # 生命值顯示
    hp = st.session_state.hp
    hearts = "❤️" * hp + "🤍" * (10 - hp)
    st.markdown(f"<div class='hp-bar'>{hearts}</div>", unsafe_allow_html=True)
    st.write(f"生命值: {hp} / 10")
    
    # 回復倒數計算
    elapsed = time.time() - st.session_state.last_hp_update
    next_recover = 1800 - elapsed
    if hp < 10:
        st.caption(f"⏳ 下一點體力回復：{int(next_recover//60)} 分鐘後")
    else:
        st.caption("體力已滿")

    st.markdown("---")
    
    # 分類選擇器
    st.subheader("📚 選擇選修課程")
    categories = ["全部"] + sorted(list(df['魔法屬性'].unique()))
    selected_class = st.selectbox("你想挑戰哪類魔法？", categories)
    
    st.markdown("---")
    
    # 經驗與進度
    lvl = st.session_state.level
    st.write(f"**等級**: {LEVEL_CONFIG[lvl]['name']}")
    next_xp = LEVEL_CONFIG[lvl+1]['xp_req'] if lvl < 4 else 9999
    current_base = LEVEL_CONFIG[lvl]['xp_req']
    if lvl < 4:
        prog = max(0.0, min(1.0, (st.session_state.xp - current_base) / max(1, next_xp - current_base)))
        st.progress(prog)
        st.caption(f"XP: {st.session_state.xp} / {next_xp}")
    
    # 徽章
    st.subheader("🏆 榮譽徽章")
    for b in st.session_state.badges:
        st.write(f"🏅 {b}")

# 主畫面
tab1, tab2, tab3 = st.tabs(["⚡ 咒語修練", "📜 O.W.L.s 成績單", "🔮 儲思盆"])

with tab1:
    st.header(f"課堂：{selected_class}")
    
    if st.session_state.hp <= 0:
        st.error("💀 你已經耗盡體力了！請休息一下，等待體力回復（或重新整理頁面重置）。")
    else:
        # 生成題目
        if st.session_state.current_q is None:
            st.session_state.current_q = generate_question(selected_class)
            st.session_state.user_answered = False

        q = st.session_state.current_q
        if q:
            st.info(q['question_text'])
            
            user_input = None
            submit = False
            
            # 根據題型顯示輸入
            if q['type'] in ['def', 'sent']:
                user_input = st.radio("選擇咒語：", q['options'], key="opt")
                submit = st.button("揮舞魔杖 (消耗 1 ❤️)")
            elif q['type'] == 'fill':
                user_input = st.text_input("輸入符文：", max_chars=1)
                submit = st.button("填補咒語 (消耗 1 ❤️)")
            elif q['type'] == 'chal':
                user_input = st.text_input("吟唱成語：")
                submit = st.button("施法 (消耗 1 ❤️)")

            if submit and not st.session_state.user_answered:
                if user_input:
                    # 扣血邏輯：按下按鈕先扣 1
                    st.session_state.hp -= 1
                    st.session_state.user_answered = True
                    
                    if user_input.strip() == q['correct_ans']:
                        # 答對：回復 1 (等於沒扣)
                        st.session_state.hp += 1
                        st.markdown('<div class="success-msg">✨ 咒語生效！ (體力維持)</div>', unsafe_allow_html=True)
                        st.session_state.xp += (10 * st.session_state.level)
                        st.session_state.history.append(1)
                    else:
                        # 答錯：不回復 (等於實扣 1)
                        st.markdown(f'<div class="error-msg">💥 魔杖逆火... 答案是：{q["correct_ans"]} (體力 -1)</div>', unsafe_allow_html=True)
                        st.session_state.history.append(0)
                        st.session_state.wrong_questions.append({
                            "題目": q['target']['成語'], 
                            "解釋": q['target']['解釋'],
                            "你的答案": user_input
                        })
                    
                    check_badges() # 檢查徽章
                    check_level_up() # 檢查升級
                    st.rerun() # 強制刷新以更新側邊欄血條
                else:
                    st.warning("請先輸入答案！")

            if st.session_state.user_answered:
                if st.button("下一題"):
                    st.session_state.current_q = None
                    st.rerun()

with tab2:
    st.subheader("📊 學習分析")
    if st.session_state.history:
        total = len(st.session_state.history)
        acc = sum(st.session_state.history)/total * 100
        col1, col2, col3 = st.columns(3)
        col1.metric("答題總數", total)
        col2.metric("正確率", f"{acc:.1f}%")
        col3.metric("剩餘體力", st.session_state.hp)
        
        st.bar_chart(pd.DataFrame(st.session_state.history, columns=["答題結果(1=對,0=錯)"]))
    else:
        st.write("尚未開始課程。")

with tab3:
    st.subheader("🔮 錯題回顧")
    if st.session_state.wrong_questions:
        st.table(pd.DataFrame(st.session_state.wrong_questions))
        if st.button("清空儲思盆"):
            st.session_state.wrong_questions = []
            st.rerun()
    else:
        st.write("你的儲思盆很乾淨，做得好！")
