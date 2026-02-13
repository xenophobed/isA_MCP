#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for audio_analyzer.py
Focus on transcription functionality - the most frequently used feature
"""

import asyncio
import sys
import os
import json
import pytest
import time
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
sys.path.insert(0, project_root)

from tools.intelligent_tools.audio.audio_analyzer import (
    AudioAnalyzer,
    AnalysisType,
    AudioQuality,
    AudioAnalysisResult,
    SentimentResult,
    MeetingAnalysis,
    AnalysisResult,
)


class TestAudioAnalyzerIntegration:
    """Integration test cases for AudioAnalyzer transcription functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = AudioAnalyzer()

    def test_get_supported_analysis_types(self):
        """Test getting supported analysis types"""
        types = self.analyzer.get_supported_analysis_types()

        assert isinstance(types, list)
        assert len(types) > 0

        expected_types = [
            "sentiment_analysis",
            "meeting_analysis",
            "topic_extraction",
            "content_classification",
            "emotion_detection",
            "speaker_detection",
            "quality_assessment",
        ]

        for expected_type in expected_types:
            assert expected_type in types

    @pytest.mark.asyncio
    async def test_transcribe_method_signature(self):
        """Test the direct transcribe method signature and availability"""
        # Test that the method exists and has the right signature
        assert hasattr(self.analyzer, "transcribe")
        assert callable(self.analyzer.transcribe)

        # Test that the method signature is correct
        import inspect

        sig = inspect.signature(self.analyzer.transcribe)
        expected_params = [
            "audio",
            "language",
            "model",
        ]  # self is not included in bound method signatures
        actual_params = list(sig.parameters.keys())

        assert actual_params == expected_params

        # Test that language and model are optional
        assert sig.parameters["language"].default is None
        assert sig.parameters["model"].default is None

    @pytest.mark.asyncio
    async def test_analyze_placeholder_methods(self):
        """Test that analyze methods return appropriate placeholder responses"""
        # Test analyze method placeholder
        result = await self.analyzer.analyze("test.wav", AnalysisType.SENTIMENT_ANALYSIS)
        assert result.success is False
        assert "not yet implemented" in result.error

        # Test convenience method placeholders
        sentiment = await self.analyzer.analyze_sentiment("test.wav")
        assert sentiment is None

        meeting = await self.analyzer.analyze_meeting("test.wav")
        assert meeting is None

        topics = await self.analyzer.extract_topics("test.wav")
        assert topics is None

    @pytest.mark.asyncio
    async def test_isa_client_initialization(self):
        """Test that ISA client is properly initialized"""
        # Access the client property to trigger lazy loading
        client = self.analyzer.client
        assert client is not None

        # Verify it's the same instance on subsequent calls
        client2 = self.analyzer.client
        assert client is client2

    @pytest.mark.asyncio
    async def test_analysis_types_enum(self):
        """Test that all analysis types are properly defined"""
        # Test that we can create all analysis types
        for analysis_type in AnalysisType:
            assert isinstance(analysis_type.value, str)
            assert len(analysis_type.value) > 0

        # Test specific required types
        required_types = [
            AnalysisType.SENTIMENT_ANALYSIS,
            AnalysisType.MEETING_ANALYSIS,
            AnalysisType.TOPIC_EXTRACTION,
            AnalysisType.CONTENT_CLASSIFICATION,
            AnalysisType.EMOTION_DETECTION,
            AnalysisType.SPEAKER_DETECTION,
            AnalysisType.QUALITY_ASSESSMENT,
        ]

        for analysis_type in required_types:
            assert analysis_type in AnalysisType

    @pytest.mark.asyncio
    async def test_audio_quality_enum(self):
        """Test audio quality enumeration"""
        quality_levels = list(AudioQuality)
        assert len(quality_levels) == 5

        expected_qualities = ["excellent", "good", "fair", "poor", "very_poor"]
        for quality in quality_levels:
            assert quality.value in expected_qualities

    def test_data_classes_structure(self):
        """Test that data classes are properly structured"""
        # Test AnalysisResult
        result = AnalysisResult(success=True, data="test", cost_usd=0.01)
        assert result.success is True
        assert result.data == "test"
        assert result.cost_usd == 0.01
        assert result.error is None

        # Test AudioAnalysisResult
        audio_result = AudioAnalysisResult(
            analysis_type=AnalysisType.SENTIMENT_ANALYSIS,
            transcript="test transcript",
            analysis={"sentiment": "positive"},
            confidence=0.9,
            processing_time=1.5,
            model_used="gpt-4",
            metadata={"duration": 30},
        )
        assert audio_result.analysis_type == AnalysisType.SENTIMENT_ANALYSIS
        assert audio_result.transcript == "test transcript"
        assert audio_result.confidence == 0.9

        # Test SentimentResult
        sentiment_result = SentimentResult(
            overall_sentiment="positive",
            sentiment_score=0.7,
            emotions={"joy": 0.8},
            sentiment_segments=[],
        )
        assert sentiment_result.overall_sentiment == "positive"
        assert sentiment_result.sentiment_score == 0.7

        # Test MeetingAnalysis
        meeting_result = MeetingAnalysis(
            summary="Test meeting",
            key_points=["point1", "point2"],
            action_items=["action1"],
            participants=["user1", "user2"],
            topics_discussed=["topic1"],
            sentiment_flow=[],
            meeting_duration=1800.0,
        )
        assert meeting_result.summary == "Test meeting"
        assert len(meeting_result.key_points) == 2
        assert meeting_result.meeting_duration == 1800.0


