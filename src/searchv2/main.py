#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from searchv2.crew import MedicalSearch
from crewai_tools import WebsiteSearchTool
from dotenv import load_dotenv
load_dotenv(dotenv_path="medical_search/.env")

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def run():
    """
    Run the crew in a user-in-the-loop interactive mode: the agent reasons and asks follow-up questions, but only the user answers them.
    """
    crew = MedicalSearch().crew()
    # greeting = (
    #     "Hello! I'm your MedicalAI Assistant.\n"
    #     "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
    #     "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
    #     "To begin, could you please tell me what symptoms you're experiencing today?"
    # )
    # user_input = input(f"{greeting}\n> ")
    while True:
        try:
            result = crew.kickoff()
        except Exception as e:
            print(f"An error occurred while running the crew: {e}")
            break
        if isinstance(result, dict):
            message = result.get('message', '')
            follow_ups = result.get('follow_up_questions', [])
            print(message)
            if follow_ups:
                for q in follow_ups:
                    user_input = input(q + ' ')
                continue
            final = result.get('final_answer')
            if final:
                print(f"\nFinal Answer: {final}")
            break
        else:
            print(result)
            break
