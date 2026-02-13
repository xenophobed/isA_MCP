#!/usr/bin/env python3
"""
Audio Tools - MCP tools wrapper for audio processing
AI-powered audio transcription and analysis tools

Tools provided:
- transcribe_audio: Convert speech to text
- get_audio_capabilities: List available audio features
"""

import json
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.intelligent_tools.audio.audio_analyzer import AudioAnalyzer, AnalysisResult
from core.logging import get_logger
from core.security import SecurityLevel

logger = get_logger(__name__)


class AudioTools(BaseTool):
    """Audio transcription tools using AudioAnalyzer"""

    def __init__(self):
        super().__init__()
        self.analyzer = AudioAnalyzer()

    def register_tools(self, mcp: FastMCP):
        """Register all audio tools with the MCP server"""
        # transcribe_audio
        self.register_tool(
            mcp,
            self.transcribe_audio_impl,
            name="transcribe_audio",
            description="""Transcribe audio to text using AI transcription services.

Converts speech in audio files to text using advanced AI models.
Supports multiple languages and file formats.

Keywords: audio, transcription, speech, text, convert, voice, recording
Category: audio

Args:
    audio: Audio file path, URL, or audio data to transcribe
    language: Audio language code (en, es, fr, de, it, pt, zh) - auto-detected if not specified
    model: Specific transcription model to use (optional)""",
            security_level=SecurityLevel.MEDIUM,  # Incurs cost
        )

        # get_audio_capabilities
        self.register_tool(
            mcp,
            self.get_capabilities_impl,
            name="get_audio_capabilities",
            description="""Get available audio processing capabilities and features.

Returns information about supported audio features, languages, and implementation status.

Keywords: audio, capabilities, features, support, transcription
Category: audio""",
            security_level=SecurityLevel.LOW,
        )

    async def transcribe_audio_impl(
        self, audio: str, language: Optional[str] = None, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe audio to text"""
        logger.info("Starting audio transcription")

        try:
            result = await self.analyzer.transcribe(audio=audio, language=language, model=model)

            if result.success:
                response_data = {
                    "transcript": result.data["transcript"],
                    "language": result.data["language"],
                    "confidence": result.data["confidence"],
                    "duration": result.data["duration"],
                    "processing_time": result.data["processing_time"],
                    "model_used": result.data["model_used"],
                    "cost": result.cost_usd,
                }

                logger.info(
                    f"Transcription completed (confidence: {result.data['confidence']:.2f})"
                )

                return self.create_response("success", "transcribe_audio", response_data)
            else:
                logger.error(f"Transcription failed: {result.error}")
                return self.create_response("error", "transcribe_audio", {}, result.error)

        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return self.create_response(
                "error", "transcribe_audio", {}, f"Audio transcription failed: {str(e)}"
            )

    async def get_capabilities_impl(self) -> Dict[str, Any]:
        """Get list of supported audio features"""
        analysis_types = self.analyzer.get_supported_analysis_types()

        feature_info = {
            "transcription": {
                "description": "Convert audio to text (main feature)",
                "status": "implemented",
                "cost_estimate": "~$0.006/minute",
            }
        }

        # Add placeholder features
        for analysis_type in analysis_types:
            if analysis_type != "transcription":
                feature_info[analysis_type] = {
                    "description": f"{analysis_type.replace('_', ' ').title()} analysis",
                    "status": "placeholder",
                    "implementation": "future",
                }

        response_data = {
            "main_feature": "transcription",
            "supported_languages": ["en", "es", "fr", "de", "it", "pt", "zh"],
            "features": feature_info,
            "total_features": len(feature_info),
            "implemented_features": 1,
            "placeholder_features": len(analysis_types),
        }

        return self.create_response("success", "get_audio_capabilities", response_data)


def register_audio_tools(mcp: FastMCP):
    """Register audio tools"""
    tool = AudioTools()
    tool.register_tools(mcp)
    logger.debug("Audio tools registered successfully")
    return tool
