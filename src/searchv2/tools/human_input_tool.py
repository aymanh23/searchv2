from crewai.tools import BaseTool


class HumanInputTool(BaseTool):
    name: str = "Human Input"
    description: str = "Ask the user a follow-up question and get their answer."
    _first_call: bool = True  # Class attribute to track first call

    def _run(self, question: str) -> str:
        if HumanInputTool._first_call:
            HumanInputTool._first_call = False
            greeting = (
                "Hello! I'm your MedicalAI Assistant.\n"
                "I'm here to help collect and organize details about your symptoms so your doctor can better understand what you're experiencing.\n"
                "I'll ask you a few questions — just answer in your own words, and I'll take care of the rest.\n"
                "To begin, could you please tell me what symptoms you're experiencing today?"
            )
            return input(f"{greeting}\n> ")
        else:
            return input(f"{question}\n")
