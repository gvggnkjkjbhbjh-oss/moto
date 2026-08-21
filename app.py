import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    return "Moto AI server is working!"


@app.get("/test")
def test():
    print("TEST: PuzzleBot successfully reached Render!")

    return jsonify({
        "ok": True,
        "message": "PuzzleBot -> Render работает!"
    })


@app.post("/analyze")
def analyze():
    print("ANALYZE: запрос на распознавание получен!")

    if "photo" not in request.files:
        print("ANALYZE ERROR: фотография не пришла!")

        return jsonify({
            "error": "Фото не пришло на сервер"
        }), 400

    photo = request.files["photo"]

    print(
        "ANALYZE: получен файл:",
        photo.filename,
        photo.content_type
    )

    return jsonify({
        "result": "Фото успешно дошло до Render!"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
