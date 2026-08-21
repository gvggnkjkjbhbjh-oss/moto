import os

import base64

from flask import Flask, jsonify, request

from flask_cors import CORS

from openai import OpenAI

# ==========================================

# SERVER

# ==========================================

app = Flask(__name__)

CORS(app)

# Ограничение размера изображения: 20 MB

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

# ==========================================

# OPENAI

# ==========================================

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:

    raise RuntimeError(

        "OPENAI_API_KEY не найден в Render Environment Variables"

    )

client = OpenAI(api_key=api_key)

MODEL = "gpt-5.6"

# ==========================================

# ГЛАВНАЯ СТРАНИЦА

# ==========================================

@app.get("/")

def home():

    return "Moto AI server is working!"

# ==========================================

# ПРОВЕРКА OPENAI

# ==========================================

@app.get("/test")

def test():

    try:

        print("TEST: проверяем OpenAI")

        response = client.responses.create(

            model=MODEL,

            input="Ответь одним словом: OK"

        )

        answer = response.output_text

        print("TEST: OpenAI ответил:", answer)

        return jsonify({

            "ok": True,

            "openai": answer,

            "model": MODEL

        })

    except Exception as error:

        print("TEST ERROR:", repr(error))

        return jsonify({

            "ok": False,

            "error": str(error)

        }), 500

# ==========================================

# ПОИСК ИЗОБРАЖЕНИЯ

# ==========================================

def get_uploaded_image():

    # --------------------------------------

    # Вариант 1:

    # multipart/form-data

    # --------------------------------------

    if request.files:

        print(

            "ANALYZE: получены файлы:",

            list(request.files.keys())

        )

        # Сначала пробуем стандартные названия

        preferred_names = [

            "file",

            "photo",

            "image",

            "picture",

            "img"

        ]

        for name in preferred_names:

            if name in request.files:

                uploaded_file = request.files[name]

                if uploaded_file.filename:

                    print(

                        "ANALYZE: найден файл:",

                        name,

                        uploaded_file.filename

                    )

                    return uploaded_file

        # Если название вообще другое —

        # берём первый файл

        for name in request.files:

            uploaded_file = request.files[name]

            if uploaded_file.filename:

                print(

                    "ANALYZE: найден неизвестный файл:",

                    name,

                    uploaded_file.filename

                )

                return uploaded_file

    # --------------------------------------

    # Вариант 2:

    # изображение пришло напрямую в body

    # --------------------------------------

    if request.data:

        content_type = request.content_type or ""

        if content_type.startswith("image/"):

            print(

                "ANALYZE: изображение пришло напрямую в body"

            )

            return None

    return None

# ==========================================

# РАСПОЗНАВАНИЕ

# ==========================================

@app.post("/analyze")

def analyze():

    try:

        print("=" * 50)

        print("ANALYZE: новый запрос")

        print("Content-Type:", request.content_type)

        print("Content-Length:", request.content_length)

        print("Files:", list(request.files.keys()))

        print("Form:", list(request.form.keys()))

        print("=" * 50)

        # ==================================

        # ПОЛУЧАЕМ ФАЙЛ

        # ==================================

        uploaded_file = get_uploaded_image()

        image_bytes = None

        mime_type = None

        filename = None

        # ----------------------------------

        # Файл через multipart/form-data

        # ----------------------------------

        if uploaded_file is not None:

            image_bytes = uploaded_file.read()

            mime_type = (

                uploaded_file.content_type

                or "image/jpeg"

            )

            filename = uploaded_file.filename

        # ----------------------------------

        # Файл напрямую в request body

        # ----------------------------------

        elif request.data:

            content_type = request.content_type or ""

            if content_type.startswith("image/"):

                image_bytes = request.data

                mime_type = content_type

                filename = "uploaded_image"

        # ==================================

        # ПРОВЕРКА

        # ==================================

        if not image_bytes:

            return jsonify({

                "ok": False,

                "error": (

                    "Изображение не получено. "

                    "Сервер ожидает фотографию "

                    "в multipart/form-data или image/* body."

                ),

                "received_files": list(

                    request.files.keys()

                )

            }), 400

        # ==================================

        # ПРОВЕРКА MIME

        # ==================================

        allowed_types = [

            "image/jpeg",

            "image/jpg",

            "image/png",

            "image/webp",

            "image/gif"

        ]

        if mime_type not in allowed_types:

            print(

                "ANALYZE: неизвестный MIME:",

                mime_type

            )

            # Для некоторых Telegram/HTTP клиентов

            # MIME может отсутствовать.

            # В таком случае JPEG считаем безопасным

            # вариантом по умолчанию.

            if not mime_type.startswith("image/"):

                mime_type = "image/jpeg"

        # ==================================

        # РАЗМЕР

        # ==================================

        print(

            "ANALYZE: файл:",

            filename

        )

        print(

            "ANALYZE: тип:",

            mime_type

        )

        print(

            "ANALYZE: размер:",

            len(image_bytes),

            "байт"

        )

        # ==================================

        # BASE64

        # ==================================

        image_base64 = base64.b64encode(

            image_bytes

        ).decode("utf-8")

        image_data_url = (

            f"data:{mime_type};base64,{image_base64}"

        )

        # ==================================

        # PROMPT

        # ==================================

        prompt = """

Ты — Moto AI, помощник по мотоциклам.

Проанализируй фотографию.

Если на изображении есть мотоцикл,

питбайк, эндуро или другой двухколёсный

моторный транспорт, определи максимально

точно:

1. Марку.

2. Модель.

3. Примерный год.

4. Объём двигателя, если его можно определить.

5. Тип двигателя, если можно определить.

6. Размер колёс, если это можно определить.

7. Заметные особенности комплектации.

8. Какие детали или признаки помогли определить модель.

Если точную модель определить невозможно,

не выдумывай.

В таком случае напиши:

- что удалось определить точно;

- что является предположением;

- какие дополнительные признаки нужны

  для более точного определения.

Отвечай на русском языке.

Будь кратким, но информативным.

"""

        # ==================================

        # OPENAI

        # ==================================

        print(

            "ANALYZE: отправляем изображение в OpenAI..."

        )

        response = client.responses.create(

            model=MODEL,

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

                            "image_url": image_data_url

                        }

                    ]

                }

            ]

        )

        # ==================================

        # ОТВЕТ

        # ==================================

        answer = response.output_text

        print(

            "ANALYZE: OpenAI ответ:",

            answer

        )

        return jsonify({

            "ok": True,

            "result": answer,

            "model": MODEL

        })

    # ======================================

    # ОШИБКА

    # ======================================

    except Exception as error:

        print("=" * 50)

        print("ANALYZE ERROR")

        print(repr(error))

        print("=" * 50)

        return jsonify({

            "ok": False,

            "error": str(error)

        }), 500

# ==========================================

# ОШИБКА СЛИШКОМ БОЛЬШОГО ФАЙЛА

# ==========================================

@app.errorhandler(413)

def file_too_large(error):

    return jsonify({

        "ok": False,

        "error": (

            "Изображение слишком большое. "

            "Максимальный размер — 20 MB."

        )

    }), 413

# ==========================================

# ЗАПУСК

# ==========================================

if __name__ == "__main__":

    port = int(

        os.environ.get(

            "PORT",

            10000

        )

    )

    app.run(

        host="0.0.0.0",

        port=port

    )
