"""
English Conversation Tutor — Streamlit App
Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud  (connect GitHub repo)
              Vercel                     (see vercel.json + api/chat.py)
"""

import re
import os
import markdown as md_lib
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────
MAX_TURNS = 20          # sliding window sent to API
MODELS = {
    "gpt-4o-mini (빠름 · 저렴)": "gpt-4o-mini",
    "gpt-4o (고품질)":           "gpt-4o",
}
LEVELS = ["Beginner", "Elementary", "Intermediate", "Upper-Intermediate", "Advanced"]

# ── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI English Tutor 🎓",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── global ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: .8rem; padding-bottom: 5rem; max-width: 760px; }

/* ── chat messages (native st.chat_message) ── */
[data-testid="stChatMessage"] { border-radius: 16px; }

/* ── section boxes ── */
.sec-feedback {
  background: #fffbeb; border-left: 4px solid #f59e0b;
  border-radius: 8px; padding: 14px 16px; margin: 8px 0;
}
.sec-feedback h4 { color: #92400e; margin: 0 0 8px; font-size: .8rem;
  text-transform: uppercase; letter-spacing: .06em; }

.sec-corrected {
  background: #f0fdf4; border-left: 4px solid #22c55e;
  border-radius: 8px; padding: 14px 16px; margin: 8px 0;
}
.sec-corrected h4 { color: #166534; margin: 0 0 8px; font-size: .8rem;
  text-transform: uppercase; letter-spacing: .06em; }

.sec-chat {
  background: #eff6ff; border-left: 4px solid #3b82f6;
  border-radius: 8px; padding: 14px 16px; margin: 8px 0;
}
.sec-chat h4 { color: #1e40af; margin: 0 0 8px; font-size: .8rem;
  text-transform: uppercase; letter-spacing: .06em; }

.sec-korean {
  background: #fdf4ff; border-left: 4px solid #a855f7;
  border-radius: 8px; padding: 14px 16px; margin: 8px 0;
}
.sec-korean h4 { color: #6b21a8; margin: 0 0 8px; font-size: .8rem;
  text-transform: uppercase; letter-spacing: .06em; }

/* ── section inner text ── */
.sec-feedback p, .sec-corrected p, .sec-chat p, .sec-korean p {
  margin: .3rem 0; font-size: 15px; line-height: 1.65;
}
.sec-feedback ul, .sec-corrected ul, .sec-chat ul, .sec-korean ul {
  margin: .3rem 0 .3rem 1.2rem; padding: 0;
}
blockquote {
  border-left: 3px solid #22c55e; background: #dcfce7;
  margin: 6px 0; padding: 8px 14px; border-radius: 4px;
  font-style: normal; font-weight: 600;
}

/* ── sidebar ── */
[data-testid="stSidebar"] { background: #075e54; }
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] .stTextInput input {
  background: rgba(255,255,255,.12) !important;
  border-color: rgba(255,255,255,.3) !important;
  color: #fff !important;
}
[data-testid="stSidebar"] label { font-weight: 600; }

