from crewai.tools import BaseTool


class HumanInputTool(BaseTool):
    name: str = "Human Input"
    description: str = "Ask the user a follow-up question and get their answer."

    def _run(self, question: str) -> str:
        return input(f"{question}\n")
