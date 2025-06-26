#!/usr/bin/env python
"""
Session Manager for Web Services
Manages browser sessions, state persistence, and session lifecycle
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from playwright.async_api import Page, BrowserContext

from core.logging import get_logger
from .browser_manager import BrowserManager

logger = get_logger(__name__)

class SessionManager:
    """Manage browser sessions and state with persistence"""
    
    def __init__(self, browser_manager: BrowserManager = None):
        self.browser_manager = browser_manager or BrowserManager()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.persistent_storage: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = timedelta(hours=2)  # Default session timeout
        self.storage_path = Path("sessions")
        self.storage_path.mkdir(exist_ok=True)
    
    async def get_or_create_session(self, session_id: str, profile_name: str = "stealth") -> Page:
        """Get existing session or create new one"""
        if session_id in self.sessions:
            # Check if session is still valid
            session = self.sessions[session_id]
            if datetime.now() - session['last_used'] < self.session_timeout:
                session['last_used'] = datetime.now()
                return session['page']
            else:
                # Session expired, clean it up
                await self.close_session(session_id)
        
        # Create new session
        return await self.create_session(session_id, profile_name)
    
    async def create_session(self, session_id: str, profile_name: str = "stealth") -> Page:
        """Create new persistent session with state"""
        try:
            # Get page from browser manager
            page = await self.browser_manager.get_page(profile_name, session_id)
            
            # Create session record
            self.sessions[session_id] = {
                'page': page,
                'profile_name': profile_name,
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'state': {},
                'context_id': session_id
            }
            
            # Restore persistent state if exists
            await self.restore_session_state(session_id)
            
            logger.info(f"Session created: {session_id} with profile {profile_name}")
            return page
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise
    
    async def restore_session_state(self, session_id: str):
        """Restore cookies, local storage, session storage from disk"""
        if session_id not in self.sessions:
            return
        
        state_file = self.storage_path / f"{session_id}.json"
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            page = self.sessions[session_id]['page']
            
            # Restore cookies
            if 'cookies' in state and state['cookies']:
                await page.context.add_cookies(state['cookies'])
            
            # Restore local storage and session storage
            if 'localStorage' in state or 'sessionStorage' in state:
                await page.evaluate(f"""
                    // Restore localStorage
                    const localStorage_data = {json.dumps(state.get('localStorage', {}))};
                    for (const [key, value] of Object.entries(localStorage_data)) {{
                        localStorage.setItem(key, value);
                    }}
                    
                    // Restore sessionStorage
                    const sessionStorage_data = {json.dumps(state.get('sessionStorage', {}))};
                    for (const [key, value] of Object.entries(sessionStorage_data)) {{
                        sessionStorage.setItem(key, value);
                    }}
                """)
            
            # Update session state
            self.sessions[session_id]['state'] = state
            logger.info(f"Session state restored for {session_id}")
            
        except Exception as e:
            logger.warning(f"Failed to restore session state for {session_id}: {e}")
    
    async def save_session_state(self, session_id: str):
        """Save current session state to disk"""
        if session_id not in self.sessions:
            return
        
        try:
            page = self.sessions[session_id]['page']
            
            # Get cookies
            cookies = await page.context.cookies()
            
            # Get localStorage and sessionStorage
            storage_data = await page.evaluate("""
                () => {
                    const localStorage_obj = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        localStorage_obj[key] = localStorage.getItem(key);
                    }
                    
                    const sessionStorage_obj = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        sessionStorage_obj[key] = sessionStorage.getItem(key);
                    }
                    
                    return {
                        localStorage: localStorage_obj,
                        sessionStorage: sessionStorage_obj
                    };
                }
            """)
            
            # Combine state
            state = {
                'cookies': cookies,
                'localStorage': storage_data.get('localStorage', {}),
                'sessionStorage': storage_data.get('sessionStorage', {}),
                'saved_at': datetime.now().isoformat()
            }
            
            # Save to disk
            state_file = self.storage_path / f"{session_id}.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Update in-memory state
            self.sessions[session_id]['state'] = state
            logger.info(f"Session state saved for {session_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save session state for {session_id}: {e}")
    
    async def close_session(self, session_id: str, save_state: bool = True):
        """Close session and optionally save state"""
        if session_id not in self.sessions:
            return
        
        try:
            # Save state before closing if requested
            if save_state:
                await self.save_session_state(session_id)
            
            # Close the page through browser manager
            session = self.sessions[session_id]
            page_key = f"{session['profile_name']}_{session['context_id']}_default"
            await self.browser_manager.close_page(page_key)
            
            # Remove from sessions
            del self.sessions[session_id]
            logger.info(f"Session closed: {session_id}")
            
        except Exception as e:
            logger.warning(f"Failed to close session {session_id}: {e}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session['last_used'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.close_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            'session_id': session_id,
            'profile_name': session['profile_name'],
            'created_at': session['created_at'].isoformat(),
            'last_used': session['last_used'].isoformat(),
            'age_minutes': (datetime.now() - session['created_at']).total_seconds() / 60,
            'idle_minutes': (datetime.now() - session['last_used']).total_seconds() / 60,
            'has_state': bool(session.get('state'))
        }
    
    async def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions"""
        session_list = {}
        for session_id in self.sessions:
            info = await self.get_session_info(session_id)
            if info:
                session_list[session_id] = info
        return session_list
    
    async def clear_session_storage(self, session_id: str):
        """Clear persistent storage for a session"""
        state_file = self.storage_path / f"{session_id}.json"
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Cleared persistent storage for session {session_id}")
    
    async def cleanup_all_sessions(self):
        """Close all sessions and cleanup"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        
        logger.info(f"All sessions cleaned up: {len(session_ids)} sessions")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get session manager status"""
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': list(self.sessions.keys()),
            'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
            'storage_path': str(self.storage_path),
            'browser_manager_initialized': self.browser_manager.initialized if self.browser_manager else False
        }