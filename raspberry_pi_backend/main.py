import socket
import struct
import pickle
import cv2
import time
import threading
import subprocess
import numpy as np

from picamera2 import Picamera2
import RPi.GPIO as GPIO
import smbus

# ================= CONFIG =================
HOST = "169.254.117.74"   # 🔴 YOUR LAPTOP IP
PORT = 5000

# ================= SOCKET =================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
print("✅ Connected to laptop")

# ================= CAMERA =================
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640,480)}))
picam2.start()

# ================= ULTRASONIC =================
TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

distance_cm = 999

def ultrasonic_loop():
    global distance_cm

    while True:
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        start = time.time()

        while GPIO.input(ECHO) == 0:
            if time.time() - start > 0.02:
                distance_cm = 999
                break
            pulse_start = time.time()

        start = time.time()
        while GPIO.input(ECHO) == 1:
            if time.time() - start > 0.02:
                distance_cm = 999
                break
            pulse_end = time.time()

        try:
            duration = pulse_end - pulse_start
            distance_cm = (duration * 34300) / 2
        except:
            distance_cm = 999

        time.sleep(0.1)

# ================= MPU6050 =================
bus = smbus.SMBus(1)
MPU_ADDR = 0x68
bus.write_byte_data(MPU_ADDR, 0x6B, 0)

imu_data = {"ax":0, "ay":0, "az":0}

def read_word(reg):
    high = bus.read_byte_data(MPU_ADDR, reg)
    low = bus.read_byte_data(MPU_ADDR, reg+1)
    val = (high << 8) + low
    if val >= 0x8000:
        val = -((65535 - val) + 1)
    return val

def imu_loop():
    global imu_data

    while True:
        ax = read_word(0x3B) / 16384.0
        ay = read_word(0x3D) / 16384.0
        az = read_word(0x3F) / 16384.0

        imu_data = {"ax": ax, "ay": ay, "az": az}

        time.sleep(0.05)

# ================= SPEAK =================
def speak(text):
    print("🔊", text)
    subprocess.Popen(
        ["espeak", text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ================= SEND =================
def send(data):
    try:
        payload = pickle.dumps(data)
        message = struct.pack("Q", len(payload)) + payload
        client.sendall(message)
    except:
        print("❌ Send failed")

# ================= VIDEO LOOP =================
def video_loop():
    global distance_cm, imu_data

    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # 🔥 ENCODE FRAME PROPERLY
        _, buffer = cv2.imencode(
            '.jpg', frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 60]
        )

        data = {
            "type": "video",
            "frame": buffer.tobytes(),   # 🔴 CRITICAL FIX
            "distance": distance_cm,
            "imu": imu_data
        }

        print("📤 Sending frame...")
        send(data)

        time.sleep(0.15)  # ~20 FPS

# ================= RECEIVE =================
def receive_loop():
    data = b""
    payload_size = struct.calcsize("Q")

    while True:
        try:
            while len(data) < payload_size:
                packet = client.recv(4096)
                if not packet:
                    return
                data += packet

            packed = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed)[0]

            while len(data) < msg_size:
                data += client.recv(4096)

            msg_data = data[:msg_size]
            data = data[msg_size:]

            msg = pickle.loads(msg_data)

            if msg["type"] == "speech":
                speak(msg["text"])

        except:
            print("❌ Connection lost")
            break

# ================= START =================
threading.Thread(target=ultrasonic_loop, daemon=True).start()
threading.Thread(target=imu_loop, daemon=True).start()
threading.Thread(target=video_loop, daemon=True).start()
threading.Thread(target=receive_loop, daemon=True).start()

# ================= KEEP ALIVE =================
while True:
    time.sleep(1)