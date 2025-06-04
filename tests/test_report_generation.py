import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add the src directory to Python path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.append(str(src_path))

from searchv2.session import SessionManager
from searchv2.tools.report_generation_tool import ReportGenerationTool
from searchv2.tools.human_input_tool import MessageBroker


def main(test_uuid: str):
    print("\n=== Testing Report Generation ===\n")
    print(f"Using UUID: {test_uuid}")

    try:
        # Create a new session
        print("\nStep 1: Creating session...")
        session = SessionManager.get_session(test_uuid)
        print("✓ Session created successfully")

        # Create the report generation tool
        print("\nStep 2: Creating report generation tool...")
        tool = ReportGenerationTool(patient_uuid=test_uuid)
        print("✓ Tool created successfully")

        # Test data
        print("\nStep 3: Preparing test data...")
        test_data = {
            "patient_info": {
                "age": "35",
                "gender": "Female",
                "medical_history": "No significant history"
            },
            "chief_complaint": "Persistent headache and fatigue",
            "history_present_illness": "Patient reports headache starting 3 days ago, accompanied by fatigue",
            "symptoms": {
                "headache": {
                    "severity": "moderate",
                    "duration": "3 days",
                    "location": "frontal region",
                    "character": "throbbing"
                },
                "fatigue": {
                    "severity": "mild",
                    "duration": "3 days",
                    "pattern": "constant"
                }
            },
            "diagnosis_assessment": "Preliminary assessment suggests tension headache with possible stress-related fatigue."
        }
        print("✓ Test data prepared")

        # Run the report generation
        print("\nStep 4: Generating report...")
        result = tool._run(**test_data)
        print("✓ Report generation completed")
        
        print("\nReport generation result:")
        print("-" * 50)
        print(result)
        print("-" * 50)

        # Check if report file exists
        if "medical_report_" in result and ".pdf" in result:
            report_path = result.split("Location: ")[1].split("\n")[0]
            if Path(report_path).exists():
                print("\n✓ Report file successfully created at:")
                print(report_path)
            else:
                print("\n✗ Error: Report file not found at expected location")

        # Check Firebase upload
        if "Uploaded to Firebase Storage at:" in result:
            storage_path = result.split("Uploaded to Firebase Storage at: ")[1]
            print("\n✓ Report uploaded to Firebase at:")
            print(storage_path)

        print("\n=== Test completed successfully! ===")

    except Exception as e:
        print(f"\n✗ Error occurred during testing:")
        print(f"  {str(e)}")
        raise

    finally:
        # Cleanup
        print("\nCleaning up...")
        SessionManager.cleanup_session(test_uuid)
        print("✓ Session cleaned up")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test report generation with a specific UUID')
    parser.add_argument('uuid', type=str, help='The UUID or string identifier to use for testing')
    args = parser.parse_args()
    main(args.uuid)