async def run_integration_tests():
    """Run integration tests"""
    print("🚀 Starting AudioAnalyzer integration tests (transcription focus)...\n")

    # Run pytest programmatically
    import subprocess
    import sys

    test_file = __file__
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-x"],
        capture_output=True,
        text=True,
    )

    print("📤 Test Output:")
    print(result.stdout)

    if result.stderr:
        print("📤 Test Errors:")
        print(result.stderr)

    print(f"\n{'='*60}")
    print("📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")

    if result.returncode == 0:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
    else:
        print("⚠️  Some tests failed - review output above")
        print(f"Return code: {result.returncode}")


if __name__ == "__main__":
    # For direct execution, run a simple integration test
    async def simple_integration_test():
        print("🧪 Running simple AudioAnalyzer integration test...\n")

        try:
            analyzer = AudioAnalyzer()
            print(f"✅ AudioAnalyzer initialized")

            # Test ISA client initialization
            client = analyzer.client
            print(f"✅ ISA client initialized: {type(client).__name__}")

            # Test getting supported analysis types
            types = analyzer.get_supported_analysis_types()
            print(f"✅ Supported analysis types: {len(types)} found")
            print(f"   Types: {', '.join(types[:3])}...")

            # Test transcribe method (most frequently used feature)
            print(f"\n🔍 Testing transcribe method exists and is callable...")
            assert hasattr(analyzer, "transcribe"), "transcribe method should exist"
            assert callable(analyzer.transcribe), "transcribe method should be callable"
            print(f"✅ Transcribe method available for audio-to-text conversion")

            # Test placeholder methods
            print(f"\n🔍 Testing placeholder methods...")
            sentiment = await analyzer.analyze_sentiment("test.wav")
            assert sentiment is None, "Placeholder should return None"
            print(f"✅ Placeholder methods working correctly")

            print("\n🎉 Simple integration test PASSED!")
            print("📋 AudioAnalyzer is ready with transcription functionality!")
            print("📋 Use analyzer.transcribe(audio_file) for audio-to-text conversion")

        except Exception as e:
            print(f"❌ Simple integration test FAILED: {e}")
            import traceback

            traceback.print_exc()

    asyncio.run(simple_integration_test())
