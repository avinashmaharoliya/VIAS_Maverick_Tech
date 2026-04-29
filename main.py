import socket, struct, pickle, time, threading
import cv2, numpy as np

from vision import detect_objects, detect_fall
from audio import listen, parse_command
from actions import speak, call, message

# ================= CONFIG =================
HOST = "0.0.0.0"
PORT = 5000

CONTACTS = {
    "amul": "7338604128",
    "shivanshu": "9110227325"
}

EMERGENCY_NUMBER = "7338604128"

# ================= SOCKET =================
server = socket.socket()
server.bind((HOST, PORT))
server.listen(1)

print("🟡 Waiting for Pi...")
conn, addr = server.accept()
print("🟢 Connected:", addr)

# ================= STATE =================
latest_frame = None
distance = 999
imu = {}

mode = "obstacle"
prev_obj = None

# FALL STATE
waiting_for_response = False
fall_time = 0

# ================= DISPLAY =================
def show_frame(frame, obj, distance, mode):
    display = frame.copy()

    if obj:
        cv2.putText(display, f"Object: {obj}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.putText(display, f"Distance: {int(distance)} cm", (20,80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

    cv2.putText(display, f"Mode: {mode}", (20,120),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)

    cv2.imshow("Vision Debug", display)

# ================= RECEIVE =================
def receive_loop():
    global latest_frame, distance, imu

    data = b""
    payload_size = struct.calcsize("Q")

    while True:
        try:
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet:
                    return
                data += packet

            packed = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed)[0]

            while len(data) < msg_size:
                data += conn.recv(4096)

            msg_data = data[:msg_size]
            data = data[msg_size:]

            msg = pickle.loads(msg_data)

            print("📥 Frame received")

            # FRAME DECODE
            frame_bytes = msg["frame"]
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is not None:
                latest_frame = frame

            distance = msg["distance"]
            imu = msg["imu"]

            print("IMU:", imu)

        except Exception as e:
            print("❌ Receive error:", e)
            break

# ================= MAIN LOOP =================
def main_loop():
    global mode, prev_obj, waiting_for_response, fall_time

    print("Press 'v' to speak | ESC to exit")

    while True:
        if latest_frame is None:
            continue

        # ===== DETECTION =====
        obj = detect_objects(latest_frame)

        # ===== DISPLAY =====
        show_frame(latest_frame, obj, distance, mode)

        # ================= FALL DETECTION =================
        if detect_fall(imu) and not waiting_for_response:
            print("⚠️ FALL DETECTED")
            speak(conn, "Fall detected. Are you okay?")
            fall_time = time.time()
            waiting_for_response = True

        # ===== FALL TIMEOUT =====
        if waiting_for_response:
            if time.time() - fall_time > 10:
                print("🚨 No response → sending emergency")
                speak(conn, "No response. Sending emergency message")
                message(EMERGENCY_NUMBER)
                waiting_for_response = False

        # ================= OBSTACLE MODE =================
        if mode == "obstacle":

            if distance < 50:
                print("⚠️ Obstacle very close")
                speak(conn, "Stop. Obstacle very close")

            elif obj and obj != prev_obj:
                print(f"👁 Detected: {obj}")
                speak(conn, f"{obj} ahead")
                prev_obj = obj

            elif obj is None:
                speak(conn, "Path clear")
                prev_obj = None

        # ================= KEY INPUT =================
        key = cv2.waitKey(1) & 0xFF

        if key == ord('v'):
            mode = "command"

            print("🎤 Listening...")
            text = listen()
            print("🧠 You said:", text)

            intent, raw = parse_command(text)
            print("Intent:", intent)

            # ===== FALL RESPONSE =====
            if intent == "ok" and waiting_for_response:
                print("✅ User is safe")
                speak(conn, "Okay, cancelling alert")
                waiting_for_response = False

            # ===== CALL =====
            elif intent == "call":
                found = False
                for name in CONTACTS:
                    if name in raw:
                        call(CONTACTS[name])
                        speak(conn, f"Calling {name}")
                        found = True
                        break
                if not found:
                    speak(conn, "Contact not found")

            # ===== MESSAGE =====
            elif intent == "message":
                found = False
                for name in CONTACTS:
                    if name in raw:
                        message(CONTACTS[name])
                        speak(conn, f"Message sent to {name}")
                        found = True
                        break
                if not found:
                    speak(conn, "Contact not found")

            # ===== SCENE (LOCAL) =====
            elif intent == "scene":
                if obj:
                    speak(conn, f"I see a {obj} in front of you")
                else:
                    speak(conn, "I don't see anything important")

            else:
                speak(conn, "Command not recognized")

            mode = "obstacle"

        # ===== EXIT =====
        if key == 27:
            break

    cv2.destroyAllWindows()

# ================= START =================
threading.Thread(target=receive_loop, daemon=True).start()

main_loop()