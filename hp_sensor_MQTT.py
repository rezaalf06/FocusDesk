import subprocess
import json
import time
import math
import paho.mqtt.client as mqtt
import certifi
from config_private import BROKER, PORT, USERNAME, PASSWORD

# ==========================================
# KONFIGURASI MQTT
# ==========================================

TOPIC = "focusdesk/rezatest/sensor_hp"
INTERVAL = 3

SENSOR_ACC = "sc7a20h_acc"
SENSOR_LIGHT = "mn78911_als"

# ==========================================
# MEMBACA SENSOR DENGAN RETRY
# ==========================================

def baca_sensor(nama_sensor):
    for percobaan in range(1, 4):
        try:
            hasil = subprocess.run(
                ["termux-sensor", "-s", nama_sensor, "-n", "1"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if hasil.returncode != 0:
                print(
                    f"[PERINGATAN] Sensor {nama_sensor}: "
                    f"{hasil.stderr.strip()}"
                )
                time.sleep(1)
                continue

            if not hasil.stdout.strip():
                print(
                    f"[PERINGATAN] Output sensor {nama_sensor} kosong."
                )
                time.sleep(1)
                continue

            data = json.loads(hasil.stdout)

            if nama_sensor not in data:
                print(f"[PERINGATAN] Data {nama_sensor} tidak ditemukan.")
                time.sleep(1)
                continue

            values = data[nama_sensor]["values"]

            if not isinstance(values, list) or len(values) == 0:
                raise ValueError("Nilai sensor kosong.")

            return values

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(
                f"[PERINGATAN] Pembacaan {nama_sensor} "
                f"percobaan {percobaan}/3: {e}"
            )

        except subprocess.TimeoutExpired:
            print(
                f"[PERINGATAN] Sensor {nama_sensor} timeout "
                f"percobaan {percobaan}/3."
            )

        time.sleep(1)

    return None


# ==========================================
# KONEKSI MQTT
# ==========================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(ca_certs=certifi.where())

print("Menghubungkan ke EMQX Cloud...")

client.connect(BROKER, PORT, 60)
client.loop_start()

time.sleep(2)

print("Berhasil terhubung ke EMQX Cloud!")
print("Pengiriman sensor dimulai.")
print("Tekan Ctrl+C untuk berhenti.")

# ==========================================
# PENGIRIMAN DATA
# ==========================================

jumlah_terkirim = 0
jumlah_gagal = 0

try:
    while True:

        # Membaca accelerometer
        acc = baca_sensor(SENSOR_ACC)

        if acc is None or len(acc) < 3:
            print("[GAGAL] Accelerometer tidak terbaca. Mencoba lagi.")
            jumlah_gagal += 1
            time.sleep(2)
            continue

        # Membaca sensor cahaya
        light = baca_sensor(SENSOR_LIGHT)

        if light is None:
            print("[GAGAL] Sensor cahaya tidak terbaca. Mencoba lagi.")
            jumlah_gagal += 1
            time.sleep(2)
            continue

        try:
            x = float(acc[0])
            y = float(acc[1])
            z = float(acc[2])
            cahaya = float(light[0])

        except (ValueError, TypeError, IndexError):
            print("[GAGAL] Format nilai sensor tidak valid.")
            jumlah_gagal += 1
            time.sleep(2)
            continue

        # Menghitung magnitudo accelerometer
        magnitudo = math.sqrt(x**2 + y**2 + z**2)

        # Membentuk data JSON
        data = {
            "device": "HP",
            "accelerometer": {
                "x": x,
                "y": y,
                "z": z,
                "magnitude": magnitudo
            },
            "light": cahaya,
            "timestamp": time.time()
        }

        pesan = json.dumps(data)

        try:
            hasil = client.publish(
                TOPIC,
                pesan,
                qos=1
            )

            hasil.wait_for_publish(timeout=10)

            if hasil.is_published():
                jumlah_terkirim += 1
                print(
                    f"[TERKIRIM] Data ke-{jumlah_terkirim}: {pesan}"
                )
            else:
                jumlah_gagal += 1
                print("[GAGAL] Data belum berhasil dipublikasikan.")

        except Exception as e:
            jumlah_gagal += 1
            print("[ERROR MQTT]", e)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nPengiriman dihentikan oleh pengguna.")

finally:
    print("\n===== RINGKASAN =====")
    print("Total terkirim:", jumlah_terkirim)
    print("Total gagal:", jumlah_gagal)

    client.loop_stop()
    client.disconnect()

    print("Koneksi MQTT ditutup.")
