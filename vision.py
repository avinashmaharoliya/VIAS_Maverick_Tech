import math
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
names = model.names

def detect_objects(frame):
    results = model(frame, conf=0.4, verbose=False)[0]

    for box in results.boxes:
        cls = int(box.cls[0])
        label = names[cls]

        if label in ["person", "chair", "car", "bike"]:
            return label

    return None


def detect_fall(imu, threshold=2.5):
    ax, ay, az = imu.get("ax",0), imu.get("ay",0), imu.get("az",0)
    acc = math.sqrt(ax*ax + ay*ay + az*az)
    return acc > threshold