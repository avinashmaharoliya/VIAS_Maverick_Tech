import os, time, pickle, struct, requests, cv2

last_spoken = ""
last_time = 0
COOLDOWN = 2

def speak(conn, text):
    global last_spoken, last_time

    now = time.time()

    if text == last_spoken and (now - last_time < COOLDOWN):
        return

    payload = pickle.dumps({"type": "speech", "text": text})
    msg = struct.pack("Q", len(payload)) + payload
    conn.sendall(msg)

    print("🗣", text)

    last_spoken = text
    last_time = now


def call(number):
    os.system(f'adb shell am start -a android.intent.action.DIAL -d tel:{number}')


def message(number):
    os.system(
        f'adb shell am start -a android.intent.action.SENDTO '
        f'-d sms:{number} --es sms_body "Emergency alert"'
    )


def ask_gemini(frame, question, api_key):
    _, img = cv2.imencode(".jpg", frame)

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"

    payload = {
        "contents":[
            {"parts":[{"text": question}]}
        ]
    }

    res = requests.post(url, json=payload)
    return res.text[:200]