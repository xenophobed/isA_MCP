#!/usr/bin/env python3
"""
Audio Tools for MCP Server
Simple audio transcription with ISA integration
"""

import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.intelligence_service.audio.audio_analyzer import AudioAnalyzer, AnalysisResult
from core.logging import get_logger

logger = get_logger(__name__)

class AudioTranscription(BaseTool):
    """Simple audio transcription tool using AudioAnalyzer"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = AudioAnalyzer()
    
    async def transcribe_audio(
        self,
        audio: str,
        language: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio file path, URL, or audio data
            language: Audio language code (optional)
            model: Specific model to use for transcription (optional)
        """
        print(f"🎧 Starting audio transcription")
        
        try:
            result = await self.analyzer.transcribe(
                audio=audio,
                language=language,
                model=model
            )
            
            if result.success:
                response_data = {
                    "transcript": result.data['transcript'],
                    "language": result.data['language'],
                    "confidence": result.data['confidence'],
                    "duration": result.data['duration'],
                    "processing_time": result.data['processing_time'],
                    "model_used": result.data['model_used'],
                    "cost": result.cost_usd
                }
                
                print(f"✅ Transcription completed (confidence: {result.data['confidence']:.2f})")
                print(f"💰 Cost: ${result.cost_usd:.6f}")
                
                return self.create_response(
                    "success",
                    "transcribe_audio",
                    response_data
                )
            else:
                print(f"❌ Transcription failed: {result.error}")
                return self.create_response(
                    "error",
                    "transcribe_audio",
                    {},
                    result.error
                )
                
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return self.create_response(
                "error",
                "transcribe_audio",
                {},
                f"Audio transcription failed: {str(e)}"
            )
    
    def get_supported_features(self) -> str:
        """Get list of supported audio features"""
        analysis_types = self.analyzer.get_supported_analysis_types()
        
        feature_info = {
            "transcription": {
                "description": "Convert audio to text (main feature)",
                "status": "implemented",
                "cost_estimate": "~$0.006/minute"
            }
        }
        
        # Add placeholder features
        for analysis_type in analysis_types:
            if analysis_type != "transcription":
                feature_info[analysis_type] = {
                    "description": f"{analysis_type.replace('_', ' ').title()} analysis",
                    "status": "placeholder",
                    "implementation": "future"
                }
        
        response_data = {
            "main_feature": "transcription",
            "supported_languages": ["en", "es", "fr", "de", "it", "pt", "zh"],
            "features": feature_info,
            "total_features": len(feature_info),
            "implemented_features": 1,
            "placeholder_features": len(analysis_types)
        }
        
        return self.create_response(
            "success",
            "get_supported_features",
            response_data
        )

def register_audio_tools(mcp: FastMCP):
    """Register audio tools"""
    audio_tools = AudioTranscription()
    
    @mcp.tool()
    async def transcribe_audio(
        audio: str,
        language: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text using AI transcription services
        
        This tool converts speech in audio files to text using advanced AI models.
        Supports multiple languages and file formats. Most frequently used audio feature.
        
        Keywords: audio, transcription, speech, text, convert, voice, recording
        Category: audio
        
        Args:
            audio: Audio file path, URL, or audio data to transcribe
            language: Audio language code (en, es, fr, de, it, pt, zh) - auto-detected if not specified
            model: Specific transcription model to use (optional, uses defaults if not specified)
        """
        return await audio_tools.transcribe_audio(audio, language, model)
    
    @mcp.tool()
    def get_audio_capabilities() -> str:
        """
        Get available audio processing capabilities and features
        
        Returns information about supported audio features, languages, and implementation status.
        Shows which features are implemented vs. placeholder for future development.
        
        Keywords: audio, capabilities, features, support, transcription
        Category: audio
        """
        return audio_tools.get_supported_features()
    
    print("🎧 Audio transcription tools registered successfully")

logger.info("Audio tools module loaded successfully")