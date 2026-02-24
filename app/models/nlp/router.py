from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.nlp.model import generate_text

router = APIRouter(prefix="/models/nlp", tags=["NLP - Text Generation"])


class TextGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500, description="Text prompt to continue")
    max_new_tokens: int = Field(100, ge=1, le=200, description="Max tokens to generate")
    num_return_sequences: int = Field(1, ge=1, le=5, description="Number of text samples")
    temperature: float = Field(0.9, ge=0.1, le=2.0, description="Sampling temperature")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    do_sample: bool = Field(True, description="Use sampling instead of greedy decoding")


class GeneratedText(BaseModel):
    generated_text: str


class TextGenerationResponse(BaseModel):
    prompt: str
    results: list[GeneratedText]


@router.post("/generate", response_model=TextGenerationResponse)
def generate(
    body: TextGenerationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate text based on a prompt using a pre-trained GPT-2 language model.
    """
    try:
        outputs = generate_text(
            prompt=body.prompt,
            max_new_tokens=body.max_new_tokens,
            num_return_sequences=body.num_return_sequences,
            temperature=body.temperature,
            top_p=body.top_p,
            do_sample=body.do_sample,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text generation failed: {exc}",
        ) from exc

    return TextGenerationResponse(
        prompt=body.prompt,
        results=[GeneratedText(**item) for item in outputs],
    )
