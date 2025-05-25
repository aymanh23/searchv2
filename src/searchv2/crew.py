from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from searchv2.tools.human_input_tool import HumanInputTool
from crewai_tools import WebsiteSearchTool
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators


@CrewBase
class MedicalSearch():
    """MedicalSearch crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools

    # Communicator agent: interacts with user, extracts symptoms, calls search agent as needed

    @tool
    def WebsiteSearchTool(self):
        from crewai_tools import WebsiteSearchTool
        return WebsiteSearchTool(
            config=dict(
                llm=dict(
                    # or google, openai, anthropic, llama2, ...
                    provider="google",
                    config=dict(
                        model="gemini/gemini-2.5-flash-preview-05-20",
                        # temperature=0.5,
                        # top_p=1,
                        # stream=true,
                    ),
                ),
                embedder=dict(
                    provider="google",  # or openai, ollama, ...
                    config=dict(
                        model="models/embedding-001",
                        task_type="retrieval_document",
                        # title="Embeddings",
                    ),
                ),
            )
        )

    @agent
    def communicator(self) -> Agent:
        return Agent(
            config=self.agents_config['communicator'],
            verbose=True,
            tools=[HumanInputTool()],
            force_tool_output=False,
        )
    # Main user-facing task

    @task
    def communicate_task(self) -> Task:
        return Task(
            config=self.tasks_config['communicate_task'],
        )

    # Search task, called by communicator for each symptom
    @task
    def search_task(self) -> Task:
        return Task(
            config=self.tasks_config['search_task'],
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            verbose=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
