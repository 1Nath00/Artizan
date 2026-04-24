from __future__ import annotations

import io
import numpy as np
from functools import lru_cache
from typing import Any
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "modelo_pinturas_gridsearch(1).h5")

@lru_cache(maxsize=1)
def _load_model():
    import tensorflow as tf
    
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Input shape del modelo:", model.input_shape)

    categories = ["Barroco", "cubismo"] 

    return model, categories

def classify_image(image_bytes: bytes, top_k: int = 5) -> list[dict[str, Any]]:
    from PIL import Image
    model, categories = _load_model()

    # El modelo fue entrenado con (160, 160)
    IMG_HEIGHT, IMG_WIDTH = 160, 160

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((IMG_WIDTH, IMG_HEIGHT))

    # ✅ AHORA: pasar píxeles crudos [0, 255], el modelo ya tiene Rescaling interno
    tensor = np.array(image, dtype=np.float32)
    tensor = np.expand_dims(tensor, axis=0)  # (1, 160, 160, 3)

    predictions = model.predict(tensor)[0]

    # Evitar IndexError si top_k > número de clases
    top_k = min(top_k, len(categories))
    top_indices = predictions.argsort()[-top_k:][::-1]

    return [
        {"label": categories[i], "confidence": round(float(predictions[i]), 4)}
        for i in top_indices
    ]