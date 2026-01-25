from fastapi import FastAPI, Request
import os
from datetime import datetime
import requests
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()


try:
    from modules.database import get_db, create_task, send_notification
    supabase = get_db()
except Exception as e:
    print(f"Warning: Could not load database: {e}")
    supabase = None

app = FastAPI()

MANAGER_TELEGRAM_ID = int(os.getenv("MANAGER_TELEGRAM_ID"))
MANAGER_USER_ID = os.getenv("MANAGER_USER_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY_FLASH = os.getenv("GEMINI_API_KEY_FLASH")

genai.configure(api_key=GEMINI_API_KEY_FLASH)


def send_telegram_message(chat_id: int, text: str) -> bool:

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Message sent to {chat_id}")
            return True
        else:
            print(f"❌ Failed to send message: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        return False


def gen_ai_response(prompt: str):
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')   
        response = model.generate_content(prompt, stream=False)                
    except Exception as e:
        return f"Error generating response: {str(e)}"
    return response.text if hasattr(response, 'text') else str(response)



def handle_task_commands(text: str) -> str:
    print("Processing task command...")

    prompt = f"""
Extract task details from the text below and return ONLY and strictly in this format:

title=<task title>
description=<task description>
deadline=<deadline in ISO format with IST timezone>
employee_name=<lowercase employee name>

Rules:
- If no deadline is mentioned, assume 5 PM IST.
- Deadline format example: 2026-01-20T17:00:00+05:30
- No extra text.
- 2026 is current year.

e.g. text: "Assign John Doe to complete the financial report by 12 dec 26."
Expected output:
title=Complete the financial report
description=Complete the financial report
deadline=2026-12-12T17:00:00+05:30
employee_name=john doe


Text:
{text}
"""

    response = gen_ai_response(prompt)
    return response


def parse_task_output(text: str) -> dict:
    print(f"Raw AI output:\n{text}\n")
    lines = [line.strip() for line in text.splitlines() if "=" in line]
    

    data = {}
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()

    print(f"Extracted data: {data}")
    required = {"title", "description", "deadline", "employee_name"}
    missing = required - set(data.keys())
    
    if missing:
        print(f"Missing required fields: {missing}")
        raise ValueError(f"Invalid AI output format. Missing: {missing}")

    return {
        "title": data["title"],
        "description": data["description"],
        "deadline": data["deadline"],
        "employee_name": data["employee_name"]
    }


@app.post("/telegram-webhook")
async def telegram_webhook(req: Request):
    print("✅ Telegram webhook HIT")
    data = await req.json()

    msg = data.get("message")
    if not msg or "text" not in msg:
        return {"ok": True}

    text = msg["text"]
    sender_id = msg["from"]["id"]
    sender_name = msg["from"].get("first_name", "User")

    print(f"📩 Message from {sender_id} ({sender_name}): {text}")
    
    try:
        ai_response = handle_task_commands(f"{text}")
        deatails = parse_task_output(ai_response)
        emp_id = supabase.table('users').select('id').ilike('full_name', deatails['employee_name']).execute().data
        create_task(
            title=deatails['title'],
            desc=deatails['description'],
            emp_id=emp_id[0]['id'] if emp_id else None,
            manager_id=MANAGER_USER_ID,
            due_datetime_iso=deatails['deadline'],
            supabase=supabase
        )
        send_notification(
            supabase,
            recipient_id=emp_id[0]['id'] if emp_id else None,
            content=f"New Task Assigned: {deatails['title']} with deadline {deatails['deadline']}",
            msg_type="new_task"
        )
        send_telegram_message(
            chat_id=sender_id,
            text="✅ Task '{deatails['title']}' assigned to {deatails['employee_name'].title()} with deadline {deatails['deadline']}."
        )
    except Exception as e:
        print(f"❌ Error parsing task: {str(e)}")
        send_telegram_message(
            chat_id=sender_id,
            text=f"Quota exceeded !! Please try again later."
        )
        return {"ok": True, "error": str(e)}
   
    if sender_id != MANAGER_TELEGRAM_ID:
        print(f"⚠️ Sender {sender_id} is not manager {MANAGER_TELEGRAM_ID}")
        return {"ok": True}
    
    return {"ok": True}





