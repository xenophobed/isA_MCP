#!/usr/bin/env python3
"""
Test script to verify session datetime serialization fix
"""

import asyncio
import sys
import os

# Add the user service to the path
sys.path.append('/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/user_service')

from models import SessionCreate
from services.session_service import SessionService


async def test_session_creation():
    """Test session creation to verify datetime serialization fix"""
    
    print("Testing session creation with datetime serialization fix...")
    
    try:
        # Create session service
        session_service = SessionService()
        
        # Create session data
        session_data = SessionCreate(
            user_id="auth0|test123",
            conversation_data={"topic": "test session"},
            metadata={"source": "test"}
        )
        
        print(f"Creating session for user: {session_data.user_id}")
        
        # Attempt to create session
        result = await session_service.create_session(session_data)
        
        if result.is_success:
            print("✅ Session created successfully!")
            print(f"Session ID: {result.data.session_id}")
            print(f"Status: {result.data.status}")
            print(f"Created at: {result.data.created_at}")
            return True
        else:
            print(f"❌ Session creation failed: {result.message}")
            if result.error_details:
                print(f"Error details: {result.error_details}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during session creation: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("=== Session DateTime Serialization Test ===")
    
    success = await test_session_creation()
    
    if success:
        print("\n✅ Test PASSED - DateTime serialization issue is fixed!")
    else:
        print("\n❌ Test FAILED - DateTime serialization issue still exists")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())