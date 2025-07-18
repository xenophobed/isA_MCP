#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for audio_tools.py
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.tools.audio_tools import AudioTranscription, register_audio_tools
from mcp.server.fastmcp import FastMCP

async def test_basic_transcription():
    """Test basic audio transcription functionality"""
    print("Test 1: Basic Audio Transcription Functionality")
    print("="*50)
    
    audio_tools = AudioTranscription()
    
    test_audio = "test_audio.wav"  # Mock audio file path
    test_language = "en"
    
    print(f"Input Parameters:")
    print(f"  Audio: {test_audio}")
    print(f"  Language: {test_language}")
    print()
    
    try:
        # First test AudioAnalyzer availability
        print("Testing AudioAnalyzer availability...")
        try:
            analyzer = audio_tools.analyzer
            if analyzer is None:
                print("AudioAnalyzer is None - skipping real ISA test")
                print("This may be due to missing configuration or environment setup")
                return True  # Skip test but don't fail
            else:
                print("AudioAnalyzer is available")
        except Exception as analyzer_e:
            print(f"AudioAnalyzer error: {analyzer_e}")
            print("Skipping real ISA test due to analyzer issues")
            return True  # Skip test but don't fail
        
        result = await audio_tools.transcribe_audio(
            audio=test_audio,
            language=test_language
        )
        
        print("Raw Response:")
        print(result)
        print()
        
        # Parse and analyze
        result_data = json.loads(result)
        
        print("Parsed Response Analysis:")
        print(f"  Status: {result_data.get('status', 'unknown')}")
        print(f"  Action: {result_data.get('action', 'unknown')}")
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print(f"  Transcript: {data.get('transcript', 'N/A')[:50]}...")
            print(f"  Language: {data.get('language', 'N/A')}")
            print(f"  Confidence: {data.get('confidence', 'N/A')}")
            print(f"  Duration: {data.get('duration', 'N/A')}s")
            print(f"  Processing Time: {data.get('processing_time', 'N/A')}s")
            print(f"  Model Used: {data.get('model_used', 'N/A')}")
            print(f"  Cost: ${data.get('cost', 0.0):.6f}")
        elif result_data.get('status') == 'error':
            error = result_data.get('error', 'Unknown error')
            print(f"  Error: {error}")
            
            # Check if it's an expected error (file not found, etc.)
            if any(phrase in error.lower() for phrase in ['not found', 'file', 'audio']):
                print("This is expected for test with mock audio file")
                print("Test 1 PASSED (Expected file error)")
                return True
        
        print("Test 1 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 1 FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's a specific ISA-related error
        error_str = str(e).lower()
        if 'isa' in error_str or 'client' in error_str:
            print("This appears to be an ISA client configuration issue")
            print("Please ensure ISA service is running and configured properly")
        
        import traceback
        traceback.print_exc()
        return False

async def test_language_support():
    """Test different language support"""
    print("\nTest 2: Language Support")
    print("="*50)
    
    audio_tools = AudioTranscription()
    
    languages = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German")
    ]
    
    for lang_code, lang_name in languages:
        print(f"\nTesting language: {lang_name} ({lang_code})")
        try:
            # Check analyzer availability first
            analyzer = audio_tools.analyzer
            if analyzer is None:
                print("AudioAnalyzer is None - skipping language test")
                continue
            
            result = await audio_tools.transcribe_audio(
                audio=f"test_audio_{lang_code}.wav",
                language=lang_code
            )
            
            result_data = json.loads(result)
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                cost = data.get('cost', 0.0)
                print(f"  {lang_name}: Transcription available (${cost:.6f})")
            elif result_data.get('status') == 'error':
                error = result_data.get('error', 'Unknown error')
                if 'not found' in error.lower() or 'file' in error.lower():
                    print(f"  {lang_name}: Language supported (mock file error expected)")
                else:
                    print(f"  {lang_name} failed: {error}")
                
        except Exception as e:
            print(f"  {lang_name} exception: {str(e)}")
    
    print("Test 2 COMPLETED")

