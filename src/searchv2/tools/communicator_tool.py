from crewai.tools import BaseTool
from typing import Type, List, Dict, Optional
from pydantic import BaseModel, Field

# For language detection and translation
try:
    from langdetect import detect
    from googletrans import Translator
except ImportError:
    detect = None
    Translator = None


class CommunicatorInput(BaseModel):
    user_input: str = Field(...,
                            description="User's message or symptom description.")
    follow_up_questions: Optional[List[str]] = Field(
        None, description="List of follow-up questions to present to the user.")
    context: Optional[Dict] = Field(
        default_factory=dict, description="Conversation context (symptoms, history, etc.)")


class CommunicatorTool(BaseTool):
    name: str = "Communicator Tool"
    description: str = (
        "Handles user interaction: extracts symptoms, manages context, detects language, translates if needed, and presents follow-up questions."
    )
    args_schema: Type[BaseModel] = CommunicatorInput

    def _run(self, user_input: str, follow_up_questions: Optional[List[str]] = None, context: Optional[Dict] = None) -> Dict:
        # Detect language
        lang = 'en'
        if detect:
            try:
                lang = detect(user_input)
            except Exception:
                lang = 'en'
        # Translate if Turkish
        processed_input = user_input
        if lang == 'tr' and Translator:
            try:
                translator = Translator()
                processed_input = translator.translate(
                    user_input, src='tr', dest='en').text
            except Exception:
                processed_input = user_input
        # No keyword extraction here; let the LLM agent handle it
        if context is None:
            context = {}
        context['last_input'] = user_input
        # Present follow-up questions if any
        answers = {}
        if follow_up_questions:
            for q in follow_up_questions:
                print(q)  # CLI: print question
                ans = input('> ')
                answers[q] = ans
        return {
            'message': "Input processed. Symptom extraction is handled by the agent.",
            'context': context,
            'lang': lang,
            'follow_up_answers': answers
        }

    def extract_symptoms(self, text: str) -> List[str]:
        # Placeholder: extract words like 'pain', 'fever', etc. Replace with LLM/spaCy later.
        keywords = ['pain', 'fever', 'cough', 'headache',
                    'nausea', 'vomiting', 'dizziness', 'fatigue', 'rash']
        found = [word for word in keywords if word in text.lower()]
        return found