/* ── mobile ── */
@media (max-width: 600px) {
  .block-container { padding-left: .4rem; padding-right: .4rem; }
}
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
def _init():
    defaults = {
        "messages": [],
        "level":     "Intermediate",
        "interests": "daily life, travel, food",
        "model_key": list(MODELS.keys())[0],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 AI English Tutor")
    st.markdown("---")

    st.session_state.level = st.selectbox(
        "📊 영어 레벨", LEVELS,
        index=LEVELS.index(st.session_state.level),
    )
    st.session_state.interests = st.text_area(
        "💡 관심사 / 대화 주제",
        value=st.session_state.interests,
        placeholder="예: K-pop, 영화, 요리, 여행, 스포츠…",
        height=90,
    )
    st.session_state.model_key = st.selectbox(
        "🤖 AI 모델", list(MODELS.keys()),
        index=list(MODELS.keys()).index(st.session_state.model_key),
    )

    st.markdown("---")
    if st.button("🔄 새로운 대화 시작", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<small>💡 영어로 말해보세요.<br>한국어로 써도 번역해 드려요!</small>",
        unsafe_allow_html=True,
    )

    # API key input (if not in .env)
    if not os.getenv("OPENAI_API_KEY"):
        api_key = st.text_input("🔑 OpenAI API Key", type="password",
                                help="OPENAI_API_KEY 환경변수가 없을 때 여기에 입력하세요")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key


# ── System prompt builder ─────────────────────────────────────────────────────
def build_system_prompt(level: str, interests: str) -> str:
    return f"""You are a kind, patient, and encouraging native English tutor.
The student's proficiency level is: **{level}**.
The student's interests / preferred topics are: **{interests}**.

━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT (MUST FOLLOW EXACTLY)
━━━━━━━━━━━━━━━━━━━━━━━

When the student writes in English, always reply with these three sections
using **exactly** these markdown headings:

## ✏️ Step 1: Sentence Correction & Feedback
- Identify unnatural or incorrect parts of the student's sentence.
- Show each issue as:  ❌ "original phrase"  →  ✅ "corrected phrase"
- Only flag errors that hurt communication or sound clearly unnatural to a native speaker.
- Explain each correction **briefly in Korean** (한국어로 설명).
- If the sentence is already perfect, write:
  "완벽해요! 🎉 아주 자연스러운 문장이에요."

## 💯 Step 2: Full Corrected Sentence
Provide the complete, polished English sentence that reflects all corrections.
Wrap it in a markdown blockquote (> …) so the student can read and memorize it easily.
Add one short Korean note below the blockquote explaining the overall tone/register if helpful.

## 💬 Step 3: Let's Keep Talking!
React warmly to what the student said, then ask **1–2 natural follow-up questions in English**
to continue the conversation.  Use a friendly, casual tone — like texting a friend.

━━━━━━━━━━━━━━━━━━━━━━━
EXCEPTION — KOREAN / NON-ENGLISH INPUT
━━━━━━━━━━━━━━━━━━━━━━━

If the student writes in Korean (or any non-English language), they likely don't know how
to express it in English.  In this case, skip the three steps above and respond with:

## 🌏 영어로 이렇게 말해요!
- Provide a natural English translation of their Korean text.
- Offer 2–3 alternative phrasings (formal / casual / short).
- Give a one-line Korean explanation of any nuance.
- Encourage them to try using one of the phrases in a full sentence.

━━━━━━━━━━━━━━━━━━━━━━━
GENERAL RULES
━━━━━━━━━━━━━━━━━━━━━━━
- Always match vocabulary complexity to the student's **{level}** level.
- Never be harsh — celebrate effort and progress.
- Keep Step 3 conversational; the goal is to build confidence through real dialogue."""


# ── Section parser ─────────────────────────────────────────────────────────────
_S1 = re.compile(r'##\s*✏️?\s*Step\s*1[^\n]*\n(.*?)(?=##\s*💯?\s*Step\s*2|$)', re.DOTALL | re.I)
_S2 = re.compile(r'##\s*💯?\s*Step\s*2[^\n]*\n(.*?)(?=##\s*💬?\s*Step\s*3|$)', re.DOTALL | re.I)
_S3 = re.compile(r'##\s*💬?\s*Step\s*3[^\n]*(.*?)$', re.DOTALL | re.I)
_KO = re.compile(r'##\s*🌏[^\n]*\n(.*?)$', re.DOTALL | re.I)


def _html(text: str) -> str:
    """Convert markdown snippet to HTML (safe inner content)."""
    return md_lib.markdown(text.strip(), extensions=["nl2br"])


def render_ai_response(content: str):
    """Render AI reply with colour-coded sections."""
    ko_match = _KO.search(content)
    if ko_match:
        body_html = _html(ko_match.group(1))
        st.markdown(
            f'<div class="sec-korean"><h4>🌏 영어로 이렇게 말해요!</h4>{body_html}</div>',
            unsafe_allow_html=True,
        )
        return

    m1, m2, m3 = _S1.search(content), _S2.search(content), _S3.search(content)
    if m1 and m2 and m3:
        st.markdown(
            f'<div class="sec-feedback">'
            f'<h4>✏️ 문장 교정 &amp; 피드백</h4>{_html(m1.group(1))}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="sec-corrected">'
            f'<h4>💯 교정된 전체 문장</h4>{_html(m2.group(1))}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="sec-chat">'
            f'<h4>💬 대화 이어가기</h4>{_html(m3.group(1))}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # Fallback: plain markdown
        st.markdown(content)


# ── Chat history display ──────────────────────────────────────────────────────
st.markdown("### 💬 AI English Tutor")

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🎓"):
        st.markdown(
            "안녕하세요! 👋 저는 여러분의 **AI 영어 튜터**예요.  \n"
            "영어로 말을 걸어주세요. 틀려도 괜찮아요 — 함께 고쳐나가요!  \n"
            "한국어로 쓰면 영어로 어떻게 말하는지 알려드려요. 😊"
        )

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🙋"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🎓"):
            render_ai_response(msg["content"])


# ── Input & API call ──────────────────────────────────────────────────────────
user_input = st.chat_input("영어로 말해보세요! (한국어도 OK 👍)")

if user_input:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API Key가 없습니다. 사이드바에서 입력하거나 .env 파일에 OPENAI_API_KEY를 설정하세요.")
        st.stop()

    # Display user message immediately
    with st.chat_message("user", avatar="🙋"):
        st.write(user_input)

    # Append to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Build sliding-window context (last MAX_TURNS turns = MAX_TURNS*2 messages)
    history = st.session_state.messages
    window = history[-(MAX_TURNS * 2):] if len(history) > MAX_TURNS * 2 else history

    system_prompt = build_system_prompt(
        st.session_state.level,
        st.session_state.interests,
    )
    api_messages = [{"role": "system", "content": system_prompt}] + window

    # Stream response
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = MODELS[st.session_state.model_key]

    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("생각 중…"):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=1200,
                )
                reply = response.choices[0].message.content
            except Exception as exc:
                st.error(f"API 오류: {exc}")
                st.stop()

        render_ai_response(reply)

    # Save assistant reply
    st.session_state.messages.append({"role": "assistant", "content": reply})
