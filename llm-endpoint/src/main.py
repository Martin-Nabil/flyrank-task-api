import os
import json
import re
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
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

VALID_CATEGORIES = ["fiction", "nonfiction", "childrens", "poetry", "reference", "other"]

class EnrichResponse(BaseModel):
    category: str
    summary: str
    quality_flags: list[str]

    @classmethod
    def validate_category(cls, value):
        if value not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {value!r}")
        return value

def call_model(title: str, description: str, extra_context: str | None = None) -> str:
    """Call the LLM and return its raw text response."""
    user_content = json.dumps({"title": title, "description": description})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    if extra_context:
        messages.append({"role": "user", "content": extra_context})

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=messages
    )
    return response.choices[0].message.content

def extract_json(raw_text: str) -> dict:
    """Strip code fences and other wrapping, then parse JSON. Raises on failure."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")

    return json.loads(match.group())

def validate_record(data: dict) -> EnrichResponse:
    """Validate parsed data against our schema, including the category enum."""
    record = EnrichResponse(**data)
    if record.category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {record.category!r}")
    return record

def quarantine(payload: EnrichRequest, raw_text: str, error: str):
    """Log a failed record to the quarantine file."""
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": payload.model_dump(),
        "raw_output": raw_text,
        "error": error,
        "prompt_version": PROMPT_VERSION
    }
    with open("logs/quarantine.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if LLM_STUB:
        return EnrichResponse(
            category="other",
            summary="Stub summary — no model was called.",
            quality_flags=["stub_mode"]
        )

    raw_text = call_model(payload.title, payload.description)

    try:
        data = extract_json(raw_text)
        record = validate_record(data)
        return record
    except (ValueError, ValidationError, json.JSONDecodeError) as first_error:
        repair_context = (
            f"Your previous response was invalid. "
            f"Response: {raw_text}\n"
            f"Error: {first_error}\n"
            f"Reply again with ONLY corrected JSON matching the required schema."
        )
        raw_text_2 = call_model(payload.title, payload.description, extra_context=repair_context)

        try:
            data_2 = extract_json(raw_text_2)
            record_2 = validate_record(data_2)
            return record_2
        except (ValueError, ValidationError, json.JSONDecodeError) as second_error:
            quarantine(payload, raw_text_2, str(second_error))
            raise HTTPException(status_code=422, detail="Model could not produce a valid response")