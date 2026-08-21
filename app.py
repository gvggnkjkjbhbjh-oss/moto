import os

import base64

from flask import Flask, jsonify, request

from flask_cors import CORS

from openai import OpenAI

app = Flask(__name__)

CORS(app)

# =========================

# OPENAI

# =========================

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:

    raise RuntimeError(

        "OPENAI_API_KEY не найден в Render Environment Variables"

    )

client = OpenAI(api_key=api_key)

# =========================

# ГЛАВНАЯ

# =========================

@app.get("/")

def home():

    return "Moto AI server is working!"

# =========================

# ПРОВЕРКА OPENAI

# =========================

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

# =========================

# РАСПОЗНАВАНИЕ ФОТО

# =========================

@app.post("/analyze")

def analyze():

    try:

        print("ANALYZE: получен запрос")

        # Проверяем, пришёл ли файл

        if "file" not in request.files:

            print("ANALYZE ERROR: файл не найден")

            return jsonify({

                "ok": False,

                "error": "Файл изображения не найден. Ожидается поле 'file'."

            }), 400

        image = request.files["file"]

        # Проверяем имя файла

        if not image.filename:

            return jsonify({

                "ok": False,

                "error": "Изображение не выбрано."

            }), 400

        print("ANALYZE: файл:", image.filename)

        # Читаем изображение

        image_bytes = image.read()

        if not image_bytes:

            return jsonify({

                "ok": False,

                "error": "Получен пустой файл изображения."

            }), 400

        print(

            "ANALYZE: размер изображения:",

            len(image_bytes),

            "байт"

        )

        # Определяем MIME-тип

        mime_type = image.content_type or "image/jpeg"

        # Переводим изображение в base64

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        image_data_url = (

            f"data:{mime_type};base64,{image_base64}"

        )

        print("ANALYZE: отправляем изображение в OpenAI")

        # Запрос к OpenAI

        response = client.responses.create(

            model="gpt-5.6",

            input=[

                {

                    "role": "user",

                    "content": [

                        {

                            "type": "input_text",

                            "text": (

                                "Ты Moto AI — помощник по мотоциклам. "

                                "Проанализируй изображение. "

                                "Если на фото есть мотоцикл, питбайк, "

                                "эндуро или другой двухколёсный транспорт, "

                                "определи максимально точно: "

                                "марку, модель, примерный год, "

                                "объём двигателя, если его можно определить, "

                                "и другие заметные особенности. "

                                "Если точно определить модель нельзя, "

                                "честно укажи, что именно удалось определить "

                                "и насколько уверенно. "

                                "Не выдумывай характеристики."

                            )

                        },

                        {

                            "type": "input_image",

                            "image_url": image_data_url

                        }

                    ]

                }

            ]

        )

        answer = response.output_text

        print("ANALYZE: OpenAI ответил:")

        print(answer)

        return jsonify({

            "ok": True,

            "result": answer

        })

    except Exception as error:

        print("ANALYZE ERROR:", repr(error))

        return jsonify({

            "ok": False,

            "error": str(error)

        }), 500

# =========================

# ЗАПУСК

# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(

        host="0.0.0.0",

        port=port

    )
