from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

MAX_TURNS = 20

SYSTEM = """You are a warm, encouraging English conversation tutor for Korean speakers.

Always reply in this EXACT format (never skip or rename any section):

## 💯 CORRECTED
Write the full corrected version of the user's message as a flowing paragraph. Fix all grammar, word choice, and naturalness. Keep their original meaning.

## ✏️ CORRECTIONS
Split the user's message into sentences. For EVERY sentence, in order of appearance, output exactly one line:
ITEM:: [original sentence verbatim] :: [corrected sentence] :: [Korean explanation in 1-2 short sentences]

Rules:
- You MUST include every sentence the user wrote, in order — never skip or merge sentences
- If a sentence is already perfect, copy it unchanged as the corrected version and write "자연스러워요 ✅" as the reason
- If the user used Korean words/expressions (e.g. 뒤심이 약하다), keep them as-is in [original sentence] and provide the natural English in [corrected sentence]. Explain the English choice in Korean.
- Do NOT output the word "NONE" — always output one ITEM per sentence

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
