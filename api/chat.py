from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

MAX_TURNS = 20

SYSTEM_TEMPLATE = """You are a kind, patient, and encouraging native English tutor.
The student's proficiency level is: **{level}**.
The student's interests / preferred topics are: **{interests}**.

When the student writes in English, always reply with these three sections:

## ✏️ Step 1: Sentence Correction & Feedback
- Identify unnatural or incorrect parts. Show as: ❌ "original" → ✅ "corrected"
- Only flag critical errors. Explain each in Korean (한국어로).
- If perfect: "완벽해요! 🎉"

## 💯 Step 2: Full Corrected Sentence
Complete polished sentence in a markdown blockquote (> …).

## 💬 Step 3: Let's Keep Talking!
React warmly and ask 1–2 natural follow-up questions in English. Casual, friendly tone.

EXCEPTION: If the student writes in Korean, respond with:
## 🌏 영어로 이렇게 말해요!
Natural English translation + 2–3 alternatives + Korean nuance note.

Always match vocabulary to the student's {level} level."""


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))

    data     = request.get_json(force=True) or {}
    level    = data.get("level", "Intermediate")
    interests= data.get("interests", "daily life")
    model    = data.get("model", "gpt-4o-mini")
    messages = data.get("messages", [])

    window = messages[-(MAX_TURNS * 2):] if len(messages) > MAX_TURNS * 2 else messages

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _cors(jsonify({"error": "OPENAI_API_KEY not set"}), 500)

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_TEMPLATE.format(level=level, interests=interests)},
                *window,
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        return _cors(jsonify({"reply": resp.choices[0].message.content}))
    except Exception as e:
        return _cors(jsonify({"error": str(e)}), 500)


def _cors(response, status=200):
    response.status_code = status
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response
