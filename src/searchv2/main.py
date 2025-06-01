#!/usr/bin/env python
import sys
import warnings
import traceback
import time
from searchv2.crew import MedicalSearch
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# --- BEGIN ADDED CODE FOR CONVERSATION LOG ---
# Define the conversation log file path relative to the storage directory
# CREWAI_STORAGE_DIR is set further down, so we need to be careful about when this is resolved.
# Let's define it here and resolve its path after CREWAI_STORAGE_DIR is confirmed.
CONVERSATION_LOG_FILENAME = "human_interaction.log"
# --- END ADDED CODE FOR CONVERSATION LOG ---

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the medical symptom interview crew with retry logic for API overload errors.
    """
    # Set custom storage path for CrewAI memory to avoid Windows path length issues
    project_root = Path(__file__).resolve().parent.parent # Assuming main.py is in src/searchv2
    storage_dir_path = project_root / "crewai_storage"
    storage_dir_path.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir_path.absolute())
    print(f"CrewAI memory storage will be at: {os.environ['CREWAI_STORAGE_DIR']}")

    # --- BEGIN ADDED CODE FOR CONVERSATION LOG ---
    # Initialize/clear the conversation log for this run
    conversation_log_file = storage_dir_path / CONVERSATION_LOG_FILENAME
    if conversation_log_file.exists():
        conversation_log_file.unlink()
    print(f"Conversation log for this run will be at: {conversation_log_file.absolute()}")
    # --- END ADDED CODE FOR CONVERSATION LOG ---

    max_retries = 3
    retry_delay = 8  # seconds
    
    for attempt in range(max_retries + 1):
        try:
            print(f"Creating crew... (attempt {attempt + 1}/{max_retries + 1})")
            crew = MedicalSearch().crew()
            print("Starting crew kickoff...")
            result = crew.kickoff()
            print("\n" + "="*50)
            print("SYMPTOM INTERVIEW COMPLETE")
            print("="*50)
            print(result)
            return  # Success - exit the function
            
        except Exception as e:
            error_message = str(e)
            print(f"An error occurred while running the crew: {e}")
            
            # Check if it's the API overload error
            if "overloaded" in error_message.lower() or "503" in error_message:
                if attempt < max_retries:
                    print(f"API overload detected. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print("Max retries reached. The Gemini API appears to be experiencing widespread issues.")
                    print("This is a Google server-side problem. Please try again later.")
            
            print("Full traceback:")
            traceback.print_exc()
            break  # Exit on non-retryable errors

if __name__ == "__main__":
    run()
