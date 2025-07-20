#!/usr/bin/env python3
"""
MCP Authentication Manager
Utility for managing MCP API keys and authentication settings
"""

import os
import sys
import argparse
import json
from typing import Dict, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from core.mcp_auth_middleware import generate_mcp_api_key, validate_mcp_api_key, setup_mcp_auth_env
from core.logging import get_logger

logger = get_logger(__name__)

class MCPAuthManager:
    """Manager for MCP authentication settings and API keys"""
    
    def __init__(self):
        self.env_file = os.path.join(project_root, "deployment/dev/.env")
    
    def generate_key(self, description: str = "CLI Generated Key") -> str:
        """Generate a new MCP API key"""
        api_key = generate_mcp_api_key(description)
        print(f"Generated MCP API Key: {api_key}")
        print(f"Description: {description}")
        print()
        print("To use this key, clients should include it in requests as:")
        print(f"  Authorization: Bearer {api_key}")
        print("  OR")
        print(f"  X-API-Key: {api_key}")
        print("  OR")
        print(f"  X-MCP-API-Key: {api_key}")
        return api_key
    
    def validate_key(self, api_key: str) -> bool:
        """Validate an API key format"""
        is_valid = validate_mcp_api_key(api_key)
        print(f"API Key: {api_key[:8]}...")
        print(f"Valid Format: {'✅ Yes' if is_valid else '❌ No'}")
        
        if is_valid:
            print("Format Details:")
            if api_key.startswith("mcp_"):
                print("  - Type: MCP Standard Format")
                print("  - Length: 36 characters")
            else:
                print("  - Type: Compatible Format")
                print(f"  - Length: {len(api_key)} characters")
        
        return is_valid
    
    def list_keys(self) -> Dict[str, str]:
        """List currently configured API keys"""
        keys = {}
        
        # Check environment variables
        mcp_key = os.getenv('MCP_API_KEY')
        if mcp_key:
            keys[mcp_key] = "Environment Variable (MCP_API_KEY)"
        
        mcp_keys = os.getenv('MCP_API_KEYS', '')
        if mcp_keys:
            for i, key in enumerate(mcp_keys.split(',')):
                key = key.strip()
                if key:
                    keys[key] = f"Environment Variable (MCP_API_KEYS[{i}])"
        
        # Check core config
        try:
            from core.config import get_settings
            settings = get_settings()
            config_keys = getattr(settings, 'mcp_api_keys', {})
            if isinstance(config_keys, dict):
                for key, desc in config_keys.items():
                    keys[key] = f"Core Config: {desc}"
        except Exception as e:
            logger.debug(f"Could not read core config: {e}")
        
        # Check .env file
        if os.path.exists(self.env_file):
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('MCP_API_KEY='):
                            key = line.split('=', 1)[1].strip('"\'')
                            if key and key not in keys:
                                keys[key] = "Environment File (.env)"
            except Exception as e:
                logger.warning(f"Could not read .env file: {e}")
        
        print(f"Found {len(keys)} configured API keys:")
        print()
        for i, (key, source) in enumerate(keys.items(), 1):
            print(f"{i}. {key[:8]}...{key[-4:]} ({source})")
        
        if not keys:
            print("No API keys found. Use 'generate' command to create one.")
        
        return keys
    
    def save_key(self, api_key: str, description: str = "Saved Key"):
        """Save API key to .env file"""
        # Update .env file
        if os.path.exists(self.env_file):
            try:
                lines = []
                with open(self.env_file, 'r') as f:
                    lines = f.readlines()
                
                # Check if MCP_API_KEY already exists
                key_found = False
                for i, line in enumerate(lines):
                    if line.startswith('MCP_API_KEY='):
                        lines[i] = f'MCP_API_KEY="{api_key}"\n'
                        key_found = True
                        break
                
                # Add if not found
                if not key_found:
                    lines.append(f'MCP_API_KEY="{api_key}"\n')
                    lines.append(f'# {description}\n')
                
                with open(self.env_file, 'w') as f:
                    f.writelines(lines)
                
                print(f"API key saved to {self.env_file}")
                print(f"Key: {api_key[:8]}...")
                print(f"Description: {description}")
            except Exception as e:
                print(f"Failed to save API key: {e}")
        else:
            print(f"Environment file not found: {self.env_file}")
            print("You can manually set the environment variable:")
            print(f"export MCP_API_KEY='{api_key}'")
    
    def enable_auth(self, api_key: Optional[str] = None):
        """Enable MCP authentication"""
        if api_key is None:
            api_key = generate_mcp_api_key("Auto-generated for auth enable")
        
        setup_mcp_auth_env(api_key, require_auth=True)
        
        # Also update .env file if it exists
        if os.path.exists(self.env_file):
            try:
                lines = []
                mcp_key_found = False
                require_auth_found = False
                
                with open(self.env_file, 'r') as f:
                    lines = f.readlines()
                
                # Update existing lines or track if we need to add
                for i, line in enumerate(lines):
                    if line.startswith('MCP_API_KEY='):
                        lines[i] = f'MCP_API_KEY="{api_key}"\n'
                        mcp_key_found = True
                    elif line.startswith('REQUIRE_MCP_AUTH='):
                        lines[i] = 'REQUIRE_MCP_AUTH=true\n'
                        require_auth_found = True
                
                # Add missing lines
                if not mcp_key_found:
                    lines.append(f'MCP_API_KEY="{api_key}"\n')
                if not require_auth_found:
                    lines.append('REQUIRE_MCP_AUTH=true\n')
                
                # Write back
                with open(self.env_file, 'w') as f:
                    f.writelines(lines)
                
                print(f"Updated {self.env_file}")
            except Exception as e:
                logger.warning(f"Could not update .env file: {e}")
        
        print("✅ MCP Authentication ENABLED")
        print(f"API Key: {api_key}")
        print()
        print("Restart the MCP server for changes to take effect.")
        print()
        print("Clients must now include the API key in requests:")
        print(f"  Authorization: Bearer {api_key}")
        
        return api_key
    
    def disable_auth(self):
        """Disable MCP authentication"""
        setup_mcp_auth_env(require_auth=False)
        
        # Update .env file if it exists
        if os.path.exists(self.env_file):
            try:
                lines = []
                with open(self.env_file, 'r') as f:
                    lines = f.readlines()
                
                # Update require auth line
                for i, line in enumerate(lines):
                    if line.startswith('REQUIRE_MCP_AUTH='):
                        lines[i] = 'REQUIRE_MCP_AUTH=false\n'
                        break
                else:
                    # Add if not found
                    lines.append('REQUIRE_MCP_AUTH=false\n')
                
                with open(self.env_file, 'w') as f:
                    f.writelines(lines)
                
                print(f"Updated {self.env_file}")
            except Exception as e:
                logger.warning(f"Could not update .env file: {e}")
        
        print("✅ MCP Authentication DISABLED")
        print("Restart the MCP server for changes to take effect.")
        print("Clients can now access MCP endpoints without API keys.")
    
    def check_status(self):
        """Check current authentication status"""
        require_auth = os.getenv('REQUIRE_MCP_AUTH', 'false').lower() == 'true'
        keys = self.list_keys()
        
        print("MCP Authentication Status")
        print("=" * 40)
        print(f"Authentication Required: {'✅ Yes' if require_auth else '❌ No'}")
        print(f"Configured API Keys: {len(keys)}")
        
        if require_auth and not keys:
            print("⚠️  WARNING: Authentication is required but no API keys are configured!")
            print("   Use 'enable-auth' command to generate a key and enable authentication.")
        elif require_auth:
            print("✅ Authentication is properly configured.")
        else:
            print("ℹ️  Authentication is disabled - MCP endpoints are publicly accessible.")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="MCP Authentication Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate key command
    gen_parser = subparsers.add_parser('generate', help='Generate a new API key')
    gen_parser.add_argument('--description', '-d', default='CLI Generated Key', 
                           help='Description for the API key')
    gen_parser.add_argument('--save', '-s', action='store_true', 
                           help='Save the key to configuration')
    
    # Validate key command
    val_parser = subparsers.add_parser('validate', help='Validate an API key format')
    val_parser.add_argument('api_key', help='API key to validate')
    
    # List keys command
    subparsers.add_parser('list', help='List configured API keys')
    
    # Save key command
    save_parser = subparsers.add_parser('save', help='Save an API key to configuration')
    save_parser.add_argument('api_key', help='API key to save')
    save_parser.add_argument('--description', '-d', default='Manually saved key',
                            help='Description for the API key')
    
    # Enable auth command
    enable_parser = subparsers.add_parser('enable-auth', help='Enable MCP authentication')
    enable_parser.add_argument('--api-key', help='Use specific API key (generates one if not provided)')
    
    # Disable auth command
    subparsers.add_parser('disable-auth', help='Disable MCP authentication')
    
    # Status command
    subparsers.add_parser('status', help='Check authentication status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MCPAuthManager()
    
    try:
        if args.command == 'generate':
            api_key = manager.generate_key(args.description)
            if args.save:
                manager.save_key(api_key, args.description)
        
        elif args.command == 'validate':
            manager.validate_key(args.api_key)
        
        elif args.command == 'list':
            manager.list_keys()
        
        elif args.command == 'save':
            if manager.validate_key(args.api_key):
                manager.save_key(args.api_key, args.description)
            else:
                print("❌ Invalid API key format - not saved")
                sys.exit(1)
        
        elif args.command == 'enable-auth':
            manager.enable_auth(args.api_key)
        
        elif args.command == 'disable-auth':
            manager.disable_auth()
        
        elif args.command == 'status':
            manager.check_status()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()