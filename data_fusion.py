import os
import csv
import json
import time
import threading
from datetime import datetime
from itertools import product

import pandas as pd
import joblib
import paho.mqtt.client as mqtt
import certifi
from config_private import BROKER, PORT, USERNAME, PASSWORD


# ==========================================
# 1. KONFIGURASI MQTT
# ==========================================

TOPIC_HP = "focusdesk/rezatest/sensor_hp"
TOPIC_LAPTOP = "focusdesk/rezatest/laptop"


# ==========================================
# 2. KONFIGURASI AI
# ==========================================

FILE_MODEL = "focusdesk_model.pkl"

FITUR = [
    "accelerometer_x",
    "accelerometer_y",
    "accelerometer_z",
    "magnitude",
    "light",
    "yaw",
    "pitch",
    "roll",
    "keyboard_activity",
    "mouse_activity",
    "face_status",
    "head_status"
]

FITUR_NUMERIK = [
    "accelerometer_x",
    "accelerometer_y",
    "accelerometer_z",
    "magnitude",
    "light",
    "yaw",
    "pitch",
    "roll",
    "keyboard_activity",
    "mouse_activity"
]


# ==========================================
# 3. KONFIGURASI DATA
# ==========================================

FILE_HASIL = "hasil_prediksi_focusdesk.csv"

TOLERANSI_WAKTU = 2.0
BATAS_DATA = 50

buffer_hp = []
buffer_laptop = []

JUMLAH_PREDIKSI = 0

lock = threading.Lock()


# ==========================================
# 4. MEMUAT MODEL AI
# ==========================================

if not os.path.exists(FILE_MODEL):
    raise FileNotFoundError(
        f"Model tidak ditemukan: {FILE_MODEL}"
    )

model = joblib.load(FILE_MODEL)

print("Model AI berhasil dimuat!")


# ==========================================
# 5. KONVERSI TIMESTAMP
# ==========================================

def konversi_waktu(timestamp):

    if isinstance(timestamp, (int, float)):
        return float(timestamp)

    waktu = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    return waktu.timestamp()


# ==========================================
# 6. PERSIAPAN FILE HASIL PREDIKSI
# ==========================================

KOLOM_HASIL = ["timestamp"] + FITUR + ["prediksi"]


def siapkan_csv():

    if not os.path.exists(FILE_HASIL):

        with open(FILE_HASIL, "w", newline="") as file:

            writer = csv.DictWriter(
                file,
                fieldnames=KOLOM_HASIL
            )

            writer.writeheader()


def simpan_hasil(data):

    with open(FILE_HASIL, "a", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=KOLOM_HASIL
        )

        writer.writerow(data)


# ==========================================
# 7. PREDIKSI AI
# ==========================================

def prediksi_aktivitas(fitur):

    # Membentuk data sesuai format training
    input_ai = pd.DataFrame(
        [fitur],
        columns=FITUR
    )

    # Memastikan fitur numerik berbentuk angka
    for kolom in FITUR_NUMERIK:

        input_ai[kolom] = pd.to_numeric(
            input_ai[kolom]
        )

    # Melakukan prediksi
    hasil = model.predict(input_ai)[0]

    return hasil


# ==========================================
# 8. PROSES DATA FUSION
# ==========================================

