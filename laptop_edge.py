import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import json

import paho.mqtt.client as mqtt
import certifi

from datetime import datetime, timezone
from pynput import keyboard, mouse
from config_private import BROKER, PORT, USERNAME, PASSWORD


# ==========================================
# 1. KONFIGURASI MQTT
# ==========================================

TOPIC = "focusdesk/rezatest/laptop"

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(ca_certs=certifi.where())


# ==========================================
# 2. VARIABEL AKTIVITAS KEYBOARD DAN MOUSE
# ==========================================

keyboard_count = 0
mouse_count = 0

last_mouse_position = None
lock = threading.Lock()


def on_key_press(key):
    global keyboard_count

    with lock:
        keyboard_count += 1


def on_mouse_move(x, y):
    global mouse_count, last_mouse_position

    with lock:
        if last_mouse_position is None:
            last_mouse_position = (x, y)
            return

        old_x, old_y = last_mouse_position

        if abs(x - old_x) >= 10 or abs(y - old_y) >= 10:
            mouse_count += 1
            last_mouse_position = (x, y)


keyboard_listener = keyboard.Listener(
    on_press=on_key_press
)

mouse_listener = mouse.Listener(
    on_move=on_mouse_move
)


# ==========================================
# 3. KONFIGURASI MEDIAPIPE
# ==========================================

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="face_landmarker.task"
    ),
    running_mode=VisionRunningMode.VIDEO,
    num_faces=1
)


# ==========================================
# 4. TITIK REFERENSI WAJAH
# ==========================================

model_points = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0)
], dtype=np.float64)

landmark_indices = [1, 152, 33, 263, 61, 291]


# ==========================================
# 5. MENGHUBUNGKAN MQTT
# ==========================================

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print("Berhasil terhubung ke MQTT Cloud.")

except Exception as error:
    print("Koneksi MQTT gagal:", error)
    exit()


# ==========================================
# 6. MEMBUKA KAMERA
# ==========================================

kamera = cv2.VideoCapture(0)

if not kamera.isOpened():
    print("Kamera tidak dapat diakses.")

    client.disconnect()
    client.loop_stop()

    exit()


keyboard_listener.start()
mouse_listener.start()

print("FocusDesk AI - Laptop Edge")
print("Tekan Q untuk keluar.")


# ==========================================
# 7. VARIABEL DETEKSI
# ==========================================

start_time = time.time()
last_report = time.time()

face_status = "Tidak Terdeteksi"
head_status = "Tidak Terdeteksi"

yaw = 0.0
pitch = 0.0
roll = 0.0


# ==========================================
# 8. PROSES DETEKSI WAJAH DAN AKTIVITAS
# ==========================================

try:

    with FaceLandmarker.create_from_options(options) as landmarker:

        while True:

            berhasil, frame = kamera.read()

            if not berhasil:
                print("Gagal membaca kamera.")
                break

            frame = cv2.flip(frame, 1)

            height, width, _ = frame.shape

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            timestamp = int(
                (time.time() - start_time) * 1000
            )

            results = landmarker.detect_for_video(
                mp_image,
                timestamp
            )

            # Reset status setiap frame
            face_status = "Tidak Terdeteksi"
            head_status = "Tidak Terdeteksi"

            yaw = 0.0
            pitch = 0.0
            roll = 0.0

            # ==================================
            # 9. DETEKSI WAJAH
            # ==================================

            if results.face_landmarks:

                face_status = "Terdeteksi"

                face_landmarks = results.face_landmarks[0]

                image_points = []

                for index in landmark_indices:

                    landmark = face_landmarks[index]

                    x = landmark.x * width
                    y = landmark.y * height

                    image_points.append((x, y))

                image_points = np.array(
                    image_points,
                    dtype=np.float64
                )

                focal_length = width
                center = (width / 2, height / 2)

                camera_matrix = np.array([
                    [focal_length, 0, center[0]],
                    [0, focal_length, center[1]],
                    [0, 0, 1]
                ], dtype=np.float64)

                distortion = np.zeros((4, 1))

                success, rotation_vector, translation_vector = (
                    cv2.solvePnP(
                        model_points,
                        image_points,
                        camera_matrix,
                        distortion,
                        flags=cv2.SOLVEPNP_ITERATIVE
                    )
                )

                if success:

                    rotation_matrix, _ = cv2.Rodrigues(
                        rotation_vector
                    )

                    angles = cv2.RQDecomp3x3(
                        rotation_matrix
                    )[0]

                    pitch = float(angles[0])
                    yaw = float(angles[1])
                    roll = float(angles[2])

                    if pitch > 90:
                        pitch -= 180
                    elif pitch < -90:
                        pitch += 180

                    if yaw > 90:
                        yaw -= 180
                    elif yaw < -90:
                        yaw += 180

                    if abs(yaw) > 20 or abs(pitch) > 20:
                        head_status = "Menoleh / Menunduk"
                    else:
                        head_status = "Menghadap Layar"

            # ==================================
            # 10. MENAMPILKAN HASIL DI KAMERA
            # ==================================

            cv2.putText(
                frame,
                f"Wajah: {face_status}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Kepala: {head_status}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Yaw: {yaw:.2f} | Pitch: {pitch:.2f}",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.imshow(
                "FocusDesk AI - Laptop Edge",
                frame
            )

            # ==================================
            # 11. MENGIRIM DATA MELALUI MQTT
            # ==================================

            if time.time() - last_report >= 3:

                with lock:

                    current_keyboard = keyboard_count
                    current_mouse = mouse_count

                    keyboard_count = 0
                    mouse_count = 0

                data = {
                    "device": "laptop",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),

                    "face_status": face_status,
                    "head_status": head_status,

                    "yaw": round(yaw, 2),
                    "pitch": round(pitch, 2),
                    "roll": round(roll, 2),

                    "keyboard_activity": current_keyboard,
                    "mouse_activity": current_mouse
                }

                payload = json.dumps(data)

                if client.is_connected():

                    info = client.publish(
                        TOPIC,
                        payload,
                        qos=1
                    )

                    print("\n===== DATA LAPTOP =====")
                    print(json.dumps(data, indent=4))

                    if info.rc == mqtt.MQTT_ERR_SUCCESS:
                        print("Data berhasil dikirim ke MQTT.")
                    else:
                        print("Gagal mengirim data MQTT.")

                else:
                    print("MQTT terputus. Data belum dikirim.")

                last_report = time.time()

            # ==================================
            # 12. KELUAR DARI PROGRAM
            # ==================================

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


finally:

    kamera.release()
    cv2.destroyAllWindows()

    keyboard_listener.stop()
    mouse_listener.stop()

    client.disconnect()
    client.loop_stop()

    print("\nProgram FocusDesk AI selesai.")