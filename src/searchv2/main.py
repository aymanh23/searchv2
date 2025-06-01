#!/usr/bin/env python
import sys
import warnings
import traceback
import time
import os
from searchv2.session_manager import session_manager
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def check_system_compatibility():
    """Check if the system is compatible and set up properly"""
    try:
        print("🔍 Checking system compatibility...")
        
        # Check if we can access temp directory
        import tempfile
        temp_dir = tempfile.gettempdir()
        print(f"✅ Temp directory accessible: {temp_dir}")
        
        # Check if we can create directories
        test_dir = os.path.join(temp_dir, "medical_interview_test")
        os.makedirs(test_dir, exist_ok=True)
        os.rmdir(test_dir)
        print("✅ Directory creation works")
        
        # Check environment
        user_home = os.path.expanduser("~")
        print(f"✅ User home directory: {user_home}")
        
        print("✅ System compatibility check passed")
        return True
        
    except Exception as e:
        print(f"❌ System compatibility check failed: {e}")
        print("⚠️  Some features may not work properly")
        return False

def run():
    """
    Run the medical symptom interview crew with retry logic for API overload errors.
    Each run starts with a fresh session to prevent memory from previous interviews.
    """
    # Run compatibility check first
    check_system_compatibility()
    
    max_retries = 3
    retry_delay = 8  # seconds
    
    # Start a new session to ensure clean state
    session_id = session_manager.start_new_session()
    
    for attempt in range(max_retries + 1):
        try:
            print(f"Creating fresh crew instance... (attempt {attempt + 1}/{max_retries + 1})")
            
            # Get a fresh crew with no memory from previous sessions
            crew = session_manager.get_fresh_crew()
            
            print("Starting symptom interview...")
            print("🔄 Note: This is a fresh session - no previous interview data is retained")
            print("-" * 60)
            
            result = crew.kickoff()
            
            print("\n" + "="*50)
            print("SYMPTOM INTERVIEW COMPLETE")
            print("="*50)
            print(result)
            
            # End the session cleanly
            session_manager.end_session()
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
            
            # End session on error
            session_manager.end_session()
            break  # Exit on non-retryable errors

if __name__ == "__main__":
    run()
