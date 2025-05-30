from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from searchv2.tools.human_input_tool import HumanInputTool
from searchv2.tools.report_generation_tool import ReportGenerationTool
from crewai_tools import WebsiteSearchTool
from datetime import datetime
import json

# Define the Flow State using Pydantic
class MedicalInterviewState(BaseModel):
    # Patient information
    chief_complaint: str = ""
    current_question: str = ""
    
    # Symptom details collected
    symptom_onset: str = ""
    symptom_duration: str = ""
    symptom_severity: str = ""
    symptom_location: str = ""
    symptom_character: str = ""
    aggravating_factors: str = ""
    relieving_factors: str = ""
    associated_symptoms: str = ""
    previous_episodes: str = ""
    treatments_tried: str = ""
    
    # Conversation tracking
    conversation_history: List[Dict[str, str]] = []
    questions_asked: int = 0
    max_questions: int = 10
    
    # Interview status
    interview_complete: bool = False
    report_generated: bool = False
    
    # Step tracking
    current_step: str = "start"

@CrewBase
class MedicalSearch():
    """MedicalSearch crew - keeping existing agents/tasks for when needed"""

    @tool
    def WebsiteSearchTool(self):
        from crewai_tools import WebsiteSearchTool
        return WebsiteSearchTool(
            config=dict(
                llm=dict(
                    provider="google",
                    config=dict(
                        model="gemini-2.0-flash-exp",
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
            llm=LLM(model="gemini/gemini-2.0-flash-exp")
        )

    @agent
    def search_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['search_agent'],
            tools=[self.WebsiteSearchTool()],
            verbose=True,
            llm=LLM(model="gemini/gemini-2.0-flash-exp")
        )

    @agent  
    def report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['report_generator'],
            tools=[self.ReportGenerationTool()],
            verbose=True,
            llm=LLM(model="gemini/gemini-2.0-flash-exp")
        )

    @agent
    def symptom_validator(self) -> Agent:
        return Agent(
            config=self.agents_config['symptom_validator'],
            verbose=True,
            llm=LLM(model="gemini/gemini-2.0-flash-exp")
        )

    @task
    def symptom_interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['symptom_interview_task'],
            agent=self.communicator()
        )

    @task
    def search_task(self) -> Task:
        return Task(
            config=self.tasks_config['search_task'],
            agent=self.search_agent()
        )

    @task
    def validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['validation_task'],
            agent=self.symptom_validator(),
            context=[self.symptom_interview_task()]
        )

    @task
    def report_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_generation_task'],
            agent=self.report_generator(),
            context=[self.validation_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MedicalSearch crew for complex collaborative tasks"""
        return Crew(
            agents=[self.communicator(), self.search_agent(), self.report_generator(), self.symptom_validator()],
            tasks=[self.symptom_interview_task(), self.search_task(), self.validation_task(), self.report_generation_task()],
            process=Process.sequential,
            verbose=True,
        )

# Proper CrewAI Flow Implementation
class MedicalInterviewFlow(Flow[MedicalInterviewState]):
    """
    Medical Interview Flow using proper CrewAI Flow patterns
    - Direct LLM calls for simple questions
    - Individual agents for specialized tasks  
    - Event-driven architecture
    """
    
    def __init__(self):
        super().__init__()
        self.medical_search = MedicalSearch()
        # Initialize direct LLM for simple tasks - fix model name
        self.llm = LLM(model="gemini/gemini-2.0-flash-exp", temperature=0.3)
    
    @start()
    def start_interview(self):
        """Start the medical interview with chief complaint"""
        print("🏥 Starting Medical Interview Flow")
        print("=" * 50)
        
        # Use the communicator agent for initial human input
        communicator = self.medical_search.communicator()
        
        # Ask for chief complaint
        try:
            question = "Hello! I'm your medical assistant. What symptoms are you experiencing today?"
            response = communicator.tools[0]._run(question=question)
            
            self.state.chief_complaint = response
            self.state.conversation_history.append({"question": question, "answer": response})
            self.state.questions_asked += 1
            self.state.current_step = "chief_complaint_received"
            
            print(f"Chief Complaint: {response}")
            return "chief_complaint_received"
            
        except Exception as e:
            print(f"Error getting chief complaint: {e}")
            return "error"

    @listen(start_interview)
    def determine_next_question(self, previous_result):
        """Use direct LLM call to determine what question to ask next"""
        
        if previous_result == "error":
            return "interview_failed"
            
        if self.state.questions_asked >= self.state.max_questions:
            return "max_questions_reached"
        
        print("🤔 Determining next question...")
        
        # Create context for LLM
        context = f"""
        Chief Complaint: {self.state.chief_complaint}
        
        Information Already Collected:
        - Onset: {self.state.symptom_onset or 'Not collected'}
        - Duration: {self.state.symptom_duration or 'Not collected'}  
        - Severity: {self.state.symptom_severity or 'Not collected'}
        - Location: {self.state.symptom_location or 'Not collected'}
        - Character: {self.state.symptom_character or 'Not collected'}
        - Aggravating factors: {self.state.aggravating_factors or 'Not collected'}
        - Relieving factors: {self.state.relieving_factors or 'Not collected'}
        - Associated symptoms: {self.state.associated_symptoms or 'Not collected'}
        - Previous episodes: {self.state.previous_episodes or 'Not collected'}
        - Treatments tried: {self.state.treatments_tried or 'Not collected'}
        
        Conversation History:
        {json.dumps(self.state.conversation_history, indent=2)}
        
        Based on the missing information, determine the MOST IMPORTANT single question to ask next.
        Return ONLY the question text, nothing else.
        
        If all critical information is collected, return "COMPLETE".
        """
        
        try:
            messages = [
                {"role": "system", "content": "You are a medical interviewer. Ask one focused question at a time to gather complete symptom information."},
                {"role": "user", "content": context}
            ]
            
            response = self.llm.call(messages=messages)
            
            if "COMPLETE" in response.upper():
                return "interview_complete"
            else:
                self.state.current_question = response.strip()
                print(f"Next question: {self.state.current_question}")
                # Directly call ask_next_question instead of returning event
                return self.ask_next_question()
                
        except Exception as e:
            print(f"Error determining next question: {e}")
            return "interview_complete"  # Fallback to complete if error

    def ask_next_question(self):
        """Ask the determined question using the communicator agent"""
        print(f"❓ Asking: {self.state.current_question}")
        
        try:
            communicator = self.medical_search.communicator()
            response = communicator.tools[0]._run(question=self.state.current_question)
            
            # Store the response in appropriate field based on question content
            self._categorize_and_store_response(self.state.current_question, response)
            
            # Add to conversation history
            self.state.conversation_history.append({
                "question": self.state.current_question, 
                "answer": response
            })
            self.state.questions_asked += 1
            
            print(f"Response: {response}")
            
            # Continue the loop by calling determine_next_question again
            return self.determine_next_question("continue")
            
        except Exception as e:
            print(f"Error asking question: {e}")
            return "interview_complete"

    @listen(determine_next_question)
    def handle_interview_completion(self, result):
        """Handle when interview is complete or max questions reached"""
        if result == "interview_complete":
            return self.validate_completeness()
        elif result == "max_questions_reached":
            print("⚠️ Maximum questions reached, proceeding to validation...")
            return self.validate_completeness()
        else:
            # If result is not completion, then determine_next_question handled the loop
            return result

    def validate_completeness(self):
        """Use individual validator agent to check completeness"""
        print("✅ Validating interview completeness...")
        
        try:
            validator = self.medical_search.symptom_validator()
            
            # Create validation prompt
            validation_context = f"""
            Validate the completeness of this medical interview:
            
            Chief Complaint: {self.state.chief_complaint}
            Onset: {self.state.symptom_onset}
            Duration: {self.state.symptom_duration}
            Severity: {self.state.symptom_severity}
            Location: {self.state.symptom_location}
            Character: {self.state.symptom_character}
            Aggravating factors: {self.state.aggravating_factors}
            Relieving factors: {self.state.relieving_factors}
            Associated symptoms: {self.state.associated_symptoms}
            Previous episodes: {self.state.previous_episodes}
            Treatments tried: {self.state.treatments_tried}
            
            Questions asked: {self.state.questions_asked}
            
            Return "COMPLETE" if sufficient information gathered, or "INCOMPLETE" if critical information missing.
            """
            
            # Execute validation
            validation_task = Task(
                description=validation_context,
                expected_output="COMPLETE or INCOMPLETE assessment",
                agent=validator
            )
            
            result = validator.execute_task(validation_task)
            result_text = str(result).upper()
            
            if "COMPLETE" in result_text and "INCOMPLETE" not in result_text:
                self.state.interview_complete = True
                print("✅ Validation: Interview is COMPLETE!")
                return self.generate_medical_report()
            else:
                print("❌ Validation: Interview is INCOMPLETE")
                if self.state.questions_asked >= self.state.max_questions:
                    print("⚠️ Max questions reached but interview incomplete. Generating report with available data...")
                    self.state.interview_complete = True
                    return self.generate_medical_report()
                else:
                    print("🔄 Continuing to ask more questions...")
                    # Continue asking questions
                    return self.determine_next_question("continue_after_validation")
                
        except Exception as e:
            print(f"Validation error: {e}")
            print("⚠️ Proceeding to report generation due to validation error...")
            self.state.interview_complete = True
            return self.generate_medical_report()

    def generate_medical_report(self):
        """Generate final medical report using the report generator agent"""
        print("📄 Generating medical report...")
        
        try:
            report_generator = self.medical_search.report_generator()
            
            # Create a comprehensive prompt for the report generator to interpret raw responses
            report_prompt = f"""
            Generate a professional medical report based on the following patient interview data. 
            
            IMPORTANT: Do not copy the patient's exact words. Instead, interpret their responses 
            and write them in proper medical terminology and professional language.
            
            PATIENT INTERVIEW DATA:
            Chief Complaint: {self.state.chief_complaint}
            
            SYMPTOM DETAILS:
            - Onset: {self.state.symptom_onset}
            - Duration: {self.state.symptom_duration}
            - Severity: {self.state.symptom_severity}
            - Location: {self.state.symptom_location}
            - Character: {self.state.symptom_character}
            - Aggravating factors: {self.state.aggravating_factors}
            - Relieving factors: {self.state.relieving_factors}
            - Associated symptoms: {self.state.associated_symptoms}
            - Previous episodes: {self.state.previous_episodes}
            - Treatments tried: {self.state.treatments_tried}
            
            CONVERSATION HISTORY:
            {json.dumps(self.state.conversation_history, indent=2)}
            
            Please generate a professional medical report that:
            1. Interprets casual patient language into medical terminology
            2. Organizes information into proper medical report sections
            3. Uses professional medical language throughout
            4. Provides clinical assessment and recommendations
            
            Format the report professionally with appropriate medical sections.
            """
            
            # Create a task for the report generator to interpret the data properly
            report_task = Task(
                description=report_prompt,
                expected_output="Professional medical report with proper medical terminology and clinical assessment",
                agent=report_generator
            )
            
            # Execute the report generation task
            interpreted_report = report_generator.execute_task(report_task)
            
            # Also generate the PDF with the interpreted data
            processed_symptoms = {
                "onset": self._interpret_medical_response(self.state.symptom_onset, "onset"),
                "duration": self._interpret_medical_response(self.state.symptom_duration, "duration"),
                "severity": self._interpret_medical_response(self.state.symptom_severity, "severity"),
                "location": self._interpret_medical_response(self.state.symptom_location, "location"),
                "character": self._interpret_medical_response(self.state.symptom_character, "character"),
                "aggravating_factors": self._interpret_medical_response(self.state.aggravating_factors, "aggravating"),
                "relieving_factors": self._interpret_medical_response(self.state.relieving_factors, "relieving"),
                "associated_symptoms": self._interpret_medical_response(self.state.associated_symptoms, "associated"),
                "previous_episodes": self._interpret_medical_response(self.state.previous_episodes, "previous"),
                "treatments_tried": self._interpret_medical_response(self.state.treatments_tried, "treatments")
            }
            
            report_data = {
                "patient_info": {},
                "chief_complaint": self.state.chief_complaint,
                "symptoms": processed_symptoms,
                "conversation_history": self.state.conversation_history,
                "clinical_interpretation": str(interpreted_report)
            }
            
            # Generate PDF report
            pdf_result = report_generator.tools[0]._run(**report_data)
            self.state.report_generated = True
            
            print("✅ Medical report generated successfully!")
            print(f"Clinical Report:\n{interpreted_report}")
            print(f"PDF Report: {pdf_result}")
            
            return f"Medical interview completed successfully!\n\nClinical Assessment:\n{interpreted_report}\n\nPDF Report: {pdf_result}"
            
        except Exception as e:
            print(f"❌ Report generation error: {e}")
            return f"Interview completed but report generation failed: {e}"

    def _interpret_medical_response(self, response: str, category: str) -> str:
        """Helper method to interpret casual patient responses into medical terminology"""
        if not response or response.strip() == "":
            return "Not provided"
        
        response_lower = response.lower().strip()
        
        # Interpret based on category and common patient expressions
        if category == "severity":
            if any(word in response_lower for word in ["8", "9", "10", "severe", "terrible", "worst"]):
                return "Severe (8-10/10)"
            elif any(word in response_lower for word in ["6", "7", "moderate", "bad"]):
                return "Moderate (6-7/10)"
            elif any(word in response_lower for word in ["1", "2", "3", "4", "5", "mild", "little"]):
                return "Mild (1-5/10)"
            else:
                return f"Patient-reported: {response}"
        
        elif category == "location":
            if "head" in response_lower:
                return "Cephalic (head region)"
            elif "back" in response_lower:
                return "Dorsal/lumbar region"
            elif "chest" in response_lower:
                return "Thoracic region"
            else:
                return f"Patient localizes to: {response}"
        
        elif category == "character":
            if any(word in response_lower for word in ["sharp", "stabbing", "knife"]):
                return "Sharp, stabbing quality"
            elif any(word in response_lower for word in ["throbbing", "pulsing", "beating"]):
                return "Throbbing, pulsatile quality"
            elif any(word in response_lower for word in ["burning", "fire", "flame"]):
                return "Burning sensation"
            elif any(word in response_lower for word in ["dull", "aching"]):
                return "Dull, aching quality"
            else:
                return f"Patient describes as: {response}"
        
        elif category == "aggravating":
            if any(word in response_lower for word in ["movement", "moving", "get up", "stand"]):
                return "Exacerbated by movement/position changes"
            elif any(word in response_lower for word in ["light", "bright"]):
                return "Photophobia (light sensitivity)"
            elif any(word in response_lower for word in ["noise", "sound"]):
                return "Phonophobia (sound sensitivity)"
            else:
                return f"Aggravated by: {response}"
        
        elif category == "relieving":
            if any(word in response_lower for word in ["nothing", "none", "no"]):
                return "No relieving factors identified"
            elif any(word in response_lower for word in ["rest", "lying", "sleep"]):
                return "Improved with rest/recumbent position"
            elif any(word in response_lower for word in ["medication", "pills", "medicine"]):
                return "Responsive to medication"
            else:
                return f"Relieved by: {response}"
        
        elif category == "associated":
            if any(word in response_lower for word in ["none", "no", "nothing"]):
                return "No associated symptoms reported"
            else:
                return f"Associated symptoms: {response}"
        
        elif category == "previous":
            if any(word in response_lower for word in ["no", "never", "none"]):
                return "No previous episodes reported"
            elif any(word in response_lower for word in ["yes", "before", "previous"]):
                return "Previous similar episodes reported"
            else:
                return f"Previous episodes: {response}"
        
        # Default: return cleaned up version
        return response if len(response) > 2 else "Not specified"

    def _categorize_and_store_response(self, question: str, response: str):
        """Helper method to categorize and store responses in appropriate fields"""
        question_lower = question.lower()
        
        if "when" in question_lower or "start" in question_lower or "began" in question_lower:
            self.state.symptom_onset = response
        elif "how long" in question_lower or "duration" in question_lower:
            self.state.symptom_duration = response
        elif "severe" in question_lower or "scale" in question_lower or "pain" in question_lower and ("rate" in question_lower or "1" in question_lower):
            self.state.symptom_severity = response
        elif "where" in question_lower or "location" in question_lower or "point" in question_lower:
            self.state.symptom_location = response
        elif "describe" in question_lower or "feel" in question_lower or "type" in question_lower:
            self.state.symptom_character = response
        elif "worse" in question_lower or "aggravat" in question_lower or "trigger" in question_lower:
            self.state.aggravating_factors = response
        elif "better" in question_lower or "reliev" in question_lower or "help" in question_lower:
            self.state.relieving_factors = response
        elif "other symptoms" in question_lower or "associated" in question_lower or "along with" in question_lower:
            self.state.associated_symptoms = response
        elif "before" in question_lower or "previous" in question_lower or "happened" in question_lower:
            self.state.previous_episodes = response
        elif "treatment" in question_lower or "tried" in question_lower or "medication" in question_lower:
            self.state.treatments_tried = response

# Function to run the proper CrewAI Flow
def run_medical_interview_flow():
    """
    Run the medical interview using proper CrewAI Flow patterns
    """
    try:
        print("🚀 Starting Proper Medical Interview Flow")
        print("=" * 50)
        
        # Create and run the flow
        flow = MedicalInterviewFlow()
        result = flow.kickoff()
        
        print("\n🎉 Medical Interview Flow completed!")
        print(f"Final result: {result}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Flow failed: {e}")
        raise e

# Legacy functions for compatibility
def run_medical_interview_with_persistence(resume: bool = True):
    """Legacy function - now redirects to proper flow"""
    return run_medical_interview_flow()
