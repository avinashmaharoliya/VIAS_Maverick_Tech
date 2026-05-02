from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.to("cuda")  # remove if no GPU

names = model.names


def detect_objects(frame):
    h, w = frame.shape[:2]

    results = model(frame, conf=0.4, verbose=False)[0]
    objs = []

    for box in results.boxes:
        label = names[int(box.cls[0])]

        if label not in ["person", "chair", "car", "bike" ]:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx = (x1 + x2) // 2

        if cx < w//3:
            pos = "LEFT"
        elif cx > 2*w//3:
            pos = "RIGHT"
        else:
            pos = "AHEAD"

        objs.append((label, pos, (x1,y1,x2,y2)))

    return objs


def detect_fall(imu):
    ax, ay, az = imu.get("ax",0), imu.get("ay",0), imu.get("az",0)
    mag = (ax*ax + ay*ay + az*az) ** 0.5
    return mag > 1.3