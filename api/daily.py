from flask import Flask, jsonify
from datetime import date
import json
import os

app = Flask(__name__)


@app.route("/api/daily", methods=["GET"])
def daily():
    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "questions.json")

    try:
        with open(path, encoding="utf-8") as f:
            questions = json.load(f)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not questions:
        return jsonify({"error": "questions.json is empty"}), 500

    # Same question all day, cycles through the list day by day
    index = date.today().timetuple().tm_yday % len(questions)
    return jsonify({
        "question": questions[index],
        "index": index,
        "total": len(questions),
    })
