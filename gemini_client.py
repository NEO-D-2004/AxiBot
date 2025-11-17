# gemini_client.py
"""
Robust Gemini wrapper with static-checker friendly types.
Uses typing.cast to tell Pylance the response is dynamic (Any) and then
accesses attributes with getattr/fallback so runtime errors are handled.
"""

import os
from typing import Any, Optional, cast
from settings import GEMINI_API_KEY

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing. Set it in .env before running.")

# Ensure SDK env var expected by some SDK variants
os.environ["GENAI_API_KEY"] = GEMINI_API_KEY

# Try importing SDK (different package names across versions)
genai: Optional[Any] = None
try:
    from google import genai  # type: ignore
    genai = genai
except Exception:
    try:
        import google_genai as genai  # type: ignore
    except Exception as e:
        raise ImportError(
            "GenAI SDK not found. Run `pip install google-genai` or `pip install google-generativeai` "
            "in your project venv."
        ) from e

# Create client if available
_client: Any
if hasattr(genai, "Client"):
    try:
        _client = genai.Client()  # type: ignore
    except Exception:
        _client = genai
else:
    _client = genai

def _safe_extract_text_from_resp(resp: Any) -> Optional[str]:
    """
    Try common paths to extract text from a response object returned by Gemini SDK.
    Use casting to Any so static checker does not complain.
    """
    r = cast(Any, resp)

    # Try .text first (some SDK shapes provide this)
    text = getattr(r, "text", None)
    if isinstance(text, str):
        return text

    # Try nested .output -> content -> text
    try:
        out = getattr(r, "output", None)
        if out and len(out) > 0:
            # each element may have .content list
            cont = getattr(out[0], "content", None)
            if cont and len(cont) > 0:
                t = getattr(cont[0], "text", None)
                if isinstance(t, str):
                    return t
    except Exception:
        pass

    # Try other common shapes: resp.output_text, resp.result, resp.result.text etc.
    for attr in ("output_text", "result", "result_text", "message", "choices"):
        val = getattr(r, attr, None)
        if isinstance(val, str):
            return val
        # if choices is list of objects
        if isinstance(val, list) and len(val) > 0:
            candidate = getattr(val[0], "text", None) or getattr(val[0], "message", None)
            if isinstance(candidate, str):
                return candidate

    # Nothing found
    return None

def generate_reply(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """
    Generate reply using whatever SDK shape is available.
    Tries multiple call shapes and extracts text safely.
    """
    # 1) New-style: client.models.generate_content(...)
    try:
        models_obj = getattr(_client, "models", None)
        if models_obj is not None:
            gen_fn = getattr(models_obj, "generate_content", None)
            if callable(gen_fn):
                resp = gen_fn(model=model, contents=prompt)
                text = _safe_extract_text_from_resp(resp)
                if text:
                    return text
                return str(resp)

    except Exception:
        # ignore and try next shape
        pass

    # 2) Older-style: client.generate_text(...)
    try:
        gen_text = getattr(_client, "generate_text", None)
        if callable(gen_text):
            resp2 = gen_text(model=model, input=prompt)
            text = _safe_extract_text_from_resp(resp2)
            if text:
                return text
            return str(resp2)
    except Exception:
        pass

    # 3) Module-level helpers like genai.generate_text or genai.generate
    try:
        gen_fn = getattr(genai, "generate_text", None) or getattr(genai, "generate", None)
        if callable(gen_fn):
            resp3 = gen_fn(model=model, input=prompt)
            text = _safe_extract_text_from_resp(resp3)
            if text:
                return text
            return str(resp3)
    except Exception:
        pass

    raise RuntimeError("Failed to generate reply with the installed GenAI SDK.")
