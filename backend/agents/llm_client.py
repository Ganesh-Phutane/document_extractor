"""
agents/llm_client.py
────────────────────
Lightweight wrapper around Gemini API for structured extraction.
"""
import json
from typing import Any
import google.generativeai as genai
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

class LLMClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in settings")
            raise ValueError("GEMINI_API_KEY must be configured.")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def get_completion(self, prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
        """
        Sends a prompt to Gemini and returns the text response.
        Set json_mode=True to force Gemini to return structured JSON.
        """
        try:
            logger.info("Sending prompt to Gemini", extra={"model": settings.GEMINI_MODEL})
            
            gen_config = {}
            if json_mode:
                gen_config["response_mime_type"] = "application/json"
            
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"SYSTEM: {system_instruction}\n\nUSER: {prompt}"
            
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=gen_config if gen_config else None
            )
            
            text = response.text.strip()
            # Only warn if we expected JSON and didn't get it
            if json_mode and not (text.startswith("{") or text.startswith("[")):
                logger.warning("Gemini response is NOT JSON", extra={"response": text[:100]})
            
            return text
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise

    def parse_json(self, text: str) -> Any:
        """Helper to parse JSON and ensure array-based structures where needed."""
        try:
            # Strip markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.strip().endswith("```"):
                text = text.strip()[:-3]
            
            data = json.loads(text.strip())
            
            # Recursive safety: Convert objects with only numeric keys into arrays
            def ensure_arrays(obj):
                if isinstance(obj, dict):
                    # Check if all keys are numeric strings "0", "1", "2"...
                    is_numeric_index = all(k.isdigit() for k in obj.keys()) and len(obj) > 0
                    if is_numeric_index:
                        # Convert to sorted list based on numeric keys
                        sorted_keys = sorted(obj.keys(), key=int)
                        return [ensure_arrays(obj[k]) for k in sorted_keys]
                    else:
                        return {k: ensure_arrays(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [ensure_arrays(i) for i in obj]
                return obj
            
            return ensure_arrays(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {str(e)}", extra={"text": text[:500]})
            raise ValueError("Invalid JSON response from LLM")
