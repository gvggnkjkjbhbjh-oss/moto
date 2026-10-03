import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI


app = Flask(__name__)
CORS(app)


# =========================================================
# OPENAI
# =========================================================

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY не найден в переменных окружения Render"
    )

client = OpenAI(api_key=api_key)

MODEL = "gpt-5.6"


# =========================================================
# PAYMENT / BACKEND
# =========================================================

PAYMENT_BACKEND_URL = os.environ.get("PAYMENT_BACKEND_URL")

if not PAYMENT_BACKEND_URL:
    raise RuntimeError(
        "PAYMENT_BACKEND_URL не найден в переменных окружения Render"
    )


# =========================================================
# MAIN
# =========================================================

@app.get("/")
def home():
    return "MiniMoto Help AI server is working!"


# =========================================================
# OPENAI TEST
# =========================================================

@app.get("/test")
def test():
    try:
        print("TEST: проверяем OpenAI...")

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


# =========================================================
# MINIMOTO HELP AI
# =========================================================

@app.post("/api/ai")
def ai_chat():

    try:

        data = request.get_json(silent=True) or {}

        question = (data.get("question") or "").strip()
        bike = data.get("bike") or {}

        # Telegram initData приходит из Mini App
        telegram_init_data = (
            data.get("telegramInitData") or ""
        )

        # -------------------------------------------------
        # Проверяем вопрос
        # -------------------------------------------------

        if not question:
            return jsonify({
                "ok": False,
                "error": "Вопрос не указан."
            }), 400

        # -------------------------------------------------
        # Проверяем Telegram
        # -------------------------------------------------

        if not telegram_init_data:
            return jsonify({
                "ok": False,
                "error": "Telegram initData не получен."
            }), 401

        # -------------------------------------------------
        # ПРОВЕРКА AI-ДОСТУПА ЧЕРЕЗ PAYMENT BACKEND
        # -------------------------------------------------

        print("AI ACCESS: проверяем пользователя через backend...")

        try:

            access_response = requests.post(
                PAYMENT_BACKEND_URL.rstrip("/") + "/api/ai-access",
                json={
                    "initData": telegram_init_data
                },
                timeout=10
            )

        except requests.RequestException as error:

            print(
                "AI ACCESS REQUEST ERROR:",
                repr(error)
            )

            return jsonify({
                "ok": False,
                "error": "Не удалось проверить доступ к AI."
            }), 503

        # Backend должен вернуть JSON
        try:
            access_data = access_response.json()
        except Exception:

            print(
                "AI ACCESS INVALID RESPONSE:",
                access_response.text
            )

            return jsonify({
                "ok": False,
                "error": "Backend вернул некорректный ответ."
            }), 502

        # -------------------------------------------------
        # Backend отказал
        # -------------------------------------------------

        if not access_response.ok or not access_data.get("ok"):

            print(
                "AI ACCESS BACKEND ERROR:",
                access_response.status_code,
                access_data
            )

            return jsonify({
                "ok": False,
                "error": access_data.get(
                    "error",
                    "Не удалось проверить доступ к AI."
                )
            }), access_response.status_code

        # -------------------------------------------------
        # Проверяем разрешение
        # -------------------------------------------------

        allowed = bool(
            access_data.get("allowed", False)
        )

        if not allowed:

            remaining = access_data.get(
                "remaining",
                0
            )

            return jsonify({
                "ok": False,
                "error": "Лимит бесплатных AI-запросов исчерпан.",
                "code": "AI_LIMIT_REACHED",
                "plan": access_data.get(
                    "plan",
                    "free"
                ),
                "remaining": remaining
            }), 403

        # -------------------------------------------------
        # PRO берём ТОЛЬКО с backend
        # -------------------------------------------------

        is_pro = (
            access_data.get("plan") == "pro"
        )

        remaining = access_data.get(
            "remaining"
        )

        print(
            "AI ACCESS:",
            "PRO" if is_pro else "FREE",
            "remaining:",
            remaining
        )

        # =================================================
        # ДАННЫЕ МОТОЦИКЛА
        # =================================================

        bike_name = bike.get("name") or "не указан"
        bike_year = bike.get("year") or "не указан"
        bike_engine = bike.get("engine") or "не указан"
        bike_wheels = bike.get("wheels") or "не указан"
        bike_mileage = bike.get("mileage") or "не указан"
        bike_hours = bike.get("hours") or "0"
        bike_priority = (
            bike.get("servicePriority")
            or "не указано"
        )

        # =================================================
        # SYSTEM PROMPT
        # =================================================

        system_prompt = """
Ты — MiniMoto Help AI.

Ты являешься помощником владельца питбайков, эндуро
и другой мототехники.

Твоя задача — помогать пользователю:

- с обслуживанием мотоцикла;
- диагностикой неисправностей;
- расходниками;
- запчастями;
- планированием обслуживания;
- моточасами;
- заменой масла;
- цепью и звёздами;
- тормозами;
- подвеской;
- двигателем;
- карбюратором;
- электрикой;
- настройкой мотоцикла;
- объяснением технических терминов.

Всегда учитывай данные конкретного мотоцикла пользователя.

Правила ответа:

1. Отвечай только на русском языке.

2. Пиши понятно и без лишней воды.

3. Если пользователь спрашивает о проблеме,
   объясняй возможные причины по приоритету.

4. Не утверждай, что неисправность точно найдена,
   если по имеющейся информации это определить нельзя.

5. Если информации недостаточно,
   задай конкретный уточняющий вопрос.

6. Не выдумывай характеристики конкретного мотоцикла.

7. Если пользователь спрашивает о детали,
   объясняй, какие характеристики нужно проверить
   перед покупкой.

8. Если пользователь спрашивает про обслуживание,
   давай понятную последовательность действий.

9. Учитывай моточасы и данные мотоцикла пользователя.

10. Не делай вид, что видел мотоцикл или деталь,
    если пользователь не предоставил соответствующую информацию.

11. Если работа требует специальных инструментов
    или может быть опасной, укажи, что её лучше выполнять
    вместе со взрослым или специалистом.

12. Не используй слишком сложные технические термины
    без объяснения.

13. Если есть несколько вариантов решения,
    объясни различия между ними.

14. Не придумывай точные моменты затяжки, зазоры,
    размеры или регламенты, если они неизвестны
    для конкретной модели.
"""

        # =================================================
        # КОНТЕКСТ МОТОЦИКЛА
        # =================================================

        bike_context = f"""
Данные мотоцикла пользователя:

Модель: {bike_name}
Год: {bike_year}
Двигатель: {bike_engine}
Колёса: {bike_wheels}
Пробег: {bike_mileage}
Моточасы: {bike_hours}
Приоритет обслуживания: {bike_priority}

Статус PRO:
{"активен" if is_pro else "не активен"}
"""

        # =================================================
        # USER PROMPT
        # =================================================

        user_prompt = f"""
{bike_context}

Вопрос пользователя:

{question}
"""

        # =================================================
        # LOG
        # =================================================

        print("=" * 60)
        print("MINIMOTO AI: новый запрос")
        print("Question:", question)
        print("Bike:", bike)
        print("PRO:", is_pro)
        print("Remaining:", remaining)
        print("=" * 60)

        # =================================================
        # OPENAI
        # =================================================

        response = client.responses.create(
            model=MODEL,
            instructions=system_prompt,
            input=user_prompt
        )

        answer = response.output_text

        print("MINIMOTO AI: ответ OpenAI:")
        print(answer)

        # =================================================
        # RESPONSE
        # =================================================

        return jsonify({
            "ok": True,
            "answer": answer,
            "model": MODEL,
            "plan": "pro" if is_pro else "free",
            "remaining": remaining
        })

    except Exception as error:

        print(
            "MINIMOTO AI ERROR:",
            repr(error)
        )

        return jsonify({
            "ok": False,
            "error": str(error)
        }), 500


# =========================================================
# SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        )
    )
