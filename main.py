import socket
import struct
import pickle
import cv2
import numpy as np
import threading
import time
import requests
from vision import detect_objects, detect_fall
from audio import listen, parse_command
from actions import speak, send_control, send_sos_sms, make_call, send_message, describe_scene

HOST = "0.0.0.0"
PORT = 5000

server = socket.socket()
server.bind((HOST, PORT))
server.listen(1)

print("🟡 Waiting for Pi...")
conn, addr = server.accept()
print("🟢 Connected:", addr)

latest_frame = None
distance = 999
imu = {}

system_paused = False
fall_mode = False
fall_time = 0
last_listen_time = 0
last_speak_time = 0

# 🔥 NEW
speech_done = False

# ===== NAVIGATION DATA =====
API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQ0OTQyZmVkYzJmNzQ2MTJhNjlmNjQ3MjZiMTc2YmRjIiwiaCI6Im11cm11cjY0In0="  # 🔥 put your OpenRouteService key

LOCATIONS = {
    "jaydeva": (12.916669657724684, 77.5999047026877),
    "home": (12.916669657724684, 77.5999047026877)
}


def get_route(start, end):
    url = "https://api.openrouteservice.org/v2/directions/foot-walking"

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [
            [start[1], start[0]],   # lon, lat
            [end[1], end[0]]
        ]
    }

    response = requests.post(url, json=body, headers=headers)

    if response.status_code != 200:
        print("❌ Route error:", response.text)
        return

    data = response.json()

    steps = data["features"][0]["properties"]["segments"][0]["steps"]

    print("\n🧭 ROUTE INSTRUCTIONS:\n")

    for i, step in enumerate(steps):
        print(f"{i+1}. {step['instruction']} ({round(step['distance'],1)} m)")


def receive_loop():
    global latest_frame, distance, imu, speech_done

    data = b""
    payload_size = struct.calcsize("Q")

    while True:
        try:
            while len(data) < payload_size:
                data += conn.recv(4096)

            packed = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed)[0]

            while len(data) < msg_size:
                data += conn.recv(4096)

            msg_data = data[:msg_size]
            data = data[msg_size:]

            msg = pickle.loads(msg_data)

            if msg["type"] == "video":
                frame = cv2.imdecode(
                    np.frombuffer(msg["frame"], dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                latest_frame = frame
                distance = msg["distance"]
                imu = msg["imu"]

            # 🔥 NEW: speech sync
            elif msg["type"] == "speech_done":
                print("✅ Speech finished")
                speech_done = True

        except:
            print("❌ Receive error")
            break


def main_loop():
    global system_paused, fall_mode, fall_time, last_listen_time, last_speak_time, speech_done

    last_detect_time = 0
    objects = []

    print("Press 'v' for command | ESC to exit")

    while True:

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        # ===== MANUAL MODE =====
        if key == ord('v'):
            system_paused = True
            send_control(conn, "pause")

            speak(conn, "What do you want to do?")
            text = listen()
            result = parse_command(text)
            if result is None:
                cmd,value = None,None
            else:
                cmd,value = result

            if cmd == "describe":

                if latest_frame is None:
                    speak(conn, "I cannot see anything right now")
                else:
                    desc = describe_scene(latest_frame,text)

                    # 🔥 UPDATED: no time guess, wait for real speech end
                    speech_done = False
                    speak(conn, desc)

                    while not speech_done:
                        time.sleep(0.05)

            elif cmd == "call":
                speak(conn,"calling now")
                make_call("amul")

            elif cmd == "message":
                send_message()

            elif cmd == "navigate":

                if value and value in LOCATIONS:

                    destination = LOCATIONS[value]

        # 🔥 TEMP current location (replace later with GPS)
                    current_location = (12.909565813620755, 77.56684097855906)

                    print(f"\n🧭 Navigating to {value}...\n")

                    get_route(current_location, destination)

                    speak(conn, f"Route to {value} ready")

                else:
                    speak(conn, "Location not found")

                system_paused = False

            system_paused = False
            send_control(conn, "resume")

        if system_paused:
            time.sleep(0.1)
            continue

        if latest_frame is None:
            continue

        frame = latest_frame.copy()

        # ===== FALL MODE =====
        if fall_mode:
            elapsed = time.time() - fall_time

            if time.time() - last_listen_time > 3:
                last_listen_time = time.time()

                speak(conn, "Are you okay?")
                text = listen()

                if "ok" in text:
                    speak(conn, "Okay cancelling alert")
                    fall_mode = False
                    continue

            if elapsed > 15:
                speak(conn, "No response, sending SOS")
                speech_done = False
                while not speech_done:
                    time.sleep(0.05)

                send_sos_sms()
                fall_mode = False

            continue

        # ===== FALL DETECTION =====
        if detect_fall(imu):
            speak(conn, "Fall detected. Are you okay?")
            fall_mode = True
            fall_time = time.time()
            continue

        # ===== YOLO =====
        if time.time() - last_detect_time > 0.5:
            objects = detect_objects(frame)
            last_detect_time = time.time()

        # ===== OBJECT SPEECH =====
        if objects and time.time() - last_speak_time > 2:
            label, pos, _ = objects[0]
            speak(conn, f"{label} {pos.lower()}")
            last_speak_time = time.time()

        # ===== DISPLAY =====
        h, w = frame.shape[:2]

        cv2.line(frame, (w//3, 0), (w//3, h), (255,0,0), 2)
        cv2.line(frame, (2*w//3, 0), (2*w//3, h), (255,0,0), 2)

        for label, pos, (x1,y1,x2,y2) in objects:
            cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame, f"{label}-{pos}",
                        (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,(0,255,255),2)

        cv2.putText(frame, f"Dist: {int(distance)} cm",
                    (20,40), cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

        cv2.imshow("Vision Assist", frame)

        time.sleep(0.01)

    cv2.destroyAllWindows()


threading.Thread(target=receive_loop, daemon=True).start()
main_loop()