import os
import sys
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

# Load environment variables
load_dotenv()

def verify_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Groq: API Key Missing")
        return False
    
    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": "Hello world"}
            ],
            model="llama-3.1-8b-instant",
        )
        print(f"✅ Groq: Connection Successful (Response: {chat_completion.choices[0].message.content[:20]}...)")
        return True
    except Exception as e:
        print(f"❌ Groq: Connection Failed ({str(e)})")
        return False

def verify_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OpenRouter: API Key Missing")
        return False

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        completion = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {"role": "user", "content": "Hello world"}
            ]
        )
        print(f"✅ OpenRouter: Connection Successful (Response: {completion.choices[0].message.content[:20]}...)")
        return True
    except Exception as e:
        print(f"❌ OpenRouter: Connection Failed ({str(e)})")
        return False

if __name__ == "__main__":
    print("🔌 Verifying API Connections...")
    groq_status = verify_groq()
    or_status = verify_openrouter()
    
    if groq_status and or_status:
        print("\n✨ All systems operational.")
        sys.exit(0)
    else:
        print("\n⚠️ Some connections failed.")
        sys.exit(1)
