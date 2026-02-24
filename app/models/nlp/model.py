"""
NLP text generator using a pre-trained GPT-2 model via Hugging Face Transformers.

The model is loaded lazily on first use and cached for subsequent requests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

DEFAULT_MODEL = "gpt2"
MAX_NEW_TOKENS = 200


@lru_cache(maxsize=1)
def _load_pipeline():
    """Load and cache the text-generation pipeline."""
    from transformers import pipeline

    return pipeline(
        "text-generation",
        model=DEFAULT_MODEL,
        tokenizer=DEFAULT_MODEL,
        device=-1,  # CPU; set to 0 for GPU
    )


def generate_text(
    prompt: str,
    max_new_tokens: int = 100,
    num_return_sequences: int = 1,
    temperature: float = 0.9,
    top_p: float = 0.95,
    do_sample: bool = True,
) -> list[dict[str, Any]]:
    """
    Generate text continuations for a given prompt using GPT-2.

    Args:
        prompt: The text prompt to continue.
        max_new_tokens: Maximum number of new tokens to generate.
        num_return_sequences: Number of independent text samples to generate.
        temperature: Sampling temperature (higher = more random).
        top_p: Nucleus sampling probability threshold.
        do_sample: Whether to use sampling (True) or greedy decoding (False).

    Returns:
        List of dicts with 'generated_text' key.
    """
    if max_new_tokens > MAX_NEW_TOKENS:
        max_new_tokens = MAX_NEW_TOKENS

    generator = _load_pipeline()
    outputs = generator(
        prompt,
        max_new_tokens=max_new_tokens,
        num_return_sequences=num_return_sequences,
        temperature=temperature,
        top_p=top_p,
        do_sample=do_sample,
        pad_token_id=generator.tokenizer.eos_token_id,
    )
    return [{"generated_text": item["generated_text"]} for item in outputs]
