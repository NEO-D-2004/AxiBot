# test_genai_import.py
import traceback
from gemini_client import generate_reply

try:
    print("Testing generate_reply")
    out = generate_reply("Say hello in one sentence.", model="gemini-2.5-flash")
    print("REPLY:", out)
except Exception as e:
    print("Generation failed:", e)
    traceback.print_exc()
