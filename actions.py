import pickle
import struct
from groq import Groq
import base64
import cv2
import os 
from dotenv import load_dotenv
from twilio.rest import Client
import subprocess
load_dotenv()

ADB_PATH = r"C:\Users\monty\Desktop\platform-tools\adb.exe"
ACCOUNT_SID = os.getenv("YOUR_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("YOUR_AUTH_TOKEN")
TWILIO_NUMBER = "+14155238886"     # Twilio number
TARGET_NUMBER = "+917338604128"   # Your phone


api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


CONTACTS = {
    "amul": "7338604128",
    "mom": "9XXXXXXXXX",
    "dad": "9XXXXXXXXX"
}



def speak(conn, text):
    try:
        payload = pickle.dumps({"type": "speech", "text": text})
        msg = struct.pack("Q", len(payload)) + payload
        conn.sendall(msg)
        print("🗣", text)
    except:
        print("❌ Speak failed")


def send_control(conn, command):
    try:
        payload = pickle.dumps({"type": "control", "command": command})
        msg = struct.pack("Q", len(payload)) + payload
        conn.sendall(msg)
        print("🎮 Control:", command)
    except:
        print("❌ Control send failed")


def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


def describe_scene(frame,query):
    if frame is None:
        return "I cannot see anything right now."

    try:
        print("🧠 Calling Groq...")

        img_base64 = encode_frame(frame)

        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistive AI for a blind person. "
                               "only answer what is being asked"
                               "Speak in short, clear sentences. "
                               "Only mention important objects, obstacles, and people. "
                               "Focus on navigation and safety. "
                               "Do not describe colors or unnecessary details. "
                               "Prioritize what is directly ahead."
                               
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=120
        )

        return completion.choices[0].message.content

    except Exception as e:
        print("❌ Groq error:", e)
        return "Sorry, I could not understand the scene."




def send_sos_sms():
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)

        message = client.messages.create(
            from_='whatsapp:+14155238886',
            body='🚨 EMERGENCY: Fall detected. No response!',
            to='whatsapp:+917338604128'
        )

        print("📩 WhatsApp sent:", message.sid)

    except Exception as e:
        print("❌ WhatsApp failed:", e)


def make_call(name=None):
        number = "7338604128"

        subprocess.run([
            ADB_PATH,
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.CALL",
            "-d",
            f"tel:{number}"
        ])



def send_message():
    print("📩 DEMO: Sending message...")