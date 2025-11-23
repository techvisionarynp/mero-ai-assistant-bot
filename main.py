from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import urllib.parse

app = FastAPI()

BOT_TOKEN = "8424346441:AAF7YxEtUeKvuNZ_nqGpEG2XVCwhhXBqFxU"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
FELO_AI_API = "https://yabes-api.pages.dev/api/ai/chat/felo-ai?query="
CHATGPT_API = "https://text.pollinations.ai/"

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

async def search_felo_ai(query: str):
    encoded_query = urllib.parse.quote(query)
    url = f"{FELO_AI_API}{encoded_query}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            results_text = data.get('results', '')
            if "📚 References:" in results_text:
                news_part, references_part = results_text.split("📚 References:")
                news_part = news_part.strip()
                references_part = references_part.strip().split("\n- ")
                references_part = [ref.strip("- ").strip() for ref in references_part if ref.strip()]
            else:
                news_part = results_text
                references_part = []
            return news_part, references_part
        return None, None

async def ask_chatgpt(query: str):
    encoded_query = urllib.parse.quote(query)
    url = f"{CHATGPT_API}{encoded_query}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
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
                "• Use /search <query> for Felo AI search\n"
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
                await send_message(chat_id, "🔍 Searching... Please wait.")
                try:
                    news, references = await search_felo_ai(query)
                    if news:
                        refs_text = ""
                        for i, ref in enumerate(references):
                            if ref.startswith("http://") or ref.startswith("https://"):
                                refs_text += f"{i+1}. [Reference]({ref})\n"
                            else:
                                refs_text += f"{i+1}. {ref}\n"
                        final_text = f"{news}"
                        if references:
                            final_text += f"\n\nReferences:\n{refs_text.strip()}"
                        await send_message(chat_id, final_text)
                    else:
                        await send_message(chat_id, "Error: Unable to fetch news from Felo AI.")
                except httpx.TimeoutException:
                    await send_message(chat_id, "Request timeout. Please try again.")
                except Exception as e:
                    await send_message(chat_id, f"An error occurred: {str(e)}")
                return JSONResponse({"ok": True})
            if text.startswith("/imagine"):
                prompt = text.replace("/imagine", "", 1).strip()
                if not prompt:
                    await send_message(chat_id, "Please provide a description to generate an image.")
                    return JSONResponse({"ok": True})
                await send_message(chat_id, "🎨 Generating your AI image... Please wait.")
                encoded_prompt = urllib.parse.quote(prompt)
                image_api_url = f"https://yabes-api.pages.dev/api/ai/image/imagen3-0?prompt={encoded_prompt}&ratio=16%3A9"
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.get(image_api_url)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success") and "url" in data:
                                image_url = data["url"]
                                await send_photo(chat_id, image_url, "Here’s your AI-generated image.")
                            else:
                                await send_message(chat_id, "Error: Image API did not return a valid URL.")
                        else:
                            await send_message(chat_id, f"Error: Image API returned status {response.status_code}.")
                except httpx.TimeoutException:
                    await send_message(chat_id, "Request timeout. Please try again.")
                except Exception as e:
                    await send_message(chat_id, f"An error occurred: {str(e)}")
                return JSONResponse({"ok": True})
            return JSONResponse({"ok": True})
        query = text.strip()
        thinking = await send_message(chat_id, "🤖 GPT-4 is preparing a response... Please wait.")
        if not thinking.get("ok"):
            return JSONResponse({"ok": True})
        try:
            result = await ask_chatgpt(query)
            if result:
                await send_message(chat_id, result)
            else:
                await send_message(chat_id, "Error fetching response from ChatGPT API.")
        except httpx.TimeoutException:
            await send_message(chat_id, "Request timeout. Please try again.")
        except Exception as e:
            await send_message(chat_id, f"An error occurred: {str(e)}")
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse({"ok": True})
