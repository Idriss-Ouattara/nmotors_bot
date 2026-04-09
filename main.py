from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import os
import json

app = FastAPI()

# Configuration
API_KEY = os.environ.get("MISTRAL_API_KEY", "NFbCfDpi9y2W0BQ0jkZmWuXX9sXd2DZO")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Mémoire des conversations
historique = {}

class Message(BaseModel):
    texte: str
    user_id: str

def call_mistral(messages):
    """Appelle l'API Mistral directement en HTTP"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "open-mistral-7b",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(MISTRAL_URL, headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"Erreur API: {response.status_code} - {response.text}")
        return "Désolé, je rencontre une erreur technique."
    
    result = response.json()
    return result["choices"][0]["message"]["content"]

@app.post("/message")
def recevoir_message(msg: Message):
    # Créer l'historique si nouveau client
    if msg.user_id not in historique:
        historique[msg.user_id] = []
    
    # Ajouter le message du client
    historique[msg.user_id].append({
        "role": "user",
        "content": msg.texte
    })
    
    # Construire les messages avec le système
    messages = [
        {
            "role": "system",
            "content": "Tu es l'assistant de NMotors, un service de covoiturage au Cameroun. Réponds en français de façon courte et sympathique."
        }
    ] + historique[msg.user_id]
    
    # Appeler Mistral
    reponse = call_mistral(messages)
    
    # Sauvegarder la réponse
    historique[msg.user_id].append({
        "role": "assistant",
        "content": reponse
    })
    
    return {"reponse": reponse}

# Configuration WhatsApp
VERIFY_TOKEN = "mon_token_secret"
TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID", "")

@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"error": "verification failed"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print(data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        texte = message["text"]["body"]
        user_id = message["from"]

        if user_id not in historique:
            historique[user_id] = []

        historique[user_id].append({
            "role": "user",
            "content": texte
        })

        messages = [
            {
                "role": "system",
                "content": "Assistant NMotors, réponds court en français"
            }
        ] + historique[user_id]

        reponse = call_mistral(messages)

        historique[user_id].append({
            "role": "assistant",
            "content": reponse
        })

        send_whatsapp_message(user_id, reponse)

    except Exception as e:
        print("Erreur:", e)

    return {"status": "ok"}

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)