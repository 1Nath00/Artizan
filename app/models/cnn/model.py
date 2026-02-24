"""
CNN image classifier using a pre-trained ResNet-50 backbone (ImageNet weights).

The model can be extended to fine-tune on custom classes by replacing the
final fully-connected layer and re-training.

Requires: torch, torchvision, Pillow
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Any


def _get_transform():
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def _build_model():
    import torch.nn as nn
    from torchvision import models

    class ImageClassifier(nn.Module):
        """ResNet-50 based image classifier."""

        def __init__(self, num_classes: int = 1000, pretrained: bool = True) -> None:
            super().__init__()
            weights = models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
            self.backbone = models.resnet50(weights=weights)
            if num_classes != 1000:
                in_features = self.backbone.fc.in_features
                self.backbone.fc = nn.Linear(in_features, num_classes)

        def forward(self, x):
            return self.backbone(x)

    return ImageClassifier


@lru_cache(maxsize=1)
def _load_model():
    from torchvision import models

    ImageClassifier = _build_model()
    model = ImageClassifier(pretrained=True)
    model.eval()

    categories: list[str] = models.ResNet50_Weights.IMAGENET1K_V1.meta["categories"]
    return model, categories


def classify_image(image_bytes: bytes, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Classify an image and return the top-k predictions.

    Args:
        image_bytes: Raw bytes of the image file.
        top_k: Number of top predictions to return.

    Returns:
        List of dicts with 'label' and 'confidence' keys.
    """
    import torch
    from PIL import Image

    model, categories = _load_model()
    transform = _get_transform()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    top_probs, top_indices = torch.topk(probabilities, k=min(top_k, len(categories)))

    return [
        {"label": categories[idx.item()], "confidence": round(prob.item(), 4)}
        for prob, idx in zip(top_probs, top_indices)
    ]
