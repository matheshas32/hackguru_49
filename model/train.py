import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import MobileNetV2
from pathlib import Path
import numpy as np
 
# ============================================================
# EVENTTRUST AI - COMBINED POSTER + QR MODEL
# ============================================================
 
BASE_DIR = Path(__file__).resolve().parent.parent
 
POSTER_DIR = BASE_DIR / "dataset"
QR_DIR = BASE_DIR / "qr_dataset" / "QR codes"
 
MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "eventtrust_model.keras"
 
IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 15
SEED = 42
 
print("==========================================")
print(" EVENTTRUST AI - MODEL TRAINING")
print("==========================================")
 
print("Poster dataset:", POSTER_DIR)
print("QR dataset:", QR_DIR)
 
# ============================================================
# CHECK DATASET
# ============================================================
 
poster_real = POSTER_DIR / "real"
poster_fake = POSTER_DIR / "fake"
 
qr_benign = QR_DIR / "benign"
qr_malicious = QR_DIR / "malicious"
 
folders = [
    poster_real,
    poster_fake,
    qr_benign,
    qr_malicious
]
 
for folder in folders:
    if not folder.exists():
        print("ERROR: Folder not found:")
        print(folder)
        exit()
 
# ============================================================
# GET IMAGE PATHS
# ============================================================
 
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
 
 
def get_images(folder):
    return [
        p for p in folder.rglob("*")
        if p.suffix.lower() in EXTENSIONS
    ]
 
 
real_images = get_images(poster_real)
fake_images = get_images(poster_fake)
 
benign_images = get_images(qr_benign)
malicious_images = get_images(qr_malicious)
 
print()
print("POSTER DATA")
print("Real:", len(real_images))
print("Fake:", len(fake_images))
 
print()
print("QR DATA")
print("Benign:", len(benign_images))
print("Malicious:", len(malicious_images))
 
# ============================================================
# CREATE COMBINED DATA
#
# poster_label:
#   1 = real
#   0 = fake
#
# qr_label:
#   0 = benign
#   1 = malicious
#
# Missing label = -1
# ============================================================
 
paths = []
poster_labels = []
qr_labels = []
 
# ------------------------------------------------------------
# POSTER DATA
# ------------------------------------------------------------
 
for p in real_images:
    paths.append(str(p))
    poster_labels.append(1.0)
    qr_labels.append(-1.0)
 
for p in fake_images:
    paths.append(str(p))
    poster_labels.append(0.0)
    qr_labels.append(-1.0)
 
# ------------------------------------------------------------
# QR DATA
# ------------------------------------------------------------
 
for p in benign_images:
    paths.append(str(p))
    poster_labels.append(-1.0)
    qr_labels.append(0.0)
 
for p in malicious_images:
    paths.append(str(p))
    poster_labels.append(-1.0)
    qr_labels.append(1.0)
 
# ============================================================
# SHUFFLE
# ============================================================
 
paths = np.array(paths)
poster_labels = np.array(poster_labels, dtype=np.float32)
qr_labels = np.array(qr_labels, dtype=np.float32)
 
rng = np.random.default_rng(SEED)
 
indices = np.arange(len(paths))
rng.shuffle(indices)
 
paths = paths[indices]
poster_labels = poster_labels[indices]
qr_labels = qr_labels[indices]
 
print()
print("TOTAL TRAINING IMAGES:", len(paths))
 
# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================
 
split = int(len(paths) * 0.8)
 
train_paths = paths[:split]
val_paths = paths[split:]
 
train_poster = poster_labels[:split]
val_poster = poster_labels[split:]
 
train_qr = qr_labels[:split]
val_qr = qr_labels[split:]
 
# ============================================================
# IMAGE LOADER
# ============================================================
 
def load_image(path):
 
    image = tf.io.read_file(path)
 
    image = tf.image.decode_image(
        image,
        channels=3,
        expand_animations=False
    )
 
    image = tf.image.resize(
        image,
        IMG_SIZE
    )
 
    image = tf.cast(image, tf.float32) / 255.0
 
    return image
 
 
def make_dataset(paths, poster_labels, qr_labels, training=False):
 
    dataset = tf.data.Dataset.from_tensor_slices(
        (
            paths,
            {
                "poster_output": poster_labels,
                "qr_output": qr_labels
            }
        )
    )
 
    def process(path, labels):
 
        image = load_image(path)
 
        return image, labels
 
    dataset = dataset.map(
        process,
        num_parallel_calls=tf.data.AUTOTUNE
    )
 
    if training:
        dataset = dataset.shuffle(
            1000,
            seed=SEED
        )
 
    dataset = dataset.batch(BATCH_SIZE)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
 
    return dataset
 
 
train_ds = make_dataset(
    train_paths,
    train_poster,
    train_qr,
    training=True
)
 
val_ds = make_dataset(
    val_paths,
    val_poster,
    val_qr,
    training=False
)
 
# ============================================================
# MASKED BINARY CROSS ENTROPY
#
# Ignores -1 labels.
# ============================================================
 
def masked_binary_crossentropy(y_true, y_pred):
 
    mask = tf.cast(
        tf.not_equal(y_true, -1.0),
        tf.float32
    )
 
    safe_true = tf.where(
        y_true == -1.0,
        tf.zeros_like(y_true),
        y_true
    )
 
    loss = tf.keras.backend.binary_crossentropy(
        safe_true,
        y_pred
    )
 
    loss = loss * mask
 
    return tf.reduce_sum(loss) / (
        tf.reduce_sum(mask) + 1e-7
    )
 
# ============================================================
# BASE MODEL
# ============================================================
 
base_model = MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)
 
base_model.trainable = False
 
inputs = layers.Input(
    shape=(224, 224, 3),
    name="image"
)
 
x = base_model(
    inputs,
    training=False
)
 
x = layers.GlobalAveragePooling2D()(x)
 
x = layers.Dropout(0.30)(x)
 
# ============================================================
# POSTER HEAD
# ============================================================
 
poster_branch = layers.Dense(
    128,
    activation="relu"
)(x)
 
poster_branch = layers.Dropout(0.30)(
    poster_branch
)
 
poster_output = layers.Dense(
    1,
    activation="sigmoid",
    name="poster_output"
)(poster_branch)
 
# ============================================================
# QR HEAD
# ============================================================
 
qr_branch = layers.Dense(
    128,
    activation="relu"
)(x)
 
qr_branch = layers.Dropout(0.30)(
    qr_branch
)
 
qr_output = layers.Dense(
    1,
    activation="sigmoid",
    name="qr_output"
)(qr_branch)
 
# ============================================================
# COMBINED MODEL
# ============================================================
 
model = Model(
    inputs=inputs,
    outputs=[
        poster_output,
        qr_output
    ]
)
 
# ============================================================
# COMPILE
# ============================================================
 
model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.001
    ),
 
    loss={
        "poster_output":
            masked_binary_crossentropy,
 
        "qr_output":
            masked_binary_crossentropy
    },
 
    metrics={
        "poster_output":
            [tf.keras.metrics.BinaryAccuracy(
                name="poster_accuracy"
            )],
 
        "qr_output":
            [tf.keras.metrics.BinaryAccuracy(
                name="qr_accuracy"
            )]
    }
)
 
print()
model.summary()
 
# ============================================================
# CALLBACKS
# ============================================================
 
callbacks = [
 
    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=4,
        restore_best_weights=True
    ),
 
    tf.keras.callbacks.ModelCheckpoint(
        MODEL_PATH,
        monitor="val_loss",
        save_best_only=True
    ),
 
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=2,
        min_lr=1e-6
    )
]
 
# ============================================================
# TRAIN
# ============================================================
 
print()
print("==========================================")
print(" STARTING TRAINING")
print("==========================================")
 
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)
 
# ============================================================
# SAVE
# ============================================================
 
model.save(MODEL_PATH)
 
print()
print("==========================================")
print(" TRAINING COMPLETED")
print("==========================================")
 
print()
print("MODEL SAVED:")
print(MODEL_PATH)
 
print()
print("You can now use predict.py")

 