# AudioAnalyzer Documentation

## Overview

The `audio_analyzer.py` provides simple audio transcription through direct integration with ISA services. **Focus on the most frequently used feature: transcription.** Other analysis features are currently placeholder methods for future implementation.

## Usage

### Transcription (Main Feature)

```python
from tools.services.intelligence_service.audio.audio_analyzer import AudioAnalyzer

# Basic transcription - the primary functionality
analyzer = AudioAnalyzer()
result = await analyzer.transcribe("path/to/audio.wav")

if result.success:
    print(f"Transcript: {result.data['transcript']}")
    print(f"Language: {result.data['language']}")
    print(f"Confidence: {result.data['confidence']}")
    print(f"Duration: {result.data['duration']}s")
    print(f"Processing time: {result.data['processing_time']}s")
    print(f"Cost: ${result.cost_usd:.6f}")
else:
    print(f"Transcription failed: {result.error}")
```

### Transcription with Parameters

```python
# Transcription with specific language and model
result = await analyzer.transcribe(
    audio="spanish_audio.wav",
    language="es",
    model="whisper-1"
)

if result.success:
    transcript = result.data['transcript']
    print(f"Spanish transcript: {transcript}")
```

### Placeholder Methods

```python
# Main transcription method
result = await analyzer.transcribe("audio.wav")
if result.success:
    transcript = result.data['transcript']
    print(f"Transcript: {transcript}")

# Placeholder methods (return None for future implementation)
sentiment = await analyzer.analyze_sentiment("audio.wav")
print(sentiment)  # None

meeting = await analyzer.analyze_meeting("audio.wav")
print(meeting)  # None

topics = await analyzer.extract_topics("lecture.wav", num_topics=5)
print(topics)  # None

# Advanced analysis placeholder (returns error)
result = await analyzer.analyze(
    audio="audio.wav",
    analysis_type=AnalysisType.SENTIMENT_ANALYSIS
)
print(f"Success: {result.success}")  # False
print(f"Error: {result.error}")  # "Advanced analysis not yet implemented"
```

## API Reference

### `AudioAnalyzer.transcribe(audio, **kwargs)`

**Most frequently used method** - Simple audio transcription.

**Parameters:**
- `audio` (str|bytes): Audio file path, URL, or raw bytes
- `language` (str, optional): Audio language code (e.g., 'en', 'es', 'fr')
- `model` (str, optional): Specific model to use for transcription

**Returns:**
- `AnalysisResult`: Contains transcription data including transcript, language, confidence, duration, and cost

### `AudioAnalyzer.analyze(audio, analysis_type, **kwargs)`

**Placeholder method** - Returns error response indicating feature not yet implemented.

**Parameters:**
- `audio` (str|bytes): Audio file path, URL, or raw bytes
- `analysis_type` (AnalysisType): Type of analysis to perform
- `language` (str, optional): Audio language code (e.g., 'en', 'es', 'fr')
- `model` (str, optional): Specific model to use for analysis

**Returns:**
- `AnalysisResult`: Contains success=False and "not yet implemented" error message

### `AudioAnalyzer.analyze_sentiment(audio, **kwargs)`

**Placeholder method** - Returns None for future implementation.

**Parameters:**
- `audio` (str|bytes): Audio file path, URL, or raw bytes
- `language` (str, optional): Audio language code
- `model` (str, optional): Specific model to use

**Returns:**
- `None`: Placeholder for future sentiment analysis functionality

### `AudioAnalyzer.analyze_meeting(audio, **kwargs)`

**Placeholder method** - Returns None for future implementation.

**Returns:**
- `None`: Placeholder for future meeting analysis functionality

### `AudioAnalyzer.extract_topics(audio, num_topics=5, **kwargs)`

**Placeholder method** - Returns None for future implementation.

**Parameters:**
- `audio` (str|bytes): Audio file path, URL, or raw bytes
- `num_topics` (int): Maximum number of topics to extract (default: 5)
- `language` (str, optional): Audio language code
- `model` (str, optional): Specific model to use

**Returns:**
- `None`: Placeholder for future topic extraction functionality

## Analysis Types

### Available Types (For Future Implementation)
- **SENTIMENT_ANALYSIS**: Overall sentiment and emotional analysis (placeholder)
- **MEETING_ANALYSIS**: Meeting summaries, action items, and participants (placeholder)
- **TOPIC_EXTRACTION**: Main topics and keywords identification (placeholder)
- **CONTENT_CLASSIFICATION**: Content categorization and formality assessment (placeholder)
- **EMOTION_DETECTION**: Detailed emotion detection and intensity (placeholder)
- **SPEAKER_DETECTION**: Speaker identification and patterns (placeholder)
- **QUALITY_ASSESSMENT**: Audio quality evaluation based on transcription (placeholder)

```python
# Get all supported types (returns list but features are placeholders)
types = analyzer.get_supported_analysis_types()
print(f"Types defined: {types}")
# ['content_classification', 'sentiment_analysis', 'speaker_detection', ...]
```

## Examples

### Audio Transcription (Main Feature)
```python
# Simple transcription
result = await analyzer.transcribe("interview.wav")

if result.success:
    data = result.data
    print(f"Transcript: {data['transcript']}")
    print(f"Language detected: {data['language']}")
    print(f"Confidence: {data['confidence']:.2f}")
    print(f"Audio duration: {data['duration']:.1f}s")
    print(f"Processing time: {data['processing_time']:.1f}s")
    print(f"Cost: ${result.cost_usd:.6f}")
else:
    print(f"Transcription failed: {result.error}")

# Multi-language transcription
spanish_result = await analyzer.transcribe(
    audio="spanish_audio.wav",
    language="es",
    model="whisper-1"
)
```

### Batch Transcription
```python
# Transcribe multiple audio files
audio_files = ["meeting1.wav", "meeting2.wav", "meeting3.wav"]
results = []

for audio_file in audio_files:
    result = await analyzer.transcribe(audio_file)
    results.append(result)

# Analyze results
successful = [r for r in results if r.success]
total_cost = sum(r.cost_usd for r in successful)
print(f"Transcribed {len(successful)}/{len(results)} files")
print(f"Total cost: ${total_cost:.6f}")

# Print transcripts
for i, result in enumerate(successful):
    print(f"File {i+1} transcript: {result.data['transcript'][:100]}...")
```

## Error Handling

Always check for success and handle errors gracefully:

```python
try:
    # Main transcription functionality
    result = await analyzer.transcribe("audio.wav")
    
    if result.success:
        print(f"Transcript: {result.data['transcript']}")
        print(f"Cost: ${result.cost_usd:.6f}")
    else:
        print(f"Transcription failed: {result.error}")
    
    # Placeholder methods return None
    sentiment = await analyzer.analyze_sentiment("audio.wav")
    if sentiment is None:
        print("Sentiment analysis not yet implemented")
        
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Notes

- **Cost**: Audio transcription ~$0.006/minute via ISA services
- **Speed**: Transcription 1-5s per minute of audio
- **Streaming**: All ISA streaming complexity handled internally
- **Logging**: Transcription costs and performance automatically logged
- **Limitations**: Only transcription is functional; other analysis features are placeholders

## Parameters

### Language Codes
- **en**: English (default)
- **es**: Spanish
- **fr**: French
- **de**: German
- **it**: Italian
- **pt**: Portuguese
- **zh**: Chinese

### Models
- **Audio Transcription**: Uses ISA audio service defaults (typically Whisper-based)
- Custom models can be specified if available in your ISA configuration
- **Note**: Text analysis models not currently used (placeholder features)

### Audio Quality
The system automatically assesses audio quality based on transcription confidence:
- **Excellent**: >= 0.9 confidence
- **Good**: >= 0.8 confidence  
- **Fair**: >= 0.6 confidence
- **Poor**: >= 0.4 confidence
- **Very Poor**: < 0.4 confidence

## Integration

### In MCP Tools
```python
from tools.services.intelligence_service.audio.audio_analyzer import AudioAnalyzer

class AudioTranscriptionTool(BaseTool):
    async def transcribe_audio(self, audio_path, language=None):
        analyzer = AudioAnalyzer()
        result = await analyzer.transcribe(audio_path, language=language)
        
        return {
            "success": result.success,
            "transcript": result.data['transcript'] if result.success else None,
            "cost": result.cost_usd,
            "error": result.error
        }
```

### In Services
```python
from tools.services.intelligence_service.audio.audio_analyzer import AudioAnalyzer

class TranscriptionService:
    def __init__(self):
        self.analyzer = AudioAnalyzer()
    
    async def process_audio_file(self, audio_file):
        result = await self.analyzer.transcribe(audio_file)
        if result.success:
            return {
                "transcript": result.data['transcript'],
                "language": result.data['language'],
                "confidence": result.data['confidence'],
                "cost": result.cost_usd
            }
        return None
```

### With Web Uploads
```python
async def process_uploaded_audio(file_bytes):
    analyzer = AudioAnalyzer()
    
    # Perform transcription
    result = await analyzer.transcribe(file_bytes)
    
    if result.success:
        return {
            "transcript": result.data['transcript'],
            "language": result.data['language'],
            "confidence": result.data['confidence'],
            "duration": result.data['duration'],
            "cost": result.cost_usd
        }
    return {"error": result.error}
```

## Testing

Run the integration tests:
```bash
# Run all tests
python -m pytest tools/services/intelligence_service/audio/tests/test_audio_analyzer.py -v

# Run simple integration test
python tools/services/intelligence_service/audio/tests/test_audio_analyzer.py
```

The tests cover:
- Transcription functionality with real ISA service calls
- Placeholder method behavior (returning None/errors)
- Error handling scenarios
- Data structure validation
- ISA client initialization and lazy loading

## Summary

The AudioAnalyzer provides a simple, focused interface for audio transcription:
- **Simple**: Just call `transcribe(audio)` and get structured results
- **Focused**: Concentrates on the most frequently used feature - transcription
- **Robust**: Handles ISA service integration and streaming complexity automatically
- **Efficient**: Tracks costs and performance metrics
- **Future-Ready**: Placeholder methods ready for implementing additional analysis features
- **Easy Integration**: Works seamlessly with MCP tools and web services

Perfect for applications that need reliable audio-to-text conversion with plans for future audio analysis features.