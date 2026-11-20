from __future__ import annotations

import io
import numpy as np
from typing import Any
from app.model_loader import get_keras_model


CATEGORIES = ["Barroco", "Cubismo"]

def classify_image(image_bytes: bytes, top_k: int = 5) -> list[dict[str, Any]]:
    from PIL import Image
    model = get_keras_model()
    categories = CATEGORIES

    IMG_HEIGHT, IMG_WIDTH = 224, 224

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((IMG_WIDTH, IMG_HEIGHT))

    # pasar píxeles crudos [0, 255], el modelo ya tiene Rescaling interno
    tensor = np.array(image, dtype=np.float32)
    tensor = np.expand_dims(tensor, axis=0)  # (1, 224, 224, 3)

    predictions = model.predict(tensor)[0]

    # Evitar IndexError si top_k > número de clases
    top_k = min(top_k, len(categories))
    top_indices = predictions.argsort()[-top_k:][::-1]

    return [
        {"label": categories[i], "confidence": round(float(predictions[i]), 4)}
        for i in top_indices
    ]