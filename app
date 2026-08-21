import os
import base64

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@app.get("/")
def home():
    return "Moto AI server is working!"


@app.post("/analyze")
def analyze():
    if "photo" not in request.files:
        return jsonify({"error": "Фото не найдено"}), 400

    photo = request.files["photo"]
    image_bytes = photo.read()

    if not image_bytes:
        return jsonify({"error": "Файл пустой"}), 400

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    content_type = photo.content_type or "image/jpeg"

    prompt = """
Ты эксперт по мотоциклам и питбайкам.

Проанализируй фотографию.

Попробуй определить:
1. Производителя
2. Модель
3. Примерный год
4. Тип мотоцикла
5. Примерный объём двигателя, если это можно определить
6. Отличительные признаки, по которым ты сделал вывод

Если точную модель определить невозможно — НЕ выдумывай.
Укажи наиболее вероятные варианты и объясни почему.

Ответ дай на русском языке и простыми словами.
"""

    response = client.responses.create(
        model="gpt-5.6",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    },
                    {
                        "type": "input_image",
                        "image_url": (
                            f"data:{content_type};base64,{image_base64}"
                        )
                    }
                ]
            }
        ]
    )

    return jsonify({
        "result": response.output_text
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
