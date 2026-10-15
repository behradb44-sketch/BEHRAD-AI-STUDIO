import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="BEHRAD AI STUDIO")

API_BASE = os.getenv(
    "GAPGPT_BASE_URL",
    "https://api.gapgpt.app/v1"
).rstrip("/")

API_KEY = os.getenv("GAPGPT_API_KEY", "").strip()
MODEL = os.getenv("GAPGPT_MODEL", "claude-fable-5-1")


class ChatRequest(BaseModel):
    message: str


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL,
        "api_key_configured": bool(API_KEY)
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API Key در تنظیمات سرور ثبت نشده است."
        )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are BEHRAD AI, a helpful AI assistant. "
                    "Answer in the user's language. "
                    "Help with programming and explain code clearly."
                )
            },
            {
                "role": "user",
                "content": request.message
            }
        ],
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"خطای API: HTTP {response.status_code}"
            )

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        if isinstance(answer, list):
            answer = "\n".join(
                item.get("text", "")
                for item in answer
                if isinstance(item, dict)
            )

        return {
            "reply": str(answer),
            "model": MODEL
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="پاسخ هوش مصنوعی بیش از حد طول کشید."
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="اتصال به سرویس هوش مصنوعی ناموفق بود."
        )

    except (KeyError, ValueError, IndexError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="فرمت پاسخ دریافتی از API معتبر نیست."
        )


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <title>BEHRAD AI STUDIO</title>
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                min-height: 100vh;
                background: #070d1b;
                color: #eef5ff;
                font-family: Tahoma, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 18px;
            }
            .app {
                width: 100%;
                max-width: 700px;
                background: #0d1729;
                border: 1px solid #243653;
                border-radius: 22px;
                padding: 22px;
                box-shadow: 0 0 50px #168bd51c;
            }
            h1 {
                color: #62ddff;
                font-size: 25px;
                margin-bottom: 5px;
            }
            .subtitle {
                color: #92a5c4;
                font-size: 13px;
                margin-bottom: 24px;
            }
            #chat {
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-bottom: 18px;
            }
            .message {
                padding: 13px;
                border-radius: 13px;
                line-height: 1.9;
                overflow-wrap: anywhere;
                white-space: pre-wrap;
                font-size: 14px;
            }
            .user {
                background: #172b48;
            }
            .ai {
                background: #101f34;
                border: 1px solid #223956;
            }
            textarea {
                width: 100%;
                min-height: 100px;
                resize: vertical;
                padding: 13px;
                border: 1px solid #2b4566;
                border-radius: 13px;
                background: #080f1d;
                color: white;
                font: inherit;
                outline: none;
            }
            textarea:focus {
                border-color: #54d9ff;
            }
            button {
                width: 100%;
                margin-top: 10px;
                padding: 13px;
                border: 0;
                border-radius: 12px;
                background: linear-gradient(100deg, #28bfe8, #6571ff);
                color: #07101d;
                font-size: 15px;
                font-weight: bold;
                cursor: pointer;
            }
            button:disabled {
                opacity: .5;
            }
            .foot {
                color: #7285a2;
                font-size: 10px;
                text-align: center;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <main class="app">
            <h1>✦ BEHRAD AI STUDIO</h1>
            <div class="subtitle">
                دستیار هوش مصنوعی و برنامه‌نویسی تو
            </div>

            <section id="chat"></section>

            <textarea id="message"
                placeholder="پیامت رو اینجا بنویس..."></textarea>

            <button id="send" onclick="sendMessage()">
                ارسال پیام ➤
            </button>

            <div class="foot">
                BEHRAD AI ممکن است اشتباه کند.
            </div>
        </main>

        <script>
            const input = document.getElementById("message");
            const chat = document.getElementById("chat");
            const button = document.getElementById("send");

            function addMessage(text, type) {
                const box = document.createElement("div");
                box.className = "message " + type;
                box.textContent = text;
                chat.appendChild(box);
                box.scrollIntoView({behavior: "smooth"});
            }

            async function sendMessage() {
                const message = input.value.trim();
                if (!message || button.disabled) return;

                addMessage(message, "user");
                input.value = "";
                button.disabled = true;
                button.textContent = "در حال دریافت پاسخ...";

                try {
                    const response = await fetch("/api/chat", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({message})
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(
                            data.detail || "خطای نامشخص"
                        );
                    }

                    addMessage(data.reply, "ai");

                } catch (error) {
                    addMessage(
                        "خطا: " + error.message,
                        "ai"
                    );
                } finally {
                    button.disabled = false;
                    button.textContent = "ارسال پیام ➤";
                }
            }

            input.addEventListener("keydown", event => {
                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {
                    event.preventDefault();
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
  )
