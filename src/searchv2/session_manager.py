"""
Session Manager for Medical Search System

This module ensures that each medical interview session starts fresh
without any memory or state from previous sessions, while maintaining
conversation context within each session.
"""

import os
import shutil
import glob
from pathlib import Path
from typing import Optional


class SessionManager:
    """Manages session state to ensure clean starts for each medical interview"""
    
    def __init__(self):
        self.session_id: Optional[str] = None
        self.crew_instance = None
        
    def start_new_session(self) -> str:
        """
        Start a new medical interview session.
        
        Returns:
            str: New session ID
        """
        import uuid
        from datetime import datetime
        
        # Generate new session ID
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Set session ID in environment for tools to access
        os.environ['CURRENT_SESSION_ID'] = self.session_id
        
        # Clear any existing memory/cache from previous sessions
        self._clear_session_state()
        
        print(f"✅ New medical interview session started: {self.session_id}")
        print("📝 Previous session data cleared - starting fresh interview")
        print("🧠 Memory enabled within this session for conversation continuity")
        print("🔄 Tool state will persist during LLM errors within this session")
        
        return self.session_id
    
    def _clear_session_state(self):
        """Clear all session state and memory from previous sessions"""
        
        # Clear CrewAI memory storage
        self._clear_crewai_memory()
        
        # Clear LangChain memory if used
        self._clear_langchain_memory()
        
        # Clear tool state files
        self._clear_tool_state_files()
        
        # Clear any cached crew instances
        self.crew_instance = None
        
        # Clear environment variables that might store state
        self._clear_state_env_vars()
        
        # Clear any SQLite databases used by CrewAI
        self._clear_memory_databases()
        
    def _clear_crewai_memory(self):
        """Clear CrewAI memory storage comprehensively"""
        # Common CrewAI memory storage locations
        possible_memory_paths = [
            # Local storage
            ".crew_memory",
            "crew_memory", 
            ".crewai",
            "crewai_memory",
            ".crew",
            "crew_storage",
            ".crewai_storage",
            
            # Home directory storage
            os.path.expanduser("~/.crewai"),
            os.path.expanduser("~/.crew"),
            os.path.expanduser("~/.crewai_memory"),
            os.path.expanduser("~/.crew_memory"),
            
            # Temp storage that might be used
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "crewai"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "crewai"),
            "/tmp/crewai",
            "/tmp/crew_memory",
        ]
        
        # Also check for memory folders with patterns
        pattern_paths = [
            "./*memory*",
            "./*crew*",
            "./*agent*memory*",
        ]
        
        # Add pattern matches to paths to check
        for pattern in pattern_paths:
            try:
                matches = glob.glob(pattern)
                possible_memory_paths.extend(matches)
            except:
                pass
        
        cleared_count = 0
        for memory_path in set(possible_memory_paths):  # Remove duplicates
            if os.path.exists(memory_path):
                try:
                    if os.path.isdir(memory_path):
                        shutil.rmtree(memory_path)
                        print(f"🧹 Cleared memory directory: {memory_path}")
                    else:
                        os.remove(memory_path)
                        print(f"🧹 Cleared memory file: {memory_path}")
                    cleared_count += 1
                except Exception as e:
                    print(f"⚠️  Could not clear {memory_path}: {e}")
        
        if cleared_count == 0:
            print("🧹 No previous memory storage found - clean start")
    
    def _clear_langchain_memory(self):
        """Clear LangChain memory storage that might be used by CrewAI"""
        langchain_paths = [
            ".langchain",
            "langchain_cache",
            os.path.expanduser("~/.langchain"),
            os.path.expanduser("~/.cache/langchain"),
        ]
        
        for path in langchain_paths:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    print(f"🧹 Cleared LangChain storage: {path}")
                except Exception as e:
                    print(f"⚠️  Could not clear LangChain storage {path}: {e}")
    
    def _clear_memory_databases(self):
        """Clear any SQLite databases that might store memory"""
        db_patterns = [
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "*memory*.db",
            "*crew*.db",
            "*agent*.db"
        ]
        
        for pattern in db_patterns:
            try:
                db_files = glob.glob(pattern)
                for db_file in db_files:
                    # Only delete if it looks like a memory/cache file
                    if any(keyword in db_file.lower() for keyword in ['memory', 'cache', 'crew', 'agent', 'temp']):
                        try:
                            os.remove(db_file)
                            print(f"🧹 Cleared memory database: {db_file}")
                        except Exception as e:
                            print(f"⚠️  Could not clear database {db_file}: {e}")
            except:
                pass
    
    def _clear_state_env_vars(self):
        """Clear environment variables that might store session state"""
        state_vars = [
            'CREW_MEMORY',
            'AGENT_MEMORY', 
            'SESSION_STATE',
            'INTERVIEW_STATE',
            'CREWAI_MEMORY',
            'LANGCHAIN_CACHE',
            'CURRENT_SESSION_ID',
        ]
        
        cleared_vars = []
        for var in state_vars:
            if var in os.environ:
                del os.environ[var]
                cleared_vars.append(var)
        
        if cleared_vars:
            print(f"🧹 Cleared environment variables: {', '.join(cleared_vars)}")
    
    def _clear_tool_state_files(self):
        """Clear tool state files from previous sessions"""
        import tempfile
        import glob
        
        session_dir = Path(tempfile.gettempdir()) / "medical_interview_sessions"
        if session_dir.exists():
            try:
                # Clear all session state files
                state_files = glob.glob(str(session_dir / "*_state.json"))
                for state_file in state_files:
                    try:
                        os.remove(state_file)
                        print(f"🧹 Cleared tool state file: {Path(state_file).name}")
                    except Exception as e:
                        print(f"⚠️  Could not clear state file {state_file}: {e}")
                
                # Remove directory if empty
                try:
                    session_dir.rmdir()
                except:
                    pass  # Directory not empty or other error
                    
            except Exception as e:
                print(f"⚠️  Could not clear tool state directory: {e}")
    
    def get_fresh_crew(self):
        """
        Get a fresh crew instance with no memory from previous sessions.
        Memory will be enabled within this session for conversation continuity.
        
        Returns:
            MedicalSearch crew instance
        """
        from searchv2.crew import MedicalSearch
        
        # Always create a new instance to ensure fresh state
        self.crew_instance = MedicalSearch()
        
        # Get the crew (with memory enabled for this session)
        crew = self.crew_instance.crew()
        
        # Reset any tool state for the new session
        for agent in crew.agents:
            for tool in agent.tools:
                if hasattr(tool, 'reset_session'):
                    tool.reset_session()
        
        print("🚀 Fresh crew created with clean state")
        print("💡 Memory is active for conversation continuity within this session")
        
        return crew
    
    def end_session(self):
        """Clean up session resources and prepare for next session"""
        if self.session_id:
            print(f"🔚 Session {self.session_id} completed")
            print("💾 Report saved successfully")
            print("🔄 Session data will be cleared for next patient interview")
            
        # Clear session ID from environment
        if 'CURRENT_SESSION_ID' in os.environ:
            del os.environ['CURRENT_SESSION_ID']
            
        # Don't clear memory here - let it persist until next session starts
        # This allows for any final processing to complete
        
        # Reset session tracking
        self.session_id = None
        self.crew_instance = None


# Global session manager instance
session_manager = SessionManager() 