def gabungkan_data():

    global JUMLAH_PREDIKSI

    while buffer_hp and buffer_laptop:

        pasangan_terbaik = min(
            product(
                enumerate(buffer_hp),
                enumerate(buffer_laptop)
            ),
            key=lambda pasangan: abs(
                pasangan[0][1]["timestamp"]
                - pasangan[1][1]["timestamp"]
            )
        )

        indeks_hp, hp = pasangan_terbaik[0]
        indeks_laptop, laptop = pasangan_terbaik[1]

        selisih = abs(
            hp["timestamp"] - laptop["timestamp"]
        )

        if selisih > TOLERANSI_WAKTU:
            break

        data_hp = hp["data"]
        data_laptop = laptop["data"]

        # Menggabungkan data sensor HP dan laptop
        fitur = {

            "accelerometer_x":
                data_hp["accelerometer"]["x"],

            "accelerometer_y":
                data_hp["accelerometer"]["y"],

            "accelerometer_z":
                data_hp["accelerometer"]["z"],

            "magnitude":
                data_hp["accelerometer"]["magnitude"],

            "light":
                data_hp["light"],

            "face_status":
                data_laptop["face_status"],

            "head_status":
                data_laptop["head_status"],

            "yaw":
                data_laptop["yaw"],

            "pitch":
                data_laptop["pitch"],

            "roll":
                data_laptop["roll"],

            "keyboard_activity":
                data_laptop["keyboard_activity"],

            "mouse_activity":
                data_laptop["mouse_activity"]
        }

        # Melakukan prediksi AI
        hasil_prediksi = prediksi_aktivitas(fitur)

        waktu_sekarang = datetime.fromtimestamp(
            (hp["timestamp"] + laptop["timestamp"]) / 2
        ).isoformat()

        # Menyimpan hasil prediksi
        hasil = {
            "timestamp": waktu_sekarang,
            **fitur,
            "prediksi": hasil_prediksi
        }

        simpan_hasil(hasil)

        JUMLAH_PREDIKSI += 1

        # Menampilkan hasil ke terminal
        print("\n====================================")
        print("          FOCUSDESK AI")
        print("====================================")
        print(f"Prediksi AI : {hasil_prediksi.upper()}")
        print(f"Jumlah data : {JUMLAH_PREDIKSI}")
        print(f"Selisih data: {selisih:.2f} detik")
        print("====================================")

        # Menghapus data yang sudah digunakan
        buffer_hp.pop(indeks_hp)
        buffer_laptop.pop(indeks_laptop)


# ==========================================
# 9. MENERIMA PESAN MQTT
# ==========================================

def on_message(client, userdata, msg):

    try:

        data = json.loads(msg.payload.decode())

        with lock:

            rekaman = {
                "timestamp": konversi_waktu(data["timestamp"]),
                "data": data
            }

            if msg.topic == TOPIC_HP:

                buffer_hp.append(rekaman)

                if len(buffer_hp) > BATAS_DATA:
                    buffer_hp.pop(0)

            elif msg.topic == TOPIC_LAPTOP:

                buffer_laptop.append(rekaman)

                if len(buffer_laptop) > BATAS_DATA:
                    buffer_laptop.pop(0)

            gabungkan_data()

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError
    ) as error:

        print("Kesalahan pengolahan data:", error)


# ==========================================
# 10. KONEKSI MQTT
# ==========================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    if reason_code == 0:

        print("\nBerhasil terhubung ke EMQX Cloud!")

        client.subscribe(TOPIC_HP, qos=1)
        client.subscribe(TOPIC_LAPTOP, qos=1)

        print("Menunggu data dari HP dan laptop...")
        print("Prediksi AI aktif.")

    else:

        print("Koneksi gagal:", reason_code)


# ==========================================
# 11. MENJALANKAN PROGRAM
# ==========================================

siapkan_csv()

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(USERNAME, PASSWORD)

client.tls_set(
    ca_certs=certifi.where()
)

client.on_connect = on_connect
client.on_message = on_message

print("\n====================================")
print("       FOCUSDESK AI DIMULAI")
print("====================================")
print("Menghubungkan ke EMQX Cloud...")

try:

    client.connect(BROKER, PORT, 60)

    client.loop_start()

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    print("\nProgram dihentikan.")

finally:

    client.loop_stop()

    if client.is_connected():
        client.disconnect()

    print("\nTotal prediksi:", JUMLAH_PREDIKSI)
    print("Hasil tersimpan:", FILE_HASIL)
