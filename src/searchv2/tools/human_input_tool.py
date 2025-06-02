from crewai.tools import BaseTool
import json
from pathlib import Path
from datetime import datetime


class HumanInputTool(BaseTool):
    name: str = "Human Input"
    description: str = "Ask the user a follow-up question and get their answer. IMPORTANT: Only use the exact symptoms provided by the user, do not add or modify symptoms."
    _first_call: bool = True  # Class attribute to track first call
    _conversation_log_file = None
    _last_response = None  # Track the last user response

    @classmethod
    def set_conversation_log(cls, log_file):
        cls._conversation_log_file = log_file

    def _save_interaction(self, question: str, answer: str):
        """Save the interaction to the conversation log"""
        if self._conversation_log_file:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "interaction",
                "question": question,
                "answer": answer,
                "raw_input": answer  # Store the raw input for verification
            }
            with open(self._conversation_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')

    def _validate_response(self, response: str) -> str:
        """Validate and clean the response"""
        # Store the raw response
        self._last_response = response.strip()
        return self._last_response

    def _run(self, question: str) -> str:
        if HumanInputTool._first_call:
            HumanInputTool._first_call = False
            greeting = (
                "Hello! I'm your MedicalAI Assistant.\n"
                "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
                "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
                "To begin, could you please tell me what symptoms you're experiencing today?"
            )
            answer = input(f"{greeting}\n> ")
            validated_answer = self._validate_response(answer)
            self._save_interaction(greeting, validated_answer)
            return validated_answer
        else:
            answer = input(f"{question}\n> ")
            validated_answer = self._validate_response(answer)
            self._save_interaction(question, validated_answer)
            return validated_answer

    @classmethod
    def get_last_response(cls) -> str:
        """Get the last raw response from the user"""
        return cls._last_response if cls._last_response else ""