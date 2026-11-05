
import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix


# ==========================================
# 1. MEMBACA DATASET
# ==========================================

df = pd.read_csv("dataset_focusdesk.csv")

print("Dataset berhasil dibaca.")
print("Jumlah data:", len(df))

print("\nDistribusi kelas:")
print(df["label"].value_counts())


# ==========================================
# 2. MENENTUKAN FITUR
# ==========================================

numeric_features = [
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

categorical_features = [
    "face_status",
    "head_status"
]

target = "label"

# Pastikan semua kolom tersedia
required_columns = (
    numeric_features + categorical_features + [target, "timestamp"]
)

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Kolom berikut tidak ditemukan dalam dataset: {missing_columns}"
    )

# Pastikan fitur numerik benar-benar berbentuk angka
for col in numeric_features:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[numeric_features + categorical_features + [target]].isnull().any().any():
    raise ValueError("Dataset memiliki nilai kosong atau tidak valid.")


# ==========================================
# 3. MEMBAGI DATA TRAINING DAN TESTING
# ==========================================

# Pembagian berdasarkan urutan waktu setiap kelas
train_parts = []
test_parts = []

for label in df["label"].unique():

    class_data = df[df["label"] == label].copy()

    class_data["timestamp"] = pd.to_datetime(
        class_data["timestamp"], errors="coerce"
    )

    class_data = class_data.sort_values("timestamp")

    split_index = int(len(class_data) * 0.8)

    train_parts.append(class_data.iloc[:split_index])
    test_parts.append(class_data.iloc[split_index:])

train_df = pd.concat(train_parts)
test_df = pd.concat(test_parts)

X_train = train_df[numeric_features + categorical_features]
y_train = train_df[target]

X_test = test_df[numeric_features + categorical_features]
y_test = test_df[target]

print("\nJumlah data training:", len(X_train))
print("Jumlah data testing:", len(X_test))


# ==========================================
# 4. MENGOLAH FITUR KATEGORI
# ==========================================

preprocessor = ColumnTransformer(
    transformers=[
        ("numerik", "passthrough", numeric_features),
        (
            "kategori",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ]
)


# ==========================================
# 5. MEMBUAT MODEL AI
# ==========================================

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight="balanced"
            )
        )
    ]
)


# ==========================================
# 6. MELATIH MODEL
# ==========================================

print("\nSedang melatih model...")

model.fit(X_train, y_train)

print("Pelatihan model selesai!")


# ==========================================
# 7. EVALUASI MODEL
# ==========================================

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n================================")
print("HASIL EVALUASI MODEL")
print("================================")

print(f"Akurasi: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, predictions, zero_division=0))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, predictions))


# ==========================================
# 8. MENYIMPAN MODEL
# ==========================================

joblib.dump(model, "focusdesk_model.pkl")

print("\nModel berhasil disimpan!")
print("Nama file: focusdesk_model.pkl")
