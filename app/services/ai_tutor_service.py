import os
import requests
import json
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class AIExplanation:
    explanation: str
    suggested_level: str
    alternative_sentences: List[str]
    grammar_notes: List[str]

class AITutorService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Base Gemini API endpoint
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def explain_sentence(self, sentence: str, target_lang: str, native_lang: str) -> AIExplanation:
        if not self.api_key or "Ab8RN" in self.api_key: # Checking if it's the provided placeholder or empty
            # If the user provided a key that doesn't start with AIza, it might be invalid for direct REST
            # But we will try anyway.
            pass

        prompt = f"""
        You are a senior language tutor helping a learner whose native language is {native_lang} (Kazakh/kk).
        The learner is practicing {target_lang}.
        Explain the following sentence in a way that is easy to understand: "{sentence}"
        
        YOU MUST RETURN ONLY A JSON OBJECT with the following structure:
        {{
            "explanation": "a clear and helpful explanation in {native_lang}",
            "suggested_level": "CEFR level like A1, B2, etc.",
            "alternative_sentences": ["alt 1", "alt 2"],
            "grammar_notes": ["note 1 in {native_lang}", "note 2 in {native_lang}"]
        }}
        """

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Gemini response parsing
            text_content = data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean JSON if model wrapped it in markdown
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0].strip()
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text_content)
            
            return AIExplanation(
                explanation=result.get("explanation", "Түсініктеме табылмады."),
                suggested_level=result.get("suggested_level", "Unknown"),
                alternative_sentences=result.get("alternative_sentences", []),
                grammar_notes=result.get("grammar_notes", [])
            )
        except Exception as e:
            print(f"AI Service Error: {e}")
            return self._mock_explanation(sentence, native_lang)

    def provide_feedback(self, user_input: str, target_text: str) -> dict:
        if not self.api_key:
            return {"score": 0, "feedback": "API key missing.", "correction": target_text}

        prompt = f"""
        Compare the user's input: "{user_input}"
        With the target correct sentence: "{target_text}"
        Provide a score from 0 to 100 based on accuracy.
        Provide a brief feedback in Kazakh (kk) explaining any mistakes.
        Provide the final correction.
        
        RETURN ONLY JSON:
        {{
            "score": 85,
            "feedback": "Жақсы, бірақ мына жерде...",
            "correction": "{target_text}"
        }}
        """

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(self.api_url, json=payload, timeout=15)
            response.raise_for_status()
            text_content = response.json()['candidates'][0]['content']['parts'][0]['text']
            
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0].strip()
            
            return json.loads(text_content)
        except Exception as e:
            return {
                "score": 0,
                "feedback": f"AI-мен байланыс орнату мүмкін болмады: {str(e)}",
                "correction": target_text
            }

    def _mock_explanation(self, sentence: str, native_lang: str) -> AIExplanation:
        """Fallback mock for safety"""
        return AIExplanation(
            explanation=f"'{sentence}' сөйлемі бойынша AI сұранысы сәтсіз аяқталды. Бұл бағытта жұмыс істеп жатырмыз.",
            suggested_level="Intermediate",
            alternative_sentences=["Try again later"],
            grammar_notes=["API байланысын тексеріңіз."]
        )
