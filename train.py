# train.py
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
import matplotlib.pyplot as plt
import numpy as np
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Set random seed for reproducibility
tf.random.set_seed(123)

# Define paths to dataset
data_dir_train = "/home/balaji/Downloads/chest-xray-pneumonia-detection/train"
data_dir_validation = "/home/balaji/Downloads/chest-xray-pneumonia-detection/test"

# Image parameters
img_height, img_width = 180, 180
batch_size = 32

# Load datasets
try:
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir_train,
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size,
        color_mode="grayscale"  # Chest X-rays are grayscale
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir_validation,
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size,
        color_mode="grayscale"
    )
except Exception as e:
    logger.error(f"Error loading datasets: {str(e)}")
    raise

# Get class names
class_names = train_ds.class_names
logger.info(f"Class names: {class_names}")  # Should be ['NORMAL', 'PNEUMONIA']

# Calculate class weights to handle imbalance
num_normal = len(os.listdir(os.path.join(data_dir_train, "NORMAL")))
num_pneumonia = len(os.listdir(os.path.join(data_dir_train, "PNEUMONIA")))
class_weights = {
    0: num_pneumonia / (num_normal + num_pneumonia),  # NORMAL
    1: num_normal / (num_normal + num_pneumonia)      # PNEUMONIA
}
logger.info(f"Class weights: {class_weights}")

# Data augmentation to improve generalization
data_augmentation = models.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.2),
])

# Build CNN model
def build_model():
    model = models.Sequential([
        # Data augmentation
        data_augmentation,
        # Rescale pixel values
        layers.Rescaling(1./255, input_shape=(img_height, img_width, 1)),
        # Convolutional layers
        layers.Conv2D(32, 3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D(),
        layers.Conv2D(128, 3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D(),
        layers.Conv2D(256, 3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D(),
        # Flatten and dense layers
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(256, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')  # Binary classification
    ])
    return model

# Compile the model
model = build_model()
model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)

# Callbacks
callbacks = [
    EarlyStopping(patience=10, restore_best_weights=True),
    ReduceLROnPlateau(factor=0.2, patience=5),
    ModelCheckpoint('best_model.h5', save_best_only=True, monitor='val_accuracy')
]

# Train the model
epochs = 50  # Increased for better learning
try:
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
        class_weight=class_weights
    )
except Exception as e:
    logger.error(f"Error during training: {str(e)}")
    raise

# Save the final model
model.save('xray_model.h5')
logger.info("Model saved as xray_model.h5")

# Plot training history
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Model Accuracy')
plt.legend()
plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.legend()
plt.savefig('training_history.png')
plt.show()

# Evaluate on validation set
val_loss, val_accuracy = model.evaluate(val_ds)
logger.info(f"Validation accuracy: {val_accuracy:.4f}")