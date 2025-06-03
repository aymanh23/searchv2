from crewai.tools import BaseTool
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from threading import Event
from pydantic import Field, PrivateAttr

class MessageBroker:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageBroker, cls).__new__(cls)
            cls._instance.messages = []
            cls._instance.current_question = None
            cls._instance.new_message_event = Event()
        return cls._instance

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
    description: str = "Ask the user a follow-up question and get their answer. IMPORTANT: Only use the exact symptoms provided by the user, do not add or modify symptoms."
    _first_call: bool = True  # Class attribute to track first call
    _conversation_log_file = None
    _last_response = None  # Track the last user response
    _broker: MessageBroker = PrivateAttr(default_factory=MessageBroker)

    @classmethod
    def set_conversation_log(cls, log_file):
        cls._conversation_log_file = log_file

    @classmethod
    def get_current_question(cls) -> Optional[str]:
        """Get the current question being asked"""
        return MessageBroker().get_question()

    @classmethod
    def add_user_message(cls, message: str):
        """Add a user message to the queue"""
        MessageBroker().add_message(message)

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
        if HumanInputTool._first_call: pass 
        else: self._broker.set_question(question)
        

        if HumanInputTool._first_call:
            HumanInputTool._first_call = False
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

    @classmethod
    def get_last_response(cls) -> str:
        """Get the last raw response from the user"""
        return cls._last_response if cls._last_response else ""