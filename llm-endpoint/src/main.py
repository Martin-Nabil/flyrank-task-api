import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="LLM Enrich Endpoint")

LLM_STUB = os.environ.get("LLM_STUB", "0") == "1"
PROMPT_VERSION = "enrich-v1"

with open(f"prompts/{PROMPT_VERSION}.md", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL"),
    api_key=os.environ.get("LLM_API_KEY")
)

class EnrichRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=0, max_length=3000)

class EnrichResponse(BaseModel):
    category: str
    summary: str
    quality_flags: list[str]

VALID_CATEGORIES = ["fiction", "nonfiction", "childrens", "poetry", "reference", "other"]

def call_model(title: str, description: str) -> str:
    """Call the LLM and return its raw text response."""
    user_content = json.dumps({"title": title, "description": description})

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
    )
    return response.choices[0].message.content

@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if LLM_STUB:
        return EnrichResponse(
            category="other",
            summary="Stub summary — no model was called.",
            quality_flags=["stub_mode"]
        )

    raw_text = call_model(payload.title, payload.description)
    print(f"RAW MODEL OUTPUT: {raw_text}")

    raise HTTPException(status_code=501, detail="Parsing and validation not implemented yet")