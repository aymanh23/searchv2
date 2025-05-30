#!/usr/bin/env python
import sys
import warnings
import traceback
import argparse
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the medical symptom interview system using CrewAI Flow.
    
    Options:
    - Flow mode: Using actual CrewAI Flow with state persistence (default)
    - Basic mode: Original crew without state persistence
    """
    try:
        parser = argparse.ArgumentParser(description="Medical Interview System")
        parser.add_argument(
            "--mode", 
            choices=["basic", "flow"], 
            default="flow",
            help="Choose interview mode: 'flow' for CrewAI Flow with state persistence (default), 'basic' for original crew"
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Start a fresh interview (ignore previous state)"
        )
        
        # Only parse args if they exist, otherwise use defaults
        if len(sys.argv) > 1:
            args = parser.parse_args()
        else:
            # Create default args when run without parameters
            class DefaultArgs:
                mode = "flow"
                fresh = False
            args = DefaultArgs()
            
    except:
        # Fallback to flow mode if argument parsing fails
        class DefaultArgs:
            mode = "flow"
            fresh = False
        args = DefaultArgs()
    
    print("🏥 Medical Interview System")
    print("=" * 50)
    
    if args.mode == "flow":
        print("🚀 Using CrewAI Flow (RECOMMENDED)")
        print("✅ Event-driven architecture")
        print("✅ Direct LLM calls for efficiency") 
        print("✅ Individual agents for specialized tasks")
        print("✅ Structured state management")
        print("✅ Works with Gemini")
        print("=" * 50)
        
        try:
            from searchv2.crew import run_medical_interview_flow
            
            # New function signature doesn't take parameters
            result = run_medical_interview_flow()
                
            print("\n🎉 CrewAI Flow completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Flow failed: {e}")
            print("\n💡 TIP: Check the error details above for troubleshooting.")
            
    else:  # basic mode
        print("🔧 Using Basic Mode")
        print("⚠️  No state persistence")
        print("⚠️  No error recovery")
        print("=" * 50)
        
        try:
            from searchv2.crew import MedicalSearch
            crew = MedicalSearch().crew()
            result = crew.kickoff()
            print("\n🎉 Medical interview completed!")
            
        except Exception as e:
            print(f"\n❌ Interview failed: {e}")
            print("\n⚠️  You'll need to start over from the beginning.")
            traceback.print_exc()

def train():
    """
    Train the crew for 'n' iterations.
    """
    try:
        from searchv2.crew import MedicalSearch
        crew = MedicalSearch().crew()
        
        print("🎯 Training the medical interview crew...")
        crew.train(n_iterations=int(sys.argv[1]) if len(sys.argv) > 1 else 3)
        print("✅ Training completed!")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        from searchv2.crew import MedicalSearch
        crew = MedicalSearch().crew()
        
        print("🔄 Replaying crew execution...")
        crew.replay(task_id=sys.argv[1] if len(sys.argv) > 1 else None)
        print("✅ Replay completed!")
        
    except Exception as e:
        print(f"❌ Replay failed: {e}")

def test():
    """
    Test the crew execution and get results.
    """
    try:
        from searchv2.crew import MedicalSearch
        crew = MedicalSearch().crew()
        
        print("🧪 Testing crew execution...")
        crew.test(n_iterations=int(sys.argv[1]) if len(sys.argv) > 1 else 3)
        print("✅ Testing completed!")
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")

if __name__ == "__main__":
    run()
