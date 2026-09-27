import google.auth
from google import genai
from google.genai import types

credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
client = genai.Client(vertexai=True, project="qwiklabs-gcp-03-cc7caa2edc63", location="global")

try:
    resp = client.models.generate_content(
        model="gemini-omni-flash-preview",
        contents="A short video demonstrating ER triage assessment.",
        config=types.GenerateContentConfig(
            response_modalities=["VIDEO"]
        )
    )
    print("generate_content response:", resp)
except Exception as e:
    print("generate_content error:", e)

try:
    resp = client.interactions.create(
        model="gemini-omni-flash-preview",
        input="A short video demonstrating ER triage assessment.",
        generation_config={
            "response_modalities": ["VIDEO"]
        }
    )
    print("interactions.create type:", type(resp))
    print("interactions.create output:", resp)
except Exception as e:
    print("interactions.create error:", e)
