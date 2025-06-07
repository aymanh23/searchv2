"""
Medical Report Generation Tool

This tool generates professional medical reports in PDF format based on symptom information
collected during patient interviews. Reports are saved in the reports folder.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from searchv2 import firebase_utils
from searchv2.session import SessionManager


class ReportGenerationToolInput(BaseModel):
    """Input schema for ReportGenerationTool."""
    patient_info: Optional[Dict[str, Any]] = Field(None, description="Patient demographics and information")
    chief_complaint: str = Field("", description="Main symptoms reported by the patient")
    history_present_illness: str = Field("", description="Detailed symptom timeline and progression")
    symptoms: Optional[Dict[str, Any]] = Field(None, description="Dictionary of organized symptom information")
    diagnosis_assessment: str = Field("", description="Preliminary diagnostic assessment from diagnosis agent")


class ReportGenerationTool(BaseTool):
    name: str = "Medical Report Generator"
    description: str = (
        "Generates comprehensive medical reports in PDF format. "
        "Input should include patient symptoms, timeline, severity, and other clinical details. "
        "Reports are automatically saved in the reports folder with timestamp."
    )
    args_schema: Type[BaseModel] = ReportGenerationToolInput

    def __init__(self, patient_uuid: str = ""):
        super().__init__()
        # Store the UUID to help find the correct session later
        self._initial_uuid = patient_uuid
    
    def _format_diagnosis_assessment(self, diagnosis_text: str, styles) -> list:
        """Format diagnosis assessment text for better readability"""
        formatted_elements = []
        
        # Clean up the text and split into sections
        text = diagnosis_text.strip()
        
        # Split by common section markers
        sections = []
        current_section = ""
        
        # Split by asterisks (common LLM formatting)
        parts = text.split('**')
        for i, part in enumerate(parts):
            if i % 2 == 1:  # This is a header (between **)
                if current_section.strip():
                    sections.append(current_section.strip())
                    current_section = ""
                # Add the header
                formatted_elements.append(Paragraph(f"<b>{part.strip()}</b>", styles['Heading4']))
            else:
                current_section += part
        
        # Add the last section
        if current_section.strip():
            sections.append(current_section.strip())
        
        # If no ** sections found, try to split by numbered points
        if len(sections) <= 1:
            sections = []
            # Split by numbered points (1., 2., 3., etc.)
            import re
            numbered_parts = re.split(r'(\d+\.)', text)
            current_text = ""
            
            for part in numbered_parts:
                if re.match(r'\d+\.', part):  # This is a number
                    if current_text.strip():
                        sections.append(current_text.strip())
                        current_text = ""
                    current_text = part + " "
                else:
                    current_text += part
            
            if current_text.strip():
                sections.append(current_text.strip())
        
        # If still no clear sections, split by sentences for better readability
        if len(sections) <= 1:
            sentences = text.split('. ')
            sections = []
            current_paragraph = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    if len(current_paragraph) + len(sentence) > 200:  # Start new paragraph
                        if current_paragraph:
                            sections.append(current_paragraph.strip() + '.')
                        current_paragraph = sentence
                    else:
                        if current_paragraph:
                            current_paragraph += ". " + sentence
                        else:
                            current_paragraph = sentence
            
            if current_paragraph:
                sections.append(current_paragraph.strip())
        
        # Format each section as a paragraph with proper spacing
        for section in sections:
            if section.strip():
                # Add bullet point if it doesn't start with a number
                if not re.match(r'^\d+\.', section.strip()):
                    formatted_elements.append(Paragraph(f"• {section.strip()}", styles['Normal']))
                else:
                    formatted_elements.append(Paragraph(section.strip(), styles['Normal']))
                formatted_elements.append(Spacer(1, 6))  # Add small space between sections
        
        return formatted_elements

    def _run(self,
             patient_info: Optional[Dict[str, Any]] = None,
             chief_complaint: str = "",
             history_present_illness: str = "",
             symptoms: Dict[str, Any] = None,
             diagnosis_assessment: str = "",
             **kwargs) -> str:
        """
        Generate a medical report PDF
        
        Args:
            patient_info: Patient demographics if available
            chief_complaint: Main symptoms reported
            history_present_illness: Detailed symptom timeline
            symptoms: Dictionary of organized symptom information
            diagnosis_assessment: Preliminary diagnostic assessment from diagnosis agent
            **kwargs: Additional information for the report
        """
        try:
            # Get the session from SessionManager using our initial UUID
            if not self._initial_uuid:
                raise ValueError("No patient UUID available - required for report generation")
            
            # Get the session - this will return the existing session since we're in the same conversation
            session = SessionManager.get_session(self._initial_uuid)
            if not session:
                raise ValueError("Could not find active session for report generation")
                
            # Create reports directory if it doesn't exist
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chief_short = chief_complaint.replace(" ", "_").replace(",", "")[:30] if chief_complaint else "symptom_report"
            filename = f"medical_report_{timestamp}_{chief_short}.pdf"
            filepath = reports_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build the story (content)
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=12,
                textColor=colors.darkblue,
                borderWidth=1,
                borderColor=colors.darkblue,
                borderPadding=5
            )
            
            # Title
            story.append(Paragraph("MEDICAL SYMPTOM REPORT", title_style))
            story.append(Spacer(1, 20))
            
            # Report Information
            report_info_data = [
                ["Report Generated:", datetime.now().strftime("%B %d, %Y at %I:%M %p")],
                ["Report Type:", "Symptom Assessment"],
                ["Source:", "AI-Assisted Patient Interview"]
            ]
            
            report_info_table = Table(report_info_data, colWidths=[2*inch, 4*inch])
            report_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(report_info_table)
            story.append(Spacer(1, 20))
            
            # Patient Information (if available)
            if patient_info:
                story.append(Paragraph("1. PATIENT INFORMATION", header_style))
                
                patient_data = []
                for key, value in patient_info.items():
                    if value:
                        patient_data.append([f"{key.replace('_', ' ').title()}:", str(value)])
                
                if patient_data:
                    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
                    patient_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(patient_table)
                else:
                    story.append(Paragraph("Patient information not provided.", styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Chief Complaint
            story.append(Paragraph("2. CHIEF COMPLAINT", header_style))
            if chief_complaint:
                story.append(Paragraph(chief_complaint, styles['Normal']))
            else:
                story.append(Paragraph("No chief complaint recorded.", styles['Normal']))
            story.append(Spacer(1, 12))
            
            # History of Present Illness
            story.append(Paragraph("3. HISTORY OF PRESENT ILLNESS", header_style))
            if history_present_illness:
                story.append(Paragraph(history_present_illness, styles['Normal']))
            else:
                story.append(Paragraph("No detailed history recorded.", styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Symptom Details
            if symptoms:
                story.append(Paragraph("4. DETAILED SYMPTOM REVIEW", header_style))
                
                for symptom_name, symptom_details in symptoms.items():
                    story.append(Paragraph(f"<b>{symptom_name.title()}</b>", styles['Heading3']))
                    
                    if isinstance(symptom_details, dict):
                        symptom_data = []
                        for detail, value in symptom_details.items():
                            if value:
                                symptom_data.append([f"{detail.replace('_', ' ').title()}:", str(value)])
                        
                        if symptom_data:
                            symptom_table = Table(symptom_data, colWidths=[2*inch, 4*inch])
                            symptom_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ]))
                            story.append(symptom_table)
                    else:
                        story.append(Paragraph(str(symptom_details), styles['Normal']))
                    
                    story.append(Spacer(1, 8))
            
            # Preliminary Diagnostic Assessment
            story.append(Paragraph("5. PRELIMINARY DIAGNOSTIC ASSESSMENT", header_style))
            if diagnosis_assessment:
                # Format the diagnosis assessment for better readability
                formatted_diagnosis = self._format_diagnosis_assessment(diagnosis_assessment, styles)
                story.extend(formatted_diagnosis)
            else:
                story.append(Paragraph("No diagnostic assessment available.", styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Clinical Summary
            story.append(Paragraph("6. CLINICAL SUMMARY", header_style))
            summary_points = []
            
            if chief_complaint:
                summary_points.append(f"• Primary complaint: {chief_complaint}")
            
            if symptoms:
                symptom_count = len(symptoms)
                summary_points.append(f"• Number of symptoms assessed: {symptom_count}")
                
                # Identify any concerning patterns
                severity_levels = []
                for symptom_details in symptoms.values():
                    if isinstance(symptom_details, dict) and 'severity' in symptom_details:
                        severity_levels.append(symptom_details['severity'])
                
                if severity_levels:
                    summary_points.append(f"• Severity levels reported: {', '.join(set(severity_levels))}")
            
            if summary_points:
                for point in summary_points:
                    story.append(Paragraph(point, styles['Normal']))
            else:
                story.append(Paragraph("Limited clinical information available for summary.", styles['Normal']))
            
            story.append(Spacer(1, 12))
            
            # Recommendations
            story.append(Paragraph("7. RECOMMENDATIONS FOR FURTHER EVALUATION", header_style))
            
            recommendations = [
                "• Complete physical examination by qualified healthcare provider",
                "• Detailed medical history review",
                "• Consider relevant diagnostic tests based on clinical presentation",
                "• Follow-up as clinically indicated",
                "• Patient should seek immediate medical attention if symptoms worsen"
            ]
            
            for rec in recommendations:
                story.append(Paragraph(rec, styles['Normal']))
            
            story.append(Spacer(1, 12))
            
            # Important Notes
            story.append(Paragraph("8. IMPORTANT NOTES", header_style))
            
            notes = [
                "• This report is generated from an AI-assisted patient interview",
                "• Information should be verified during clinical examination",
                "• This report does not constitute medical diagnosis or treatment",
                "• Healthcare provider discretion is essential for patient care decisions"
            ]
            
            for note in notes:
                story.append(Paragraph(note, styles['Normal']))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(Paragraph("End of Report", 
                                  ParagraphStyle('Footer', 
                                               parent=styles['Normal'],
                                               alignment=TA_CENTER,
                                               textColor=colors.grey)))
            
            # Build PDF
            doc.build(story)

            storage_info = ""
            if self._initial_uuid:
                storage_path = firebase_utils.upload_report(filepath, self._initial_uuid)
                firebase_utils.log_report(self._initial_uuid, storage_path, filename)
                storage_info = f"\nUploaded to Firebase Storage at: {storage_path}"

            return (
                f"Medical report successfully generated and saved as: {filename}\n"
                f"Location: {filepath.absolute()}" + storage_info
            )
            
        except Exception as e:
            return f"Error generating medical report: {str(e)}"