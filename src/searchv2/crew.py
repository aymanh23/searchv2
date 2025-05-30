from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from searchv2.tools.human_input_tool import HumanInputTool
from searchv2.tools.report_generation_tool import ReportGenerationTool
from crewai_tools import WebsiteSearchTool
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
                    # or google, openai, anthropic, llama2, ...
                    provider="google",
                    config=dict(
                        model="gemini-1.5-pro",
                        temperature=0.3,
                        max_tokens=1000,
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
            verbose=True
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            tools=[self.WebsiteSearchTool()],
            verbose=True
        )

    @agent  
    def report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['report_generator'],
            tools=[self.ReportGenerationTool()],
            verbose=True
        )

    @task
    def symptom_interview_task(self) -> Task:
        return Task(
            description="""
            Conduct a comprehensive symptom interview and generate a medical report.
            
            PROCESS:
            1. Welcome the patient and begin the symptom interview
            2. Use delegation to search_agent when you need follow-up questions about specific symptoms
            3. Continue gathering detailed symptom information until you have comprehensive data
            4. Once the interview is complete, delegate to report_generator to create a professional PDF report
            
            INTERVIEW COMPLETION CRITERIA:
            Stop the interview when you have gathered sufficient information about:
            - Onset, duration, severity, location, character
            - Aggravating and relieving factors  
            - Associated symptoms
            - Previous episodes and treatments attempted
            
            FINAL STEP: After completing the interview, delegate the report generation to report_generator with all collected information.
            """,
            expected_output="""
            A completed symptom interview with a generated medical report saved as PDF.
            The output should include:
            1. Summary of the interview process
            2. Confirmation that the PDF report was generated and saved
            3. The filename and location of the generated report
            """,
            agent=self.communicator(),
            human_input=True
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew"""
        return Crew(
            agents=[self.communicator(), self.search_agent(), self.report_generator()],
            tasks=[self.symptom_interview_task()],
            process=Process.sequential,
            verbose=True,
        )
