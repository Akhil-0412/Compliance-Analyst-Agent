"""
LLM Client — Extracted provider initialization and failover API call logic.
"""
import os
import logging
from groq import Groq
from openai import OpenAI
import instructor
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(filename="backend_debug.log", level=logging.INFO)


def get_llm_client():
    """
    Initializes and returns the LLM client configuration.
    Returns: (base_client, instructor_client, models, provider_name)
    """
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if groq_key:
        print("Using Groq Provider")
        models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "gemma2-9b-it",
        ]
        base_client = Groq(api_key=groq_key)
        client = instructor.from_groq(base_client, mode=instructor.Mode.TOOLS)
        return base_client, client, models, "groq"

    elif openrouter_key:
        print("Using OpenRouter Provider")
        models = [
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.1-8b-instruct",
        ]
        base_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )
        client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
        return base_client, client, models, "openrouter"

    elif google_key:
        print("Using Google Gemini Provider")
        models = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]
        base_client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=google_key,
        )
        client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
        return base_client, client, models, "google"

    else:
        raise ValueError("No API Key found. Set GROQ_API_KEY, OPENROUTER_API_KEY, or GOOGLE_API_KEY.")


def safe_api_call(base_client, instructor_client, models, messages,
                  temperature=0, response_model=None):
    """
    ULTIMATE FAILOVER LOOP — tries every model in sequence.
    Returns the parsed response or raises RuntimeError.
    """
    errors = []

    for model in models:
        try:
            masked_model = model[:30]
            logging.info(f"Trying Model: {masked_model}")

            if response_model:
                response = instructor_client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    response_model=response_model,
                )
            else:
                response = base_client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                )

            logging.info(f"[OK] Success with {masked_model}")
            return response

        except Exception as e:
            error_msg = str(e).lower()
            # Short-circuit on schema validation errors — no retry will fix them
            if "tool call validation failed" in error_msg or "validation error" in error_msg:
                logging.critical(f"[ABORT] SCHEMA MISMATCH: {error_msg}")
                raise RuntimeError(f"Schema Validation Error: {error_msg}")

            logging.error(f"[ERR] Error on {model}: {str(e)}")
            errors.append(f"{model}: {str(e)}")
            print(f"[FALLBACK] Downgrading: {model} failed, trying next...")
            continue

    raise RuntimeError(
        f"[OUTAGE] SERVICE OUTAGE: All {len(models)} models exhausted. Errors: {errors[:3]}"
    )
