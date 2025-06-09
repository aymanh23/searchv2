from crewai.tools import BaseTool
import os
from pathlib import Path
from typing import Optional

CONVERSATION_LOG_FILENAME = "human_interaction.log" # Consistent with main.py and human_input_tool.py

def get_conversation_log_path(session_uuid: str = None) -> Path:
    storage_dir_env = os.environ.get("CREWAI_STORAGE_DIR")
    if not storage_dir_env:
        # This should ideally not happen if main.py has run and set the ENV var
        print("Warning: CREWAI_STORAGE_DIR not found. ConversationLogReaderTool might fail.")
        # Fallback to a local path, though this is not ideal
        if session_uuid:
            return Path(".") / f"human_interaction_{session_uuid}.log"
        return Path(".") / CONVERSATION_LOG_FILENAME 
    
    if session_uuid:
        return Path(storage_dir_env) / f"human_interaction_{session_uuid}.log"
    return Path(storage_dir_env) / CONVERSATION_LOG_FILENAME

class ConversationLogReaderTool(BaseTool):
    name: str = "Conversation Log Reader"
    description: str = "Reads the entire history of the current human-AI conversation from the log file. Use this first to understand what has already been discussed."
    session_uuid: Optional[str] = None

    def _run(self) -> str:
        log_file_path = get_conversation_log_path(self.session_uuid)
        if not log_file_path.exists():
            return "Conversation log is empty or does not exist. This might be the start of a new conversation."
        
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                history = f.read()
            if not history.strip():
                return "Conversation log is empty. This is the start of a new conversation."
            return f"Current conversation history:\n---\n{history}\n---" 
        except Exception as e:
            return f"Error reading conversation log: {str(e)}"

# Example usage (for testing - not part of the tool itself)
if __name__ == '__main__':
    # For this example to work, CREWAI_STORAGE_DIR would need to be set
    # and human_interaction.log would need to exist in it.
    # You would typically set this in your main application script.
    # os.environ["CREWAI_STORAGE_DIR"] = "./crewai_storage" 
    # Path(os.environ["CREWAI_STORAGE_DIR"]).mkdir(exist_ok=True)
    # with open(Path(os.environ["CREWAI_STORAGE_DIR"]) / CONVERSATION_LOG_FILENAME, "w") as f:
    #     f.write("Example log entry\n")

    tool = ConversationLogReaderTool()
    print(tool.run()) 