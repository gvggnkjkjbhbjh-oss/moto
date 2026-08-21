import os
import base64

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Максимальный размер изображения: 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

# Проверяем переменную окружения с ключом OpenAI
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения")
client = OpenAI(api_key=api_key)

MODEL = "gpt-5.6"

@app.get("/")
def home():
    return "Moto AI server is working!"

@app.get("/test")
def test():
    try:
        print("TEST: проверяем OpenAI...")
        response = client.responses.create(
            model=MODEL,
            input="OK"  # простой тестовый запрос
        )
        answer = response.output_text
        print("TEST: OpenAI ответил:", answer)
        return jsonify({"ok": True, "openai": answer, "model": MODEL})
    except Exception as error:
        print("TEST ERROR:", repr(error))
        return jsonify({"ok": False, "error": str(error)}), 500

def get_uploaded_image():
    # Ищем файл в request.files под ожидаемыми именами
    if request.files:
        print("ANALYZE: получены файлы:", list(request.files.keys()))
        preferred = ["file", "photo", "image", "picture", "img"]
        for name in preferred:
            if name in request.files:
                file = request.files[name]
                if file.filename:
                    print(f"ANALYZE: найден файл '{name}': {file.filename}")
                    return file
        # Если под обычными именами не найден, берём первый файл
        for name, file in request.files.items():
            if file.filename:
                print(f"ANALYZE: найден файл (необычное имя) '{name}': {file.filename}")
                return file

    # Если запрос без multipart (raw image)
    if request.data:
        content_type = request.content_type or ""
        if content_type.startswith("image/"):
            print("ANALYZE: изображение получено в теле запроса (raw data)")
            return None  # обозначаем, что файл придёт через request.data

    return None

@app.post("/analyze")
def analyze():
    try:
        print("="*50)
        print("ANALYZE: новый запрос")
        print("Content-Type:", request.content_type)
        print("Content-Length:", request.content_length)
        print("Files:", list(request.files.keys()))
        print("Form:", list(request.form.keys()))
        print("="*50)

        # Пытаемся получить файл
        uploaded_file = get_uploaded_image()

        image_bytes = None
        mime_type = None
        filename = None

        if uploaded_file is not None:
            # Файл в multipart/form-data
            image_bytes = uploaded_file.read()
            mime_type = uploaded_file.content_type or "image/jpeg"
            filename = uploaded_file.filename
        elif request.data:
            # Файл пришёл raw в теле
            content_type = request.content_type or ""
            if content_type.startswith("image/"):
                image_bytes = request.data
                mime_type = content_type
                filename = "uploaded_image"

        # Проверки
        if not image_bytes:
            print("ANALYZE ERROR: изображение не получено")
            return jsonify({
                "ok": False,
                "error": "Изображение не получено. Ожидается файл в multipart/form-data или raw image/* в теле."
            }), 400

        # Проверяем MIME-тип
        allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
        if mime_type not in allowed:
            print("ANALYZE: неизвестный MIME:", mime_type)
            if not mime_type.startswith("image/"):
                mime_type = "image/jpeg"
        print(f"ANALYZE: файл '{filename}', тип: {mime_type}, размер: {len(image_bytes)} байт")

        # Конвертация в base64 data URL
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{mime_type};base64,{image_b64}"

        # Формируем запрос к OpenAI
        prompt = (
            "Ты — Moto AI, помощник по мотоциклам. "
            "Проанализируй фотографию. "
            "Если на изображении есть мотоцикл или другой двухколёсный транспорт, определи: "
            "марку, модель, приблизительный год, объём и тип двигателя (если можно), "
            "значимые особенности. Если модель точно не установить, честно укажи, что определил и насколько уверен. "
            "Отвечай кратко и по-русски."
        )

        print("ANALYZE: отправляем изображение в OpenAI...")
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": image_data_url}
                    ]
                }
            ]
        )
        answer = response.output_text
        print("ANALYZE: OpenAI ответ:", answer)

        return jsonify({"ok": True, "result": answer, "model": MODEL})

    except Exception as error:
        print("ANALYZE ERROR:", repr(error))
        return jsonify({"ok": False, "error": str(error)}), 500

@app.errorhandler(413)
def handle_too_large(error):
    return jsonify({"ok": False, "error": "Изображение слишком большое (макс 20 MB)."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
