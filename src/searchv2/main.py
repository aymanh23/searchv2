#!/usr/bin/env python
import sys
import warnings
import traceback
import time
import asyncio
from searchv2.crew import MedicalSearch
from dotenv import load_dotenv
import os
from pathlib import Path
import random
import json
from threading import Lock, Thread
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from searchv2.session import SessionManager

load_dotenv()

# FastAPI app definition at the top
app = FastAPI(
    title="CrewAI Interaction API",
    description="API to interact with CrewAI agents for symptom analysis and reporting.",
    version="0.1.0"
)

# --- BEGIN ADDED CODE FOR CONVERSATION LOG ---
# Define the conversation log file path relative to the storage directory
# CREWAI_STORAGE_DIR is set further down, so we need to be careful about when this is resolved.
# Let's define it here and resolve its path after CREWAI_STORAGE_DIR is confirmed.
CONVERSATION_LOG_FILENAME = "human_interaction.log"
# --- END ADDED CODE FOR CONVERSATION LOG  ---

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


class ChatMessage(BaseModel):
    message: str

class RateLimiter:
    def __init__(self, max_requests_per_minute):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        with self.lock:
            now = datetime.now()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(minutes=1)]
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request is 1 minute old
                wait_time = 60 - (now - self.requests[0]).total_seconds()
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    # Update now after waiting
                    now = datetime.now()
                    # Clean up old requests again
                    self.requests = [req_time for req_time in self.requests 
                                   if now - req_time < timedelta(minutes=1)]
            
            # Add current request
            self.requests.append(now)

def is_vertex_ai_overload(error_message):
    """Check if the error is a VertexAI overload error"""
    try:
        if "VertexAIException" in error_message:
            error_data = json.loads(error_message.split("VertexAIException - ")[1])
            return error_data.get("error", {}).get("code") == 503
    except:
        pass
    return False

def load_conversation_history(log_file):
    """Load conversation history from log file"""
    if not log_file.exists():
        return []
    
    history = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                history.append(entry)
            except json.JSONDecodeError:
                continue
    return history

def save_conversation_state(log_file, state):
    """Save conversation state to log file"""
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(state) + '\n')

def run_crew_process(session_uuid: str):
    """
    Run the medical symptom interview crew in a separate thread
    """
    # Set custom storage path for CrewAI memory to avoid Windows path length issues
    project_root = Path(__file__).resolve().parent.parent # Assuming main.py is in src/searchv2
    storage_dir_path = project_root / "crewai_storage"
    storage_dir_path.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir_path.absolute())
    print(f"CrewAI memory storage will be at: {os.environ['CREWAI_STORAGE_DIR']}")
    
    # --- BEGIN ADDED CODE FOR CONVERSATION LOG ---
    # Initialize/clear the conversation log for this run
    conversation_log_file = storage_dir_path / f"human_interaction_{session_uuid}.log"
    session = SessionManager.get_session(session_uuid)
    session.log_file = conversation_log_file
    if conversation_log_file.exists():
        conversation_log_file.unlink()
    print(f"Conversation log for this run will be at: {conversation_log_file.absolute()}")
    # --- END ADDED CODE FOR CONVERSATION LOG ---

    # Load existing conversation history
    conversation_history = load_conversation_history(conversation_log_file)
    if conversation_history:
        print(f"Loaded {len(conversation_history)} previous conversation entries")

    # Initialize rate limiter - 20 requests per minute for VertexAI
    rate_limiter = RateLimiter(max_requests_per_minute=20)

    # Enhanced retry configuration for VertexAI
    max_retries = 8  # Increased retries for VertexAI
    base_delay = 15  # Start with 15 seconds for VertexAI
    max_delay = 120  # Maximum delay of 120 seconds
    jitter = 0.2     # Increased jitter to 20%

    try:
        for attempt in range(max_retries + 1):
            try:
                # Apply rate limiting before making the request
                rate_limiter.wait_if_needed()

                print(f"Creating crew... (attempt {attempt + 1}/{max_retries + 1})")
                crew = MedicalSearch(session.broker, conversation_log_file, patient_uuid=session_uuid).crew()
                session.crew_process = crew

                if conversation_history:
                    print("Restoring previous conversation state...")
                    for entry in conversation_history:
                        save_conversation_state(conversation_log_file, entry)

                print("Starting crew kickoff...")
                result = crew.kickoff()

                save_conversation_state(conversation_log_file, {
                    "timestamp": datetime.now().isoformat(),
                    "type": "completion",
                    "result": result
                })

                print("\n" + "="*50)
                print("SYMPTOM INTERVIEW COMPLETE")
                print("="*50)
                print(result)
                return result

            except Exception as e:
                error_message = str(e)
                print(f"An error occurred while running the crew: {e}")

                save_conversation_state(conversation_log_file, {
                    "timestamp": datetime.now().isoformat(),
                    "type": "error",
                    "error": error_message
                })

                if is_vertex_ai_overload(error_message):
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt) * (1 + jitter * (2 * random.random() - 1)), max_delay)
                        print(f"VertexAI model is overloaded. Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Max retries reached. The VertexAI model is experiencing high load.")
                        print("Please try again in a few minutes when the load is lower.")
                        break

                elif any(err in error_message.lower() for err in ["429", "rate limit", "too many requests"]):
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt) * (1 + jitter * (2 * random.random() - 1)), max_delay)
                        print(f"API rate limit detected. Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Max retries reached. API rate limit exceeded.")
                        print("Please try again later when the rate limit resets.")
                        break

                print("Full traceback:")
                traceback.print_exc()
                break  # Exit on non-retryable errors
    finally:
        SessionManager.cleanup_session(str(session_uuid))
@app.get("/")
async def read_root():
    return {"message": "CrewAI API is running"}

@app.get("/crew/kickoff")
async def run(session_uuid: str):
    """
    Run the medical symptom interview crew with rate limiting and enhanced retry logic.
    Returns the initial greeting message that will be asked to the user.
    """
    # Return the initial greeting message
    initial_greeting = (
        "Hello! I'm your MedicalAI Assistant.\n"
        "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
        "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
        "To begin, could you please tell me what symptoms you're experiencing today?"
    )

    session = SessionManager.get_session(session_uuid)

    if session.crew_thread is None or not session.crew_thread.is_alive():
        session.crew_thread = Thread(target=run_crew_process, args=(session_uuid,))
        session.crew_thread.daemon = True
        session.crew_thread.start()

    return {"question": initial_greeting}

@app.post("/chat")
async def chat(session_uuid: str, message: ChatMessage):
    """
    Handle chat messages from the user and return the next question
    """
    session = SessionManager.get_session(session_uuid)
    if session.crew_thread is None or not session.crew_thread.is_alive():
        raise HTTPException(status_code=400, detail="Crew process not started. Please call /crew/kickoff first")

    # Add the message to the HumanInputTool queue
    session.broker.add_message(message.message)

    async def wait_for_response():
        max_wait = 300  # 5 minutes
        wait_interval = 0.1
        attempts = int(max_wait / wait_interval)

        for _ in range(attempts):
            current_question = session.broker.get_question()
            if current_question:
                return {"question": current_question}
            await asyncio.sleep(wait_interval)
        
        raise HTTPException(
            status_code=408,
            detail="Timeout waiting for agent response. Please try again."
        )

    try:
        # Wait for response with timeout
        return await asyncio.wait_for(wait_for_response(), timeout=300)  # 5 minutes timeout
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Request timeout after 5 minutes. The crew is still processing your request. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

