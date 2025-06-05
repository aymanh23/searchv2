from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from searchv2.tools.human_input_tool import HumanInputTool, MessageBroker
from searchv2.tools.report_generation_tool import ReportGenerationTool
from searchv2.tools.serper_tool import SerperSearchTool
from searchv2.tools.trusted_medical_search_tool import TrustedMedicalSearchTool
from crewai_tools import WebsiteSearchTool
import os
from pathlib import Path
import logging
import time
from functools import wraps
import yaml

logger = logging.getLogger(__name__)

def retry_on_empty(max_retries: int = 3, delay: float = 1.0,
                  fallback: str = "No response, please try again later."):
    """Decorator to retry on empty responses."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, max_retries + 1):
                result = func(self, *args, **kwargs)
                if result is not None and str(result).strip() != "":
                    return result
                logger.warning(
                    "Empty response from agent '%s' (attempt %s/%s)",
                    getattr(self, "name", "unknown"),
                    attempt,
                    max_retries,
                )
                time.sleep(delay)

            logger.error(
                "Agent '%s' returned no response after %s attempts",
                getattr(self, "name", "unknown"),
                max_retries,
            )

            name = getattr(self, "name", "").lower()
            if "communicator" in name or "interviewer" in name:
                return "I'm having trouble responding, please wait a moment"
            return fallback
        return wrapper
    return decorator

# Patch the Agent class with the retry decorator
Agent.execute_task = retry_on_empty()(Agent.execute_task)

@CrewBase
class MedicalSearch():
    """MedicalSearch crew"""

    def __init__(self, broker: MessageBroker, conversation_log: Path, patient_uuid: str = ""):
        config_dir = Path(__file__).parent / "config"
        with open(config_dir / "agents.yaml", "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(config_dir / "tasks.yaml", "r") as f:
            self.tasks_config = yaml.safe_load(f)
        self._broker = broker
        self._conversation_log = conversation_log
        self._patient_uuid = patient_uuid

        # Initialize agents in correct dependency order
        # First initialize agents that don't depend on others
        self._search_agent = self.search_agent()
        self._report_generator_agent = self.report_generator()
        
        # Then initialize agents that depend on the independent ones
        self._symptom_validator_agent = self.symptom_validator()
        self._diagnosis_agent = self.diagnosis_agent()
        
        # Finally initialize the communicator that depends on others
        self._communicator_agent = self.communicator()

        # Instantiate tasks once and reuse them
        self._symptom_interview_task = Task(
            config=self.tasks_config['symptom_interview_task'],
            agent=self._communicator_agent,
            human_input=False,
            max_rpm=40,
            context=[]
        )

        self._validation_task = Task(
            config=self.tasks_config['validation_task'],
            agent=self._symptom_validator_agent,
            human_input=False,
            context=[self._symptom_interview_task],
            max_rpm=40
        )

        self._diagnosis_task = Task(
            config=self.tasks_config['diagnosis_task'],
            agent=self._diagnosis_agent,
            human_input=False,
            context=[self._symptom_interview_task, self._validation_task],
            max_rpm=40
        )

        self._report_task = Task(
            config=self.tasks_config['report_task'],
            agent=self._report_generator_agent,
            human_input=False,
            context=[
                self._symptom_interview_task,
                self._validation_task,
                self._diagnosis_task,
            ],
            max_rpm=40
        )

    @tool
    def WebsiteSearchTool(self):
        from crewai_tools import WebsiteSearchTool
        return WebsiteSearchTool(
            config=dict(
                llm=dict(
                    provider="google",
                    config=dict(
                        model="gemini-1.5-pro",
                        temperature=0.3,
                        max_tokens=1000,
                    ),
                ),
                embedder=dict(
                    provider="google",
                    config=dict(
                        model="models/embedding-001",
                        task_type="retrieval_document",
                    ),
                ),
            )
        )

    @tool
    def SerperSearchTool(self):
        return SerperSearchTool()

    @tool
    def TrustedMedicalSearchTool(self):
        return TrustedMedicalSearchTool()

    @tool
    def HumanInputTool(self):
        return HumanInputTool(broker=self._broker, conversation_log=self._conversation_log)

    @tool
    def ReportGenerationTool(self):
        return ReportGenerationTool(patient_uuid=self._patient_uuid)

    @agent
    def communicator(self) -> Agent:
        return Agent(
            config=self.agents_config['communicator'],
            tools=[self.HumanInputTool()],
            verbose=True,
            allow_delegation=True,
            allowed_agents=["Researcher", "Validator"],  # Match exact role names from agents.yaml
            llm="gemini/gemini-1.5-pro",
            memory=False,
            max_rpm=50
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            tools=[self.TrustedMedicalSearchTool(), self.SerperSearchTool(), self.WebsiteSearchTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-1.5-pro",
            memory=False,
            max_rpm=40               
        )

    @agent
    def diagnosis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['diagnosis_agent'],
            verbose=True,
            allow_delegation=True,
            allowed_agents=["Researcher"],  # Match exact role name from agents.yaml
            llm="gemini/gemini-1.5-pro",
            memory=False,
            max_rpm=40       
        )

    @agent  
    def report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['report_generator'],
            tools=[self.ReportGenerationTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-1.5-pro",
            memory=False,
            max_rpm=40
        )

    @agent
    def symptom_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['symptom_validator'],
            verbose=True,
            allow_delegation=True,
            allowed_agents=["Interviewer"],  # Match exact role name from agents.yaml
            llm="gemini/gemini-1.5-pro",
            memory=False,
            max_rpm=40
        )

    @task
    def symptom_interview_task(self) -> Task:
        return self._symptom_interview_task

    @task
    def validation_task(self) -> Task:
        return self._validation_task

    @task
    def diagnosis_task(self) -> Task:
        return self._diagnosis_task

    @task
    def report_task(self) -> Task:
        return self._report_task

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew"""
        return Crew(
            agents=[
                self._communicator_agent,
                self._diagnosis_agent,
                self._search_agent,
                self._report_generator_agent,
                self._symptom_validator_agent,
            ],
            tasks=[
                self._symptom_interview_task,  # Initial interview
                self._validation_task,         # Validate initial information
                self._diagnosis_task,          # Create preliminary diagnosis
                self._report_task,             # Generate final report
            ],
            process=Process.sequential,  # Sequential execution ensures all tasks run
            verbose=True,
            memory=False,
            max_rpm=40
        )

