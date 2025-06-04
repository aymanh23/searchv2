from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from pathlib import Path
from typing import Dict, Optional

from .tools.human_input_tool import MessageBroker


@dataclass
class Session:
    broker: MessageBroker
    crew_thread: Optional[Thread] = None
    crew_process: Optional[object] = None
    log_file: Optional[Path] = None


class SessionManager:
    """Manage crew sessions and their resources."""

    _sessions: Dict[str, Session] = {}
    _lock: Lock = Lock()

    @classmethod
    def get_session(cls, session_id: str) -> Session:
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session is None:
                session = Session(broker=MessageBroker())
                cls._sessions[session_id] = session
            return session

    @classmethod
    def cleanup_session(cls, session_id: str) -> None:
        with cls._lock:
            session = cls._sessions.pop(session_id, None)
        if session and session.log_file and session.log_file.exists():
            try:
                session.log_file.unlink()
            except Exception:
                pass

