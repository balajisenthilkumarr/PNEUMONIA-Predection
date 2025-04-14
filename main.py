# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# Add CORS support
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})  # Allow React dev server

# Load the trained model at startup
try:
    model = tf.keras.models.load_model("xray_model.h5")
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise RuntimeError(f"Model loading failed: {str(e)}")

class_names = ["NORMAL", "PNEUMONIA"]

# Image preprocessing function
def preprocess_image(image: Image.Image) -> np.ndarray:
    try:
        # Resize to 180x180 to match training
        image = image.resize((180, 180))
        # Convert to grayscale (consistent with train.py)
        image = image.convert("L")
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.asarray(image, dtype=np.float32) / 255.0
        # Add batch and channel dimensions: (1, 180, 180, 1)
        img_array = img_array[np.newaxis, ..., np.newaxis]
        logger.info(f"Preprocessed image shape: {img_array.shape}")
        return img_array
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        raise Exception(f"Image preprocessing failed: {str(e)}")

# Prediction endpoint
@app.route("/predict/", methods=["POST"])
def predict():
    try:
        if "file" not in request.files:
            logger.warning("No file part in request")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.content_type not in ["image/jpeg", "image/png"]:
            logger.warning(f"Unsupported file type: {file.content_type}")
            return jsonify({"error": "Only JPEG or PNG images are supported"}), 400

        # Read and process image
        contents = file.read()
        image = Image.open(io.BytesIO(contents))
        img_array = preprocess_image(image)

        # Make prediction and log raw score
        prediction = model.predict(img_array, verbose=0)
        score = float(prediction[0][0])
        logger.info(f"Raw prediction score: {score}")  # Log raw score for debugging
        predicted_class = class_names[1 if score > 0.5 else 0]  # Threshold at 0.5
        confidence = score if score > 0.5 else 1 - score
        has_pneumonia = predicted_class == "PNEUMONIA"

        logger.info(f"Prediction: {predicted_class}, Confidence: {confidence:.2%}")
        return jsonify({
            "status": "success",
            "prediction": predicted_class,
            "has_pneumonia": has_pneumonia,
            "confidence": f"{confidence:.2%}",
            "raw_score": score
        })
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "Pneumonia Detection API is running", "status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)