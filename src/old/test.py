from google import genai
from google.genai import types

print("Contacting Gemini API...")
client = genai.Client(api_key="AIzaSyAs3u9PnTBDHldawpFkyqC9txh3rqRg_U8")
MODEL_ID = "gemini-2.5-flash"

print("Generating content...")
response = client.models.generate_content(
    model=MODEL_ID,
    contents="What's the largest planet in our solar system?"
)

print("Response:", response)