from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import urllib.parse

app = FastAPI()

BOT_TOKEN = "8424346441:AAF7YxEtUeKvuNZ_nqGpEG2XVCwhhXBqFxU"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
PERPLEXITY_API = "https://perplex-city.vercel.app/search"
CHATGPT_API = "https://chat-gpt-six-tan.vercel.app/chat?text="
GEMINI_IMAGE_API = "https://gemini-image-generator-api.vercel.app/?prompt="

async def send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    url = f"{TELEGRAM_API}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=data)
        return response.json()

async def send_photo(chat_id: int, photo_url: str, caption: str = None):
    url = f"{TELEGRAM_API}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, data=data)
        return response.json()

async def edit_message(chat_id: int, message_id: int, text: str, parse_mode: str = "Markdown"):
    url = f"{TELEGRAM_API}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=data)
        return response.json()

async def search_perplexity(query: str):
    encoded_query = urllib.parse.quote(query)
    url = f"{PERPLEXITY_API}?message={encoded_query}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        return None

async def ask_chatgpt(query: str):
    encoded_query = urllib.parse.quote(query)
    url = f"{CHATGPT_API}{encoded_query}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        return None

@app.get("/")
async def home():
    return {"status": "ok", "message": "Mero AI Assistant Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        if "message" not in data:
            return JSONResponse({"ok": True})

        message = data["message"]
        chat_id = message["chat"]["id"]

        if "text" not in message:
            return JSONResponse({"ok": True})

        text = message["text"]

        if text == "/start":
            welcome = (
                "👋 Welcome to *Mero AI Assistant!*\n\n"
                "You can:\n"
                "• Ask anything normally (ChatGPT powered)\n"
                "• Use /search <query> for Perplexity AI search\n"
                "• Use /imagine <prompt> to generate AI images\n\n"
                "Let's get started!"
            )
            await send_message(chat_id, welcome)
            return JSONResponse({"ok": True})

        if text.startswith("/"):
            if text.startswith("/search"):
                query = text.replace("/search", "", 1).strip()
                if not query:
                    await send_message(chat_id, "Please provide something to search.")
                    return JSONResponse({"ok": True})
                searching = await send_message(chat_id, "🔍 Searching... Please wait.")
                if not searching.get("ok"):
                    return JSONResponse({"ok": True})
                msg_id = searching["result"]["message_id"]
                try:
                    result = await search_perplexity(query)
                    if result and result.get("status_code") == 200:
                        ai_response = result.get("response", "No response available.")
                        await edit_message(chat_id, msg_id, ai_response)
                    else:
                        error_msg = result.get("message", "Unable to get answer") if result else "API error"
                        await edit_message(chat_id, msg_id, f"Error: {error_msg}")
                except httpx.TimeoutException:
                    await edit_message(chat_id, msg_id, "Request timeout. Please try again.")
                except Exception as e:
                    await edit_message(chat_id, msg_id, f"An error occurred: {str(e)}")
                return JSONResponse({"ok": True})

            if text.startswith("/imagine"):
                prompt = text.replace("/imagine", "", 1).strip()
                if not prompt:
                    await send_message(chat_id, "Please provide a description to generate an image.")
                    return JSONResponse({"ok": True})
                await send_message(chat_id, "🎨 Generating your AI image... Please wait.")
                image_url = f"{GEMINI_IMAGE_API}{urllib.parse.quote(prompt)}"
                await send_photo(chat_id, image_url, "Here's your AI image is generated.")
                return JSONResponse({"ok": True})

            return JSONResponse({"ok": True})

        query = text.strip()
        thinking = await send_message(chat_id, "🤖 Thinking... Please wait.")
        if not thinking.get("ok"):
            return JSONResponse({"ok": True})
        msg_id = thinking["result"]["message_id"]
        try:
            result = await ask_chatgpt(query)
            if result and "message" in result:
                ai_response = result["message"]
                await edit_message(chat_id, msg_id, ai_response)
            else:
                await edit_message(chat_id, msg_id, "Error fetching response from ChatGPT API.")
        except httpx.TimeoutException:
            await edit_message(chat_id, msg_id, "Request timeout. Please try again.")
        except Exception as e:
            await edit_message(chat_id, msg_id, f"An error occurred: {str(e)}")

        return JSONResponse({"ok": True})

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse({"ok": True})