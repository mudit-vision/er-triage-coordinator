import os
from app.tools import generate_triage_instruction_video

print("Testing generate_triage_instruction_video tool...")
res = generate_triage_instruction_video("A 5-second instructional video showing emergency CPR technique.")
print("Tool result:\n", res)
