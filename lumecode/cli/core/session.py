"""
Session Management for Lumecode
Save, load, and manage conversation sessions
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import uuid


@dataclass
class Message:
    """Single message in conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


@dataclass
class Session:
    """Conversation session."""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create_new(cls, name: str = "Untitled Session") -> 'Session':
        """Create new session."""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4())[:8],
            name=name,
            created_at=now,
            updated_at=now
        )
    
    def add_message(self, role: str, content: str, **metadata):
        """Add message to session."""
        msg = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get recent messages."""
        return self.messages[-count:]
    
    def get_context_summary(self) -> str:
        """Get summary of session context."""
        lines = [
            f"Session: {self.name}",
            f"ID: {self.id}",
            f"Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Messages: {len(self.messages)}",
        ]
        
        if self.context:
            lines.append(f"Context items: {len(self.context)}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'messages': [msg.to_dict() for msg in self.messages],
            'context': self.context,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            messages=[Message.from_dict(m) for m in data.get('messages', [])],
            context=data.get('context', {}),
            metadata=data.get('metadata', {})
        )


class SessionManager:
    """Manage session persistence."""
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or (Path.home() / '.lumecode' / 'sessions')
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, session: Session) -> Path:
        """Save session to disk."""
        session.updated_at = datetime.now()
        
        session_file = self.sessions_dir / f"{session.id}.json"
        
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
        
        return session_file
    
    def load(self, session_id: str) -> Session:
        """Load session from disk."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        with open(session_file) as f:
            data = json.load(f)
        
        return Session.from_dict(data)
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List all sessions."""
        sessions = []
        
        for session_file in sorted(
            self.sessions_dir.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            try:
                with open(session_file) as f:
                    data = json.load(f)
                
                sessions.append({
                    'id': data['id'],
                    'name': data['name'],
                    'created_at': data['created_at'],
                    'updated_at': data['updated_at'],
                    'message_count': len(data.get('messages', []))
                })
            except Exception:
                continue
        
        return sessions
    
    def delete(self, session_id: str):
        """Delete session."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            session_file.unlink()
    
    def export(self, session_id: str, format: str = 'markdown') -> str:
        """Export session to readable format."""
        session = self.load(session_id)
        
        if format == 'markdown':
            return self._export_markdown(session)
        elif format == 'json':
            return json.dumps(session.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_markdown(self, session: Session) -> str:
        """Export session as Markdown."""
        lines = [
            f"# {session.name}",
            f"**Session ID:** {session.id}",
            f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Messages:** {len(session.messages)}",
            "",
            "---",
            ""
        ]
        
        for i, msg in enumerate(session.messages, 1):
            role_emoji = "👤" if msg.role == "user" else "🤖"
            timestamp = msg.timestamp.strftime('%H:%M:%S')
            
            lines.append(f"## {i}. {role_emoji} {msg.role.title()} [{timestamp}]")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
