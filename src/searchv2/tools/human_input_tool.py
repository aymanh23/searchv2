from crewai.tools import BaseTool
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from threading import Event

class MessageBroker:
    """Simple message broker used for passing user input to the crew."""

    def __init__(self) -> None:
        self.messages = []
        self.current_question = None
        self.new_message_event = Event()

    def add_message(self, message: str):
        self.messages.append(message)
        self.new_message_event.set()

    def get_message(self) -> str:
        while not self.messages:
            self.new_message_event.wait()
            self.new_message_event.clear()
        return self.messages.pop(0)

    def set_question(self, question: str):
        self.current_question = question

    def get_question(self) -> Optional[str]:
        return self.current_question

class HumanInputTool(BaseTool):
    name: str = "Human Input"
    description: str = (
        "Ask the user a follow-up question and get their answer. IMPORTANT: "
        "Only use the exact symptoms provided by the user, do not add or modify symptoms."
    )

    def __init__(self, broker: MessageBroker, conversation_log: Optional[Path] = None):
        super().__init__()
        self._first_call = True
        self._conversation_log_file = conversation_log
        self._last_response = None
        self._broker: MessageBroker = broker

    def set_conversation_log(self, log_file: Path) -> None:
        self._conversation_log_file = log_file

    def get_current_question(self) -> Optional[str]:
        """Get the current question being asked"""
        return self._broker.get_question()

    def add_user_message(self, message: str) -> None:
        """Add a user message to the queue"""
        self._broker.add_message(message)

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
        # Store the current question
        if self._first_call:
            pass
        else:
            self._broker.set_question(question)

        if self._first_call:
            self._first_call = False
            greeting = (
                "Hello! I'm your MedicalAI Assistant.\n"
                "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
                "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
                "To begin, could you please tell me what symptoms you're experiencing today?"
            )
            # Wait for user's response
            answer = self._broker.get_message()
            validated_answer = self._validate_response(answer)
            self._save_interaction(greeting, validated_answer)
            return validated_answer
        else:
            # Wait for user's response
            answer = self._broker.get_message()
            validated_answer = self._validate_response(answer)
            self._save_interaction(question, validated_answer)
            return validated_answer

    def get_last_response(self) -> str:
        """Get the last raw response from the user"""
        return self._last_response if self._last_response else ""
