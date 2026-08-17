import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLM Enrich Endpoint")

LLM_STUB = os.environ.get("LLM_STUB", "0") == "1"

class EnrichRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=0, max_length=3000)

class EnrichResponse(BaseModel):
    category: str
    summary: str
    quality_flags: list[str]

VALID_CATEGORIES = ["fiction", "nonfiction", "childrens", "poetry", "reference", "other"]

@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if LLM_STUB:
        return EnrichResponse(
            category="other",
            summary="Stub summary — no model was called.",
            quality_flags=["stub_mode"]
        )

    raise HTTPException(status_code=501, detail="Real model call not implemented yet")