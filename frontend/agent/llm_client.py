import os
import json
from groq import Groq
from openai import OpenAI

class LLMFailure(Exception):
    pass

def run_llm_with_failover(primary_fn, fallback_fn, **kwargs):
    try:
        return primary_fn(**kwargs)
    except LLMFailure as e:
        print(f"Primary LLM failed: {e}. Switching to fallback...")
        return fallback_fn(**kwargs)

def groq_call(model, prompt, input, response_model, **kwargs):
     api_key = os.environ.get("GROQ_API_KEY")
     if not api_key:
         raise LLMFailure("GROQ_API_KEY not found")

     client = Groq(api_key=api_key)

     # Map internal model names to Groq model IDs
     # Using 'llama-3.1-8b-instant' as it is confirmed working
     groq_model = "llama-3.1-8b-instant"
         
     # Inject Schema
     schema = json.dumps(response_model.model_json_schema(), indent=2)
     full_prompt = f"{prompt}\n\nJSON Schema:\n{schema}"
     
     messages = [
         {"role": "system", "content": full_prompt},
         {"role": "user", "content": input}
     ]
     
     try:
         chat_completion = client.chat.completions.create(
             model=groq_model,
             messages=messages,
             response_format={"type": "json_object"},
             temperature=0.0
         )
         
         content = chat_completion.choices[0].message.content
         if not content:
             raise LLMFailure("Empty response from Groq")
             
         return response_model.model_validate_json(content)
         
     except Exception as e:
         raise LLMFailure(f"Groq API Error: {str(e)}")

def openrouter_call(model, prompt, input, response_model, **kwargs):
     api_key = os.environ.get("OPENROUTER_API_KEY")
     if not api_key:
         raise LLMFailure("OPENROUTER_API_KEY not found")
    
     client = OpenAI(
         base_url="https://openrouter.ai/api/v1",
         api_key=api_key,
     )

     # Use verified working model
     or_model = "google/gemini-2.0-flash-001"
     
     # Inject Schema
     schema = json.dumps(response_model.model_json_schema(), indent=2)
     full_prompt = f"{prompt}\n\nJSON Schema:\n{schema}"
     
     messages = [
         {"role": "system", "content": full_prompt},
         {"role": "user", "content": input}
     ]
     
     try:
         completion = client.chat.completions.create(
            model=or_model,
            messages=messages,
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Compliance Agent"
            }
         )
         
         content = completion.choices[0].message.content
         if not content:
              raise LLMFailure("Empty response from OpenRouter")

         # Clean markdown if present
         if "```json" in content:
             content = content.split("```json")[1].split("```")[0].strip()
         elif "```" in content:
             content = content.split("```")[1].split("```")[0].strip()

         return response_model.model_validate_json(content)
         
     except Exception as e:
         raise LLMFailure(f"OpenRouter API Error: {str(e)}")
