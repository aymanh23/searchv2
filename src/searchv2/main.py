#!/usr/bin/env python
import sys
import warnings
import traceback
import time
from searchv2.crew import MedicalSearch
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the medical symptom interview crew with retry logic for API overload errors.
    """
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
