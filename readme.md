# FocusDesk AI

**Sistem Pemantauan Pola Aktivitas Fisik Saat Belajar Berbasis IoT dan Artificial Intelligence**

## 1. Deskripsi Proyek

FocusDesk AI merupakan sistem berbasis Internet of Things (IoT) dan Artificial Intelligence (AI) yang dirancang untuk memantau pola aktivitas fisik seseorang selama sesi belajar.

Sistem memanfaatkan sensor pada smartphone dan laptop untuk mengumpulkan data aktivitas. Data tersebut dikirim melalui protokol MQTT, kemudian digabungkan dan dianalisis menggunakan model Machine Learning untuk mengklasifikasikan aktivitas pengguna.

## 2. Tujuan

- Memantau pola aktivitas fisik selama belajar.
- Mengintegrasikan beberapa perangkat dan sensor melalui IoT.
- Menerapkan Machine Learning untuk mengklasifikasikan aktivitas.
- Menghasilkan prediksi aktivitas berdasarkan data sensor.

## 3. Arsitektur Sistem

Sistem terdiri dari tiga bagian utama:

### A. Phone Edge (Smartphone)
Menggunakan Android dengan Termux dan Termux:API.

Sensor yang digunakan:
- Accelerometer: mendeteksi perubahan gerakan smartphone.
- Light Sensor: mengukur intensitas cahaya di sekitar perangkat.

Data dikirim ke MQTT Broker.

### B. Laptop Edge
Menggunakan webcam dan perangkat input laptop.

Komponen yang digunakan:
- Webcam: mendeteksi keberadaan wajah.
- MediaPipe: membantu mendeteksi wajah dan memperkirakan posisi kepala.
- OpenCV: memproses citra dan memperkirakan orientasi kepala.
- Keyboard dan Mouse: mendeteksi aktivitas interaksi pengguna.

Data dikirim ke MQTT Broker.

### C. Cloud dan Data Fusion
Menggunakan EMQX Cloud sebagai MQTT Broker.

Data dari smartphone dan laptop diterima oleh program `data_fusion.py`, kemudian digabungkan berdasarkan timestamp untuk diproses oleh model Machine Learning.

## 4. Penerapan Artificial Intelligence

FocusDesk AI menggunakan algoritma **Random Forest Classifier** untuk mengklasifikasikan pola aktivitas pengguna.

Kategori klasifikasi:
1. `belajar`
2. `terdistraksi`
3. `meninggalkan_meja`

Model dilatih menggunakan dataset aktivitas yang dikumpulkan selama pengujian.

Hasil prediksi disimpan dalam file `hasil_prediksi_focusdesk.csv`.

## 5. Teknologi yang Digunakan

| Komponen | Teknologi |
|---|---|
| Bahasa pemrograman | Python |
| Smartphone Edge | Termux, Termux:API |
| Sensor smartphone | Accelerometer, Light Sensor |
| Computer Vision | OpenCV, MediaPipe |
| Input laptop | pynput |
| Komunikasi IoT | MQTT |
| MQTT Broker | EMQX Cloud |
| Machine Learning | Scikit-learn |
| Model AI | Random Forest |
| Pengolahan data | Pandas, NumPy |
| Model serialization | Joblib |

## 6. Struktur Folder

```text
FocusDesk/
│
├── hp_sensor_MQTT.py
├── laptop_edge.py
├── data_fusion.py
├── train_model.py
│
├── focusdesk_model.pkl
├── face_landmarker.task
│
├── config_private.py
├── config_private.example.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

**Catatan:**
- `config_private.py` berisi kredensial MQTT dan tidak boleh diunggah ke GitHub.
- `config_private.example.py` merupakan template konfigurasi yang dapat disalin oleh anggota kelompok.
- `focusdesk_model.pkl` merupakan model Machine Learning yang telah dilatih.
- `face_landmarker.task` merupakan file model untuk deteksi wajah.
- Dataset dan hasil prediksi tidak disertakan dalam repository karena bersifat lokal.

## 7. Instalasi dan Konfigurasi

### A. Clone Repository

```bash
git clone URL_REPOSITORY
cd FocusDesk
```

### B. Membuat Virtual Environment

```bash
python -m venv .venv
```

Aktifkan virtual environment pada Windows:

```bash
.venv\Scripts\activate
```

### C. Instalasi Dependencies

```bash
pip install -r requirements.txt
```

### D. Konfigurasi MQTT

Salin file template:

```bash
copy config_private.example.py config_private.py
```

Buka `config_private.py`, kemudian isi konfigurasi sesuai kredensial EMQX Cloud masing-masing.

```python
BROKER = "YOUR_EMQX_HOSTNAME"
PORT = 8883
USERNAME = "YOUR_MQTT_USERNAME"
PASSWORD = "YOUR_MQTT_PASSWORD"
```

**Penting:** Jangan mengunggah `config_private.py` ke repository GitHub.

### E. Persiapan Smartphone

1. Instal Termux dan Termux:API.
2. Pastikan izin sensor telah diberikan.
3. Pastikan smartphone terhubung ke internet.
4. Jalankan program `hp_sensor_MQTT.py` melalui Termux.

## 8. Menjalankan Sistem

Jalankan program dalam urutan berikut:

**Terminal 1 — Data Fusion**

```bash
python data_fusion.py
```

Program akan menerima data dari smartphone dan laptop, menggabungkan data, serta menghasilkan prediksi aktivitas.

**Terminal 2 — Laptop Edge**

```bash
python laptop_edge.py
```

Program akan mengaktifkan webcam, mendeteksi wajah, memproses orientasi kepala, dan memantau aktivitas keyboard serta mouse.

**Smartphone — Phone Edge**

```bash
python hp_sensor_MQTT.py
```

Program akan membaca sensor smartphone dan mengirimkan datanya ke MQTT Broker.

Pastikan seluruh perangkat menggunakan konfigurasi broker MQTT yang sesuai.

## 9. Output Sistem

Sistem menghasilkan klasifikasi aktivitas berupa:

- BELAJAR
- TERDISTRAKSI
- MENINGGALKAN_MEJA

Hasil prediksi juga disimpan dalam:

```text
hasil_prediksi_focusdesk.csv
```

File tersebut berisi hasil pengolahan dan prediksi aktivitas selama sistem berjalan.

## 10. Batasan Sistem

- Klasifikasi didasarkan pada pola aktivitas fisik dan data sensor, bukan pengukuran langsung terhadap kondisi mental atau tingkat konsentrasi seseorang.
- Akurasi model masih dapat dipengaruhi oleh kondisi lingkungan, posisi perangkat, dan variasi aktivitas pengguna.
- Dataset pengujian masih terbatas sehingga kemampuan generalisasi model perlu diuji lebih lanjut.

## 11. Pengembangan Selanjutnya

- Menambah variasi dataset dari lebih banyak pengguna.
- Meningkatkan kemampuan generalisasi model.
- Mengembangkan dashboard untuk visualisasi aktivitas.
- Mengembangkan rekomendasi istirahat berdasarkan pola aktivitas.

---

**FocusDesk AI — IoT and Artificial Intelligence Project**