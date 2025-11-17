# gemini_client.py
import os
from settings import GEMINI_API_KEY

# set env var for SDK if needed
os.environ.setdefault("GENAI_API_KEY", GEMINI_API_KEY)

# try possible imports
genai = None
try:
    from google import genai
    genai = genai
    # print("Imported google.genai")
except Exception:
    try:
        import google_genai as genai
    except Exception:
        raise ImportError(
            "Gemini SDK not installed. Run `pip install google-genai` or `pip install google-generativeai` "
            "and ensure your Python interpreter is the same virtualenv."
        )

# create client or use module
_client = None
if hasattr(genai, "Client"):
    _client = genai.Client()
else:
    _client = genai

def generate_reply(prompt, model="gemini-2.5-flash"):
    """
    Try common SDK call shapes. If your SDK uses a different method,
    run a small test to print the response shape and adapt.
    """
    # new-style: client.models.generate_content(...)
    try:
        resp = _client.models.generate_content(model=model, contents=prompt)
        # attempt to extract text
        text = getattr(resp, "text", None)
        if not text:
            # fallback
            try:
                text = resp.output[0].content[0].text
            except Exception:
                text = str(resp)
        return text
    except Exception:
        # fallback older SDKs
        try:
            resp = _client.generate_text(model=model, input=prompt)
            return getattr(resp, "text", str(resp))
        except Exception as e:
            raise RuntimeError("Gemini generate failed: " + str(e))