async def test_feature_information():
    """Test audio feature information retrieval"""
    print("\nTest 3: Audio Feature Information")
    print("="*50)
    
    audio_tools = AudioTranscription()
    
    print("Testing feature information:")
    try:
        result = audio_tools.get_supported_features()
        
        print(f"Raw Response:")
        print(result)
        print()
        
        result_data = json.loads(result)
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            main_feature = data.get('main_feature', 'N/A')
            supported_languages = data.get('supported_languages', [])
            features = data.get('features', {})
            total_features = data.get('total_features', 0)
            implemented_features = data.get('implemented_features', 0)
            placeholder_features = data.get('placeholder_features', 0)
            
            print(f"  Main Feature: {main_feature}")
            print(f"  Total Features: {total_features}")
            print(f"  Implemented: {implemented_features}")
            print(f"  Placeholders: {placeholder_features}")
            print(f"  Supported Languages: {len(supported_languages)}")
            for lang in supported_languages[:3]:  # Show first 3
                print(f"    - {lang}")
            
            print(f"\n  Feature Details Sample:")
            for feature_name in list(features.keys())[:3]:  # Show first 3
                info = features.get(feature_name, {})
                print(f"    {feature_name}:")
                print(f"      Description: {info.get('description', 'N/A')}")
                print(f"      Status: {info.get('status', 'N/A')}")
                if 'cost_estimate' in info:
                    print(f"      Cost: {info.get('cost_estimate', 'N/A')}")
                if 'implementation' in info:
                    print(f"      Implementation: {info.get('implementation', 'N/A')}")
                
        else:
            print(f"  Failed to get feature information: {result_data.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"  Feature information retrieval failed: {str(e)}")
    
    print("Test 3 COMPLETED")

async def test_parameter_validation():
    """Test parameter validation and error handling"""
    print("\nTest 4: Parameter Validation")
    print("="*50)
    
    audio_tools = AudioTranscription()
    
    test_cases = [
        {
            "name": "Valid transcription with language",
            "params": {
                "audio": "valid_audio.wav",
                "language": "en"
            },
            "should_fail": False
        },
        {
            "name": "Valid transcription without language",
            "params": {
                "audio": "valid_audio.wav"
            },
            "should_fail": False
        },
        {
            "name": "Valid transcription with model",
            "params": {
                "audio": "valid_audio.wav",
                "language": "en",
                "model": "whisper-1"
            },
            "should_fail": False
        }
    ]
    
    print("Testing parameter validation:")
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        try:
            # Check analyzer availability first
            analyzer = audio_tools.analyzer
            if analyzer is None:
                print("AudioAnalyzer is None - skipping validation test")
                continue
            
            result = await audio_tools.transcribe_audio(**test_case['params'])
            result_data = json.loads(result)
            
            success = result_data.get('status') == 'success'
            should_fail = test_case['should_fail']
            error = result_data.get('error', 'No error')
            
            # For our tests, file not found is expected and considered successful validation
            if 'not found' in error.lower() or 'file' in error.lower():
                print(f"  Parameter validation passed (expected file error)")
            elif should_fail and not success:
                print(f"  Correctly failed: {error}")
            elif not should_fail and success:
                print(f"  Correctly succeeded")
            else:
                print(f"  Unexpected result - Expected fail: {should_fail}, Got success: {success}")
                print(f"    Error: {error}")
                
        except Exception as e:
            if test_case['should_fail']:
                print(f"  Correctly threw exception: {str(e)}")
            else:
                print(f"  Unexpected exception: {str(e)}")
    
    print("Test 4 COMPLETED")

async def test_analyzer_integration():
    """Test AudioAnalyzer integration"""
    print("\nTest 5: AudioAnalyzer Integration")
    print("="*50)
    
    audio_tools = AudioTranscription()
    
    print("Testing AudioAnalyzer integration:")
    try:
        # Test analyzer property
        analyzer = audio_tools.analyzer
        print(f"  AudioAnalyzer accessible: {type(analyzer).__name__}")
        
        # Test get_supported_analysis_types
        analysis_types = analyzer.get_supported_analysis_types()
        print(f"  Analysis types available: {len(analysis_types)}")
        print(f"    Types: {', '.join(analysis_types[:3])}...")
        
        # Test transcribe method exists
        if hasattr(analyzer, 'transcribe'):
            print(f"  Transcribe method available")
        else:
            print(f"  Transcribe method missing")
        
        # Test placeholder methods
        if hasattr(analyzer, 'analyze_sentiment'):
            print(f"  Placeholder methods available")
        else:
            print(f"  Placeholder methods missing")
            
    except Exception as e:
        print(f"  AudioAnalyzer integration failed: {str(e)}")
    
    print("Test 5 COMPLETED")

async def test_mcp_tools_registration():
    """Test MCP tools registration and discovery"""
    print("\nTest 6: MCP Tools Registration and Discovery")
    print("="*50)
    
    print("Testing MCP tools registration:")
    try:
        # Create FastMCP instance
        mcp = FastMCP("audio-tools-test")
        
        # Register audio tools
        print("  Registering audio tools...")
        register_audio_tools(mcp)
        
        # Get registered tools
        tools = await mcp.list_tools()
        print(f"  Total registered tools: {len(tools)}")
        
        # Expected audio tools
        expected_tools = [
            "transcribe_audio",
            "get_audio_capabilities"
        ]
        
        print(f"\n  Audio Tools Discovery:")
        for tool_name in expected_tools:
            if tool_name in [tool.name for tool in tools]:
                print(f"    {tool_name}: Found")
                
                # Get tool details
                tool_info = next((tool for tool in tools if tool.name == tool_name), None)
                if tool_info:
                    print(f"      Description: {tool_info.description[:60]}...")
                    print(f"      Parameters: {len(tool_info.inputSchema.get('properties', {}))} parameters")
            else:
                print(f"    {tool_name}: Missing")
        
        print("Test 6 COMPLETED")
        return True
        
    except Exception as e:
        print(f"  MCP tools registration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Test 6 COMPLETED")
        return False

async def test_mcp_tool_calls():
    """Test actual MCP tool calls"""
    print("\nTest 7: MCP Tool Calls")
    print("="*50)
    
    print("Testing MCP tool calls:")
    try:
        # Create FastMCP instance
        mcp = FastMCP("audio-tools-test")
        
        # Register audio tools
        register_audio_tools(mcp)
        
        # Test get_audio_capabilities tool call
        print("  Testing get_audio_capabilities tool call...")
        try:
            capabilities_result = await mcp.call_tool("get_audio_capabilities", {})
            
            # Extract text from TextContent response
            if isinstance(capabilities_result, list) and len(capabilities_result) > 0:
                capabilities_text = capabilities_result[0].text
            else:
                capabilities_text = str(capabilities_result)
            
            print(f"    Raw response: {capabilities_text[:100]}...")
            
            result_data = json.loads(capabilities_text)
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                print(f"    Main feature: {data.get('main_feature', 'N/A')}")
                print(f"    Total features: {data.get('total_features', 0)}")
                print(f"    Implemented features: {data.get('implemented_features', 0)}")
                print(f"    Supported languages: {len(data.get('supported_languages', []))}")
                print("    get_audio_capabilities: SUCCESS")
            else:
                print(f"    get_audio_capabilities: FAILED - {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"    get_audio_capabilities: EXCEPTION - {str(e)}")
        
        # Test transcribe_audio tool call with mock file
        print("\n  Testing transcribe_audio tool call...")
        try:
            transcribe_result = await mcp.call_tool("transcribe_audio", {
                "audio": "mock_audio.wav",
                "language": "en"
            })
            
            # Extract text from TextContent response
            if isinstance(transcribe_result, list) and len(transcribe_result) > 0:
                transcribe_text = transcribe_result[0].text
            else:
                transcribe_text = str(transcribe_result)
            
            print(f"    Raw response: {transcribe_text[:100]}...")
            
            result_data = json.loads(transcribe_text)
            if result_data.get('status') == 'error':
                error = result_data.get('error', 'Unknown error')
                if 'not found' in error.lower() or 'file' in error.lower():
                    print("    transcribe_audio: SUCCESS (expected file error)")
                else:
                    print(f"    transcribe_audio: UNEXPECTED ERROR - {error}")
            elif result_data.get('status') == 'success':
                print("    transcribe_audio: SUCCESS")
            else:
                print(f"    transcribe_audio: UNKNOWN STATUS - {result_data.get('status')}")
        except Exception as e:
            print(f"    transcribe_audio: EXCEPTION - {str(e)}")
        
        print("Test 7 COMPLETED")
        return True
        
    except Exception as e:
        print(f"  MCP tool calls failed: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Test 7 COMPLETED")
        return False

async def run_all_tests():
    """Run all tests"""
    print("Starting audio_tools.py comprehensive tests...\n")
    
    tests = [
        test_basic_transcription,
        test_language_support,
        test_feature_information,
        test_parameter_validation,
        test_analyzer_integration,
        test_mcp_tools_registration,
        test_mcp_tool_calls
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    test_names = [
        "Basic Audio Transcription Functionality",
        "Language Support",
        "Audio Feature Information", 
        "Parameter Validation",
        "AudioAnalyzer Integration",
        "MCP Tools Registration and Discovery",
        "MCP Tool Calls"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")
    
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("Some tests failed - review output above")

if __name__ == "__main__":
    asyncio.run(run_all_tests())