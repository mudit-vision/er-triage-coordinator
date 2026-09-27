import google.auth
from google import genai

credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
client = genai.Client(vertexai=True, project="qwiklabs-gcp-03-cc7caa2edc63", location="global")

try:
    resp = client.interactions.create(
        model="gemini-omni-flash-preview",
        input="A 5-second instructional video showing CPR chest compression technique.",
        generation_config={
            "response_modalities": ["VIDEO"]
        }
    )
    print("Response type:", type(resp))
    print("Response dict:", resp.model_dump() if hasattr(resp, "model_dump") else resp)
except Exception as e:
    print("Error calling interactions.create:", e)
