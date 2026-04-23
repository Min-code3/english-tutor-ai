from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

MAX_TURNS = 20

SYSTEM = """You are a warm, encouraging English conversation tutor for Korean speakers.

Always reply in this EXACT format (never skip or rename any section):

## 💯 CORRECTED
Write the full corrected version of the user's message. Fix all grammar, word choice, and naturalness. Keep their original meaning completely.

## ✏️ CORRECTIONS
List each correction on its own line in exactly this format:
ITEM:: [original phrase] :: [corrected phrase] :: [Korean explanation in 1-2 sentences]

Rules:
- If the user included Korean words or expressions (e.g. 뒤심이 약하다), include an ITEM to give the natural English equivalent
- List the most important corrections only (up to 5 items)
- If there are truly no errors, write the single word: NONE

## 💬 CHAT
2-3 sentences. Be warm and encouraging. React to what they said and ask one natural follow-up question. English only.

---
EXCEPTION — If the user writes ONLY in Korean (zero English):
Do NOT use the format above. Instead respond with:
## 🌏 KOREAN
[In Korean: encourage them to try writing in English, and give a useful example English sentence they could use.]"""


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))

    data = request.get_json(force=True) or {}
    messages = data.get("messages", [])

    window = messages[-(MAX_TURNS * 2):] if len(messages) > MAX_TURNS * 2 else messages

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _cors(jsonify({"error": "OPENAI_API_KEY not set"}), 500)

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM}, *window],
            temperature=0.7,
            max_tokens=1200,
        )
        return _cors(jsonify({"reply": resp.choices[0].message.content}))
    except Exception as e:
        return _cors(jsonify({"error": str(e)}), 500)


def _cors(response, status=200):
    response.status_code = status
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response
