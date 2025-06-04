#!/usr/bin/env python3
"""
Test script for PDF generation functionality
This demonstrates the medical report generation without needing API calls
"""

from src.searchv2.tools.report_generation_tool import ReportGenerationTool

def test_pdf_generation():
    """Test the PDF generation with sample data"""
    
    # Create the tool instance
    pdf_tool = ReportGenerationTool()
    
    # Sample patient data
    sample_patient_info = {
        "name": "John Doe",
        "age": "35",
        "gender": "Male",
        "contact": "555-0123"
    }
    
    sample_chief_complaint = "Headache and dizziness for the past 3 days"
    
    sample_history = """
    Patient reports onset of headache 3 days ago, initially mild but progressively worsening.
    Describes headache as throbbing, primarily frontal and temporal regions.
    Associated with dizziness, especially when standing up quickly.
    No visual changes, nausea, or vomiting reported.
    Patient has been taking over-the-counter ibuprofen with minimal relief.
    """
    
    sample_symptoms = {
        "headache": {
            "onset": "3 days ago",
            "duration": "Continuous",
            "severity": "7/10, worsening",
            "location": "Frontal and temporal regions",
            "character": "Throbbing",
            "aggravating_factors": "Bright lights, noise",
            "relieving_factors": "Rest in dark room",
            "associated_symptoms": "Dizziness"
        },
        "dizziness": {
            "onset": "3 days ago",
            "duration": "Intermittent",
            "severity": "Moderate",
            "character": "Lightheadedness",
            "aggravating_factors": "Standing up quickly",
            "relieving_factors": "Sitting down",
            "associated_symptoms": "Headache"
        }
    }
    
    print("Generating medical report PDF...")
    
    # Generate the PDF
    result = pdf_tool._run(
        patient_info=sample_patient_info,
        chief_complaint=sample_chief_complaint,
        history_present_illness=sample_history,
        symptoms=sample_symptoms,
        patient_uuid="test-patient-123",
    )
    
    print(f"Result: {result}")


if __name__ == "__main__":
    test_pdf_generation()
