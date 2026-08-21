import os

from flask import Flask, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY не найден в Render Environment Variables")

client = OpenAI(api_key=api_key)


@app.get("/")
def home():
    return "Moto AI server is working!"


@app.get("/test")
def test():
    try:
        print("TEST: начинаем проверку OpenAI")

        response = client.responses.create(
            model="gpt-5.6",
            input="Ответь одним словом: OK"
        )

        answer = response.output_text

        print("TEST: OpenAI ответил:", answer)

        return jsonify({
            "ok": True,
            "openai": answer
        })

    except Exception as error:
        print("OPENAI ERROR:", repr(error))

        return jsonify({
            "ok": False,
            "error": str(error)
        }), 500


@app.post("/analyze")
def analyze():
    return jsonify({

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
