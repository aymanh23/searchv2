from crewai.tools import BaseTool
import os
import tempfile
import json
from pathlib import Path


class HumanInputTool(BaseTool):
    name: str = "Human Input"
    description: str = "Ask the user a follow-up question and get their answer."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session_state_file = None
    
    def _get_session_state_file(self):
        """Get the session state file path"""
        if self._session_state_file is None:
            # Use a session-specific state file that persists across tool recreation
            session_dir = Path(tempfile.gettempdir()) / "medical_interview_sessions"
            session_dir.mkdir(exist_ok=True)
            
            # Try to get session ID from environment or create a default
            session_id = os.environ.get('CURRENT_SESSION_ID', 'default_session')
            self._session_state_file = session_dir / f"{session_id}_state.json"
        
        return self._session_state_file
    
    def _load_session_state(self):
        """Load session state from file"""
        state_file = self._get_session_state_file()
        try:
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                return state.get('first_call', True)
            return True
        except:
            return True
    
    def _save_session_state(self, first_call):
        """Save session state to file"""
        state_file = self._get_session_state_file()
        try:
            state = {'first_call': first_call}
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except:
            pass  # Fail silently if can't save
    
    def reset_session(self):
        """Reset the tool for a new session"""
        self._session_state_file = None
        # Clear any existing state file
        try:
            state_file = self._get_session_state_file()
            if state_file.exists():
                state_file.unlink()
        except:
            pass
        # Reset to first call
        self._save_session_state(True)

    def _run(self, question: str) -> str:
        # Load current state
        is_first_call = self._load_session_state()
        
        if is_first_call:
            # Mark as no longer first call
            self._save_session_state(False)
            
            greeting = (
                "Hello! I'm your MedicalAI Assistant.\n"
                "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
                "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
                "To begin, could you please tell me what symptoms you're experiencing today?"
            )
            return input(f"{greeting}\n> ")
        else:
            return input(f"{question}\n> ")
