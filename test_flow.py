#!/usr/bin/env python3
"""
Test script for the Medical Interview Flow
Demonstrates state persistence and error recovery
"""

import os
import sys
sys.path.append('src')

from searchv2.flow_crew import run_medical_interview

def main():
    """Test the medical interview flow"""
    
    print("🏥 Testing Medical Interview Flow")
    print("=" * 50)
    print()
    print("This Flow provides:")
    print("✅ Conversation state persistence")
    print("✅ Automatic retry with exponential backoff")
    print("✅ Resume from last successful point")
    print("✅ Professional PDF report generation")
    print()
    print("If API fails, conversation state is preserved!")
    print("=" * 50)
    print()
    
    try:
        result = run_medical_interview()
        print(f"\n🎉 Flow completed successfully!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"\n❌ Flow failed: {e}")
        print("\nNote: You can restart with the same state ID to resume!")

if __name__ == "__main__":
    main() 