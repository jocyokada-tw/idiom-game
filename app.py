import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# --- 1. 設定與風格 (CSS) ---
st.set_page_config(page_title="霍格華茲成語魔法學院", page_icon="🏰", layout="wide")

st.markdown("""
<style>
    /* 全局設定 */
    .stApp { background-color: #f8f5e6; color: #2c2c2c; font-family: "Garamond", "Times New Roman", serif; }
    h1, h2, h3 { color: #740001; font-weight: bold; }
    
    /* 按鈕樣式 */
    .stButton>button { color: #d3a625; background-color: #740001; border: 2px solid #d3a625; font-weight: bold; border-radius: 8px;}
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
    .cert-title { font-size: 2.5em; color: #740001; font-family: 'Cursive', serif; margin-bottom: 10px; }
    .cert-body { font-size: 1.2em; color: #333; line-height: 1.6; }
    .cert-signature { margin-top: 30px; font-style: italic; color: #555; }
    
    /* 訊息框 */
    .success-msg { padding:15px; background-color:#d4edda; color:#155724; border-left: 5px solid #28a745; font-weight:bold; font-size:1.1em; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-left: 5px solid #dc3545; }
    .correct-ans { font-size: 1.3em; font-weight: bold; color: #c62828; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 魔法分類帽演算法 (15學科版) ---
def sorting_hat(idiom_row):
    text = str(idiom_row['成語']) + str(idiom_row['解釋'])
    
    # 關鍵字對映表
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
    
    # 優先順序判定
    for subject, keys in keywords.items():
        if any(k in text for k in keys):
            return subject
            
    return "符咒學" # 預設分類 (一般類)

# --- 3. 資料處理 ---
@st.cache_data
def load_data():
    # 支援多種檔名讀取
    files = ['idioms.csv', '成語資料庫.xlsx - 工作表1 (2).csv', '成語資料庫.csv']
    df = None
    for f in files:
        try:
            df = pd.read_csv(f)
            break
        except: continue
    
    if df is None:
        st.error("⚠️ 找不到資料庫檔案，請確認 CSV 已上傳。")
        return pd.DataFrame()
        
    df['例句'] = df['例句'].fillna('')
    df = df.dropna(subset=['成語', '解釋'])
    # 應用新分類
    df['魔法學科'] = df.apply(sorting_hat, axis=1)
    return df

df = load_data()

# --- 4. 遊戲狀態與升級設定 ---

# 等級設定 (年級)
LEVELS = {
    1: {"name": "一年級", "type": "def", "target": 90, "streak_req": 20, "desc": "解釋題"},
    2: {"name": "三年級", "type": "sent", "target": 70, "streak_req": 15, "desc": "例句題"},
    3: {"name": "五年級", "type": "fill", "target": 50, "streak_req": 10, "desc": "填空題"},
    4: {"name": "七年級", "type": "chal", "target": 50, "streak_req": 0, "desc": "挑戰題 (全默寫)"}
}

if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.level = 1
    st.session_state.xp = 0
    st.session_state.hp = 10
    st.session_state.last_hp_time = time.time()
    
    # 進度追蹤
    st.session_state.level_correct = 0  # 當前等級答對總數
    st.session_state.streak = 0         # 當前連對數
    st.session_state.max_streak = 0     # 本級最大連對
    
    st.session_state.badges = []
    st.session_state.history = []
    st.session_state.wrong_list = []
    
    # 遊戲流程控制
    st.session_state.current_q = None
    st.session_state.last_result = None # 儲存上一題結果以顯示回饋
    st.session_state.show_cert = False  # 是否顯示證書
    st.session_state.cert_type = None   # "level_up" or "master"

# 體力回復
def recover_hp():
    now = time.time()
    elapsed = now - st.session_state.last_hp_time
    rec = int(elapsed // 1800) # 30分
    if rec > 0:
        if st.session_state.hp < 10:
            st.session_state.hp = min(10, st.session_state.hp + rec)
        st.session_state.last_hp_time = now - (elapsed % 1800)
recover_hp()

# --- 5. 核心邏輯函式 ---

def check_progress():
    lvl = st.session_state.level
    cfg = LEVELS[lvl]
    
    # 檢查是否滿足升級/通關條件
    cond_total = st.session_state.level_correct >= cfg['target']
    cond_streak = st.session_state.streak >= cfg['streak_req'] # 七年級 streak_req 為 0，自動為 True
    
    if cond_total and cond_streak:
        st.session_state.show_cert = True
        if lvl == 4:
            st.session_state.cert_type = "master"
        else:
            st.session_state.cert_type = "level_up"

def proceed_level():
    """ 點擊證書上的繼續按鈕後執行 """
    if st.session_state.cert_type == "level_up":
        st.session_state.level += 1
        # 重置當前等級進度
        st.session_state.level_correct = 0
        st.session_state.streak = 0
        st.session_state.show_cert = False
        st.session_state.current_q = None
        st.rerun()
    elif st.session_state.cert_type == "master":
        # 通關處理
        subject = st.session_state.current_subject
        if f"{subject}大師" not in st.session_state.badges:
            st.session_state.badges.append(f"{subject}大師")
        st.session_state.show_cert = False
        st.session_state.level_correct = 0 # 可以選擇讓他們無限玩，或重置
        st.rerun()

def generate_question(subject):
    if df.empty: return None
    
    # 篩選學科
    pool = df
    if subject != "全部學科":
        pool = df[df['魔法學科'] == subject]
        if pool.empty:
            st.toast(f"⚠️ {subject} 的考題不足，暫時使用全部題庫。", icon="🧙‍♂️")
            pool = df
    
    # 根據等級選題型
    lvl_type = LEVELS[st.session_state.level]['type']
    
    # 取題
    if lvl_type == 'sent':
        pool = pool[pool['例句'] != '']
        if pool.empty: pool = df
        
    row = pool.sample(1).iloc[0]
    
    q = {
        'row': row,
        'type': lvl_type,
        'ans': row['成語'],
        'options': []
    }
    
    # 構建題目內容
    if lvl_type == 'def': # 一年級
        q['text'] = f"🔮 **【解釋】**：{row['解釋']}"
        opts = df[df['成語'] != row['成語']].sample(3)['成語'].tolist() + [row['成語']]
        random.shuffle(opts)
        q['options'] = opts
        
    elif lvl_type == 'sent': # 三年級
        sent = row['例句'].replace(row['成語'], '______')
        q['text'] = f"📜 **【例句】**：{sent}"
        opts = df[df['成語'] != row['成語']].sample(3)['成語'].tolist() + [row['成語']]
        random.shuffle(opts)
        q['options'] = opts
        
    elif lvl_type == 'fill': # 五年級
        chars = list(row['成語'])
        if len(chars) >= 4:
            mask = random.randint(0, 3)
            ans_char = chars[mask]
            chars[mask] = '❓'
            q['text'] = f"🧩 **【填空】**：{''.join(chars)}\n\n(提示：{row['解釋']})"
            q['ans'] = ans_char # 答案改為單字
            q['full'] = row['成語']
        else:
            return generate_question(subject) # 遞迴重抽
            
    elif lvl_type == 'chal': # 七年級
        q['text'] = f"🔥 **【終極挑戰】**：請寫出符合此解釋的成語\n\n{row['解釋']}"
        
    return q

# --- 6. 介面佈局 ---

# 側邊欄：巫師狀態
with st.sidebar:
    st.header("🏰 巫師檔案")
    
    # 體力
    hp = st.session_state.hp
    st.markdown(f"<div style='font-size:20px; color:#c62828'>{'❤️'*hp}{'🤍'*(10-hp)}</div>", unsafe_allow_html=True)
    st.caption(f"生命值: {hp}/10 (每30分回復1點)")
    
    st.markdown("---")
    
    # 選課系統
    subjects = ["全部學科"] + sorted(list(df['魔法學科'].unique()))
    selected_subject = st.selectbox("📚 選擇選修課程", subjects)
    st.session_state.current_subject = selected_subject # 存入狀態以供證書使用
    
    st.markdown("---")
    
    # 升級進度顯示
    lvl = st.session_state.level
    cfg = LEVELS[lvl]
    st.subheader(f"🎓 {cfg['name']}")
    st.caption(f"測驗內容：{cfg['desc']}")
    
    # 進度條 1: 總答對數
    curr_total = st.session_state.level_correct
    req_total = cfg['target']
    st.write(f"✅ 累積答對：{curr_total} / {req_total}")
    prog1 = min(1.0, curr_total / req_total)
    st.progress(prog1)
    
    # 進度條 2: 連續答對
    if cfg['streak_req'] > 0:
        curr_streak = st.session_state.streak
        req_streak = cfg['streak_req']
        st.write(f"🔥 連續答對：{curr_streak} / {req_streak}")
        prog2 = min(1.0, curr_streak / req_streak)
        st.progress(prog2)
    else:
        st.info("🔥 七年級不需連續答對，只需累積題數！")

    st.markdown("---")
    st.subheader("🏅 榮譽徽章")
    for b in st.session_state.badges:
        st.write(f"🛡️ {b}")

# 主畫面邏輯
st.title("🧙‍♂️ 霍格華茲成語魔法學院")

# 1. 顯示證書 (最高優先級)
if st.session_state.show_cert:
    if st.session_state.cert_type == "level_up":
        cert_title = "✨ 升級證書 ✨"
        cert_msg = f"""
        茲證明 <b>傑出的巫師</b><br>
        已成功通過 <b>{LEVELS[st.session_state.level]['name']}</b> 的嚴苛試煉。<br>
        展現了非凡的智慧與毅力！
        """
        btn_txt = "晉升下一年級"
    else:
        cert_title = "🏆 宗師證書 🏆"
        cert_msg = f"""
        至高無上的榮耀！<br>
        恭喜您完全精通了 <b>{st.session_state.current_subject}</b><br>
        並完成了七年級的所有挑戰。<br>
        您已成為該領域的魔法大師！
        """
        btn_txt = "領取徽章並繼續修練"

    st.markdown(f"""
    <div class="certificate-box">
        <div class="cert-title">{cert_title}</div>
        <div class="cert-body">{cert_msg}</div>
        <div class="cert-signature">霍格華茲校長室 頒發<br>{datetime.now().strftime('%Y-%m-%d')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(btn_txt, use_container_width=True):
        proceed_level()

# 2. 正常遊戲畫面
else:
    # 顯示上一題的結果 (Feedback)
    if st.session_state.last_result:
        res = st.session_state.last_result
        if res['correct']:
            st.markdown(f'<div class="success-msg">✨ 咒語生效！ (正確) +Streak</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="error-box">
                💥 魔杖逆火... (錯誤)<br>
                題目：{res['q_text']}<br>
                <div class="correct-ans">正確答案是：{res['ans']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.session_state.last_result = None # 清除結果

    # 檢查體力
    if st.session_state.hp <= 0:
        st.error("💀 體力耗盡！請休息一下等待回復。")
    else:
        # 生成題目
        if st.session_state.current_q is None:
            st.session_state.current_q = generate_question(st.session_state.current_subject)
        
        q = st.session_state.current_q
        
        if q:
            st.markdown(f"### {q['text']}")
            
            # 輸入區
            user_input = None
            submit = False
            
            with st.form("ans_form"):
                if q['type'] in ['def', 'sent']:
                    user_input = st.radio("請選擇：", q['options'])
                elif q['type'] == 'fill':
                    user_input = st.text_input("請輸入缺少的字：", max_chars=1)
                elif q['type'] == 'chal':
                    user_input = st.text_input("請輸入完整成語：")
                
                submit = st.form_submit_button("🪄 施法 (消耗1體力)")
            
            if submit:
                # 扣體力
                st.session_state.hp -= 1
                
                # 判定
                is_correct = False
                if user_input:
                    ans_clean = user_input.strip()
                    correct_ans = q['ans']
                    
                    if ans_clean == correct_ans:
                        is_correct = True
                        st.session_state.level_correct += 1
                        st.session_state.streak += 1
                        if st.session_state.streak > st.session_state.max_streak:
                            st.session_state.max_streak = st.session_state.streak
                    else:
                        st.session_state.streak = 0 # 重置連對
                        st.session_state.wrong_list.append({
                            "題目": q['row']['成語'],
                            "正確答案": q['ans']
                        })

                # 記錄結果給 Feedback 區塊顯示
                st.session_state.last_result = {
                    'correct': is_correct,
                    'ans': q['ans'],
                    'q_text': q['row']['解釋'] if q['type'] == 'chal' else q['row']['成語']
                }
                
                # 檢查是否升級
                check_progress()
                
                # 換下一題
                st.session_state.current_q = None
                st.rerun()

# --- 頁尾 ---
with st.expander("🔮 儲思盆 (錯題紀錄)"):
    if st.session_state.wrong_list:
        st.table(pd.DataFrame(st.session_state.wrong_list))
        if st.button("清空記憶"):
            st.session_state.wrong_list = []
            st.rerun()
    else:
        st.write("目前沒有錯題紀錄。")
