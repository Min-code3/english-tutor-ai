"""
Vercel Serverless API — /api/chat
POST body: { "messages": [...], "level": "...", "interests": "...", "model": "..." }
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
from openai import OpenAI

MAX_TURNS = 20

SYSTEM_TEMPLATE = """You are a kind, patient, and encouraging native English tutor.
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

## 💬 Step 3: Let's Keep Talking!
React warmly to what the student said, then ask **1–2 natural follow-up questions in English**
to continue the conversation. Use a friendly, casual tone — like texting a friend.

━━━━━━━━━━━━━━━━━━━━━━━
EXCEPTION — KOREAN / NON-ENGLISH INPUT
━━━━━━━━━━━━━━━━━━━━━━━

If the student writes in Korean (or any non-English language), skip the three steps and respond with:

## 🌏 영어로 이렇게 말해요!
- Provide a natural English translation.
- Offer 2–3 alternative phrasings (formal / casual / short).
- Give a one-line Korean explanation of any nuance.
- Encourage them to try using one of the phrases in a full sentence.

Always match vocabulary complexity to the student's **{level}** level."""


def build_system_prompt(level: str, interests: str) -> str:
    return SYSTEM_TEMPLATE.format(level=level, interests=interests)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        level     = body.get("level", "Intermediate")
        interests = body.get("interests", "daily life, travel")
        model     = body.get("model", "gpt-4o-mini")
        messages  = body.get("messages", [])

        # Sliding window
        window = messages[-(MAX_TURNS * 2):] if len(messages) > MAX_TURNS * 2 else messages

        api_messages = [
            {"role": "system", "content": build_system_prompt(level, interests)},
            *window,
        ]

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._json({"error": "OPENAI_API_KEY not configured"}, 500)
            return

        try:
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=0.7,
                max_tokens=1200,
            )
            reply = resp.choices[0].message.content
            self._json({"reply": reply})
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _cors(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Content-Type", "application/json")

    def _json(self, data: dict, status: int = 200):
        self._cors()
        self.send_response(status)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, *args):
        pass  # suppress default access logs
