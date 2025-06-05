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

logger = logging.getLogger(__name__)


def _patch_agent_run_with_retry(max_retries: int = 3, delay: float = 1.0,
                                fallback: str = "No response, please try again later."):
    """Wrap Agent.run to retry on empty responses."""
    if getattr(Agent, "_run_wrapped", False):
        return

    original_run = Agent.run

    def run_with_retry(self, *args, **kwargs):
        for attempt in range(1, max_retries + 1):
            result = original_run(self, *args, **kwargs)
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

        # Provide a clearer fallback for the communicator so that the user
        # is informed that the system is still working on a response.
        name = getattr(self, "name", "").lower()
        if "communicator" in name or "interviewer" in name:
            return "I'm having trouble responding, please wait a moment"
        return fallback

    Agent.run = run_with_retry
    Agent._run_wrapped = True


_patch_agent_run_with_retry()
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators


@CrewBase
class MedicalSearch():
    """MedicalSearch crew"""

    def __init__(self, broker: MessageBroker, conversation_log: Path, patient_uuid: str = ""):
        self._broker = broker
        self._conversation_log = conversation_log
        self._patient_uuid = patient_uuid

        # Instantiate agents once and reuse them
        self._communicator_agent = self.communicator()
        self._search_agent = self.search_agent()
        self._diagnosis_agent = self.diagnosis_agent()
        self._report_generator_agent = self.report_generator()
        self._symptom_validator_agent = self.symptom_validator()

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
                    # Back to Gemini with standard configuration
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
            allow_delegation=True,  # Enable delegation
            llm="gemini/gemini-2.0-flash-lite",
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
            llm="gemini/gemini-2.0-flash-lite",
            memory=False,
            max_rpm=40               
        )
    @agent
    def diagnosis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['diagnosis_agent'],
            verbose=True,
            allow_delegation=True,  # Can delegate to search_agent for research
            llm="gemini/gemini-2.0-flash-lite",
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
            llm="gemini/gemini-2.0-flash-lite",
            memory=False,
            max_rpm=40
        )

    @agent
    def symptom_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['symptom_validator'],
            verbose=True,
            allow_delegation=True,  # Can delegate back to communicator
            llm="gemini/gemini-2.0-flash-lite",
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

