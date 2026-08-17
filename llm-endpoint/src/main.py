import os
import json
import re
import time
import random
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, APIStatusError

load_dotenv()

app = FastAPI(title="LLM Enrich Endpoint")

LLM_STUB = os.environ.get("LLM_STUB", "0") == "1"
LLM_ENABLED = os.environ.get("LLM_ENABLED", "true").lower() != "false"
PROMPT_VERSION = "enrich-v1"
TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2

def log_cost(model, input_tokens, output_tokens, duration, repaired):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_seconds": duration,
        "repaired": repaired
    }
    with open("logs/cost.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
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

def call_model(title: str, description: str, extra_context: str | None = None, repaired: bool = False) -> str:
    """Call the LLM with timeout and retry policy. Returns raw text response."""
    user_content = json.dumps({"title": title, "description": description})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    if extra_context:
        messages.append({"role": "user", "content": extra_context})

    model_name = os.environ["LLM_MODEL"]
    attempt = 0
    last_error = None

    while attempt <= MAX_RETRIES:
        start = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.2,
                messages=messages,
                timeout=TIMEOUT_SECONDS
            )
            duration = time.monotonic() - start

            usage = response.usage
            log_cost(
                model=model_name,
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
                duration=duration,
                repaired=repaired
            )

            return response.choices[0].message.content

        except APITimeoutError as e:
            last_error = e
            duration = time.monotonic() - start
            print(f"TIMEOUT on attempt {attempt + 1}: {e}")

        except APIStatusError as e:
            status = e.status_code
            if status in (400, 401, 403):
                raise HTTPException(status_code=502, detail=f"Model provider rejected the request ({status})")
            last_error = e
            print(f"HTTP {status} on attempt {attempt + 1}: {e}")

            if status == 429:
                retry_after = e.response.headers.get("Retry-After") if hasattr(e, "response") else None
                if retry_after:
                    time.sleep(float(retry_after))
                    attempt += 1
                    continue

        attempt += 1
        if attempt <= MAX_RETRIES:
            backoff = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(backoff)

    raise HTTPException(status_code=504, detail="Model did not respond in time after retries")

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
    if not LLM_ENABLED:
        raise HTTPException(status_code=503, detail="LLM feature is currently disabled")

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
        raw_text_2 = call_model(payload.title, payload.description, extra_context=repair_context, repaired=True)

        try:
            data_2 = extract_json(raw_text_2)
            record_2 = validate_record(data_2)
            return record_2
        except (ValueError, ValidationError, json.JSONDecodeError) as second_error:
            quarantine(payload, raw_text_2, str(second_error))
            raise HTTPException(status_code=422, detail="Model could not produce a valid response")