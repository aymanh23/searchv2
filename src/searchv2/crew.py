from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from searchv2.tools.human_input_tool import HumanInputTool
from searchv2.tools.report_generation_tool import ReportGenerationTool
from searchv2.tools.serper_tool import SerperSearchTool
from searchv2.tools.trusted_medical_search_tool import TrustedMedicalSearchTool
from crewai_tools import WebsiteSearchTool
import os
from pathlib import Path
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators


@CrewBase
class MedicalSearch():
    """MedicalSearch crew"""

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
        return HumanInputTool()

    @tool
    def ReportGenerationTool(self):
        return ReportGenerationTool()

    @agent
    def communicator(self) -> Agent:
        return Agent(
            config=self.agents_config['communicator'],
            tools=[self.HumanInputTool()],
            verbose=True,
            allow_delegation=True,  # Enable delegation
            llm="gemini/gemini-2.0-flash-lite",
            memory=True,
            max_rpm=4
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            tools=[self.TrustedMedicalSearchTool(), self.SerperSearchTool(), self.WebsiteSearchTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-2.0-flash-lite",
            memory=True,
            max_rpm=4               
        )
    @agent
    def diagnosis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['diagnosis_agent'],
            verbose=True,
            allow_delegation=True,  # Can delegate to search_agent for research
            llm="gemini/gemini-2.0-flash-lite",
            memory=True,
            max_rpm=4       
        )
    @agent  
    def report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['report_generator'],
            tools=[self.ReportGenerationTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-2.0-flash-lite",
            memory=True,
            max_rpm=4
        )

    @agent
    def symptom_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['symptom_validator'],
            verbose=True,
            allow_delegation=True,  # Can delegate back to communicator
            llm="gemini/gemini-2.0-flash-lite",
            memory=True,
            max_rpm=4
        )

    @task
    def symptom_interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['symptom_interview_task'],
            agent=self.communicator(),
            human_input=True,
            max_rpm=4,
            context=[]  # Initial task has no context
        )

    @task
    def validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['validation_task'],
            agent=self.symptom_validator(),
            context=[self.symptom_interview_task()],  # Gets interview results as input
            max_rpm=4
        )

    @task
    def diagnosis_task(self) -> Task:
        return Task(
            config=self.tasks_config['diagnosis_task'],
            agent=self.diagnosis_agent(),
            context=[self.symptom_interview_task(), self.validation_task()],  # Gets both interview and validation results
            max_rpm=4
        )

    @task
    def follow_up_task(self) -> Task:
        return Task(
            config=self.tasks_config['symptom_interview_task'],  # Reuse the same config but with different context
            agent=self.communicator(),
            human_input=True,
            context=[self.symptom_interview_task(), self.validation_task(), self.diagnosis_task()],  # Gets all previous results
            max_rpm=4
        )

    @task
    def report_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_task'],
            agent=self.report_generator(),
            context=[self.symptom_interview_task(), self.validation_task(), self.diagnosis_task(), self.follow_up_task()],  # Gets all results including follow-up
            max_rpm=4
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew"""
        # Set up conversation log for HumanInputTool
        storage_dir = Path(os.environ.get("CREWAI_STORAGE_DIR", "crewai_storage"))
        conversation_log = storage_dir / "human_interaction.log"
        HumanInputTool.set_conversation_log(conversation_log)

        return Crew(
            agents=[self.communicator(), self.search_agent(), self.report_generator(), self.symptom_validator()],
            tasks=[
                self.symptom_interview_task(),  # Initial interview
                self.validation_task(),         # Validate initial information
                self.diagnosis_task(),          # Create preliminary diagnosis
                self.follow_up_task(),          # Get additional details based on diagnosis
                self.report_task()              # Generate final report
            ],
            process=Process.sequential,  # Sequential execution ensures all tasks run
            verbose=True,
            memory=True,
            max_rpm=4
        )