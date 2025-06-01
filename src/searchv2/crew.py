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
            llm="gemini/gemini-2.0-flash",
            memory=True
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            tools=[self.TrustedMedicalSearchTool(), self.SerperSearchTool(), self.WebsiteSearchTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-2.0-flash",
            memory=True
        )
    @agent
    def diagnosis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['diagnosis_agent'],
            verbose=True,
            allow_delegation=True,  # Can delegate to search_agent for research
            llm="gemini/gemini-2.0-flash",
            memory=True
        )
    @agent  
    def report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['report_generator'],
            tools=[self.ReportGenerationTool()],
            verbose=True,
            allow_delegation=False,  # Focused specialist
            llm="gemini/gemini-2.0-flash",
            memory=True
        )

    @agent
    def symptom_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['symptom_validator'],
            verbose=True,
            allow_delegation=True,  # Can delegate back to communicator
            llm="gemini/gemini-2.0-flash",
            memory=True
        )

    @task
    def symptom_interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['symptom_interview_task'],
            agent=self.communicator(),
            human_input=True,
            
        )

    @task
    def validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['validation_task'],
            agent=self.symptom_validator(),
            context=[self.symptom_interview_task()]  # Gets interview results as input
        )

    @task
    def report_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_task'],
            agent=self.report_generator(),
            context=[self.symptom_interview_task(), self.validation_task()]  # Gets both interview and validation results
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew"""
        return Crew(
            agents=[self.communicator(), self.search_agent(), self.report_generator(), self.symptom_validator()],
            tasks=[self.symptom_interview_task(), self.validation_task(), self.report_task()],  # Sequential tasks
            process=Process.sequential,  # Sequential execution ensures all tasks run
            verbose=True,
            memory=True
        )
