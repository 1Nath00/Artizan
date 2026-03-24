"""
CNN image classifier using a pre-trained ResNet-50 backbone (ImageNet weights).

The model can be extended to fine-tune on custom classes by replacing the
final fully-connected layer and re-training.

Requires: torch, torchvision, Pillow
"""

from __future__ import annotations

import io
import numpy as np
from functools import lru_cache
from typing import Any
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "modelo_pinturas.h5")

@lru_cache(maxsize=1)
def _load_model():
    import tensorflow as tf
    
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Input shape del modelo:", model.input_shape)

    categories = ["Barroco", "cubismo"]  # <-- Cambia esto

    return model, categories

def classify_image(image_bytes: bytes, top_k: int = 5) -> list[dict[str, Any]]:
    from PIL import Image
    model, categories = _load_model()

    _, height, width, _ = model.input_shape

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((width, height))
    tensor = np.array(image) / 255.0
    tensor = np.expand_dims(tensor, axis=0)

    predictions = model.predict(tensor)[0]
    top_indices = predictions.argsort()[-top_k:][::-1]

    return [
        {"label": categories[i], "confidence": round(float(predictions[i]), 4)}
        for i in top_indices
    ]