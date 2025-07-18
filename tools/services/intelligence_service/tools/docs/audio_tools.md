# Audio Tools Documentation

## Overview

The `audio_tools.py` provides simple audio transcription capabilities for MCP clients. It focuses on the most frequently used audio feature - converting speech to text - using AI-powered transcription models with automatic cost tracking and transparent billing information.

## Available Tools

### `transcribe_audio`

Converts speech in audio files to text using advanced AI transcription services. This is the primary and most frequently used audio processing feature.

**Function Signature:**
```python
async def transcribe_audio(
    audio: str,
    language: Optional[str] = None,
    model: Optional[str] = None
) -> str
```

**Parameters:**
- `audio` (required): Audio file path, URL, or audio data to transcribe
- `language` (optional): Audio language code (en, es, fr, de, it, pt, zh) - auto-detected if not specified
- `model` (optional): Specific transcription model to use (optional, uses defaults if not specified)

**Returns:**
JSON response with transcription text, confidence scores, language detection, and cost information

## Transcription Capabilities

The AI automatically selects the most appropriate transcription model and processing approach:

### Audio Transcription
Convert speech in audio files to text using ISA audio services (typically Whisper-based).
```
Primary Feature: Audio-to-text conversion
Cost: ~$0.006 per minute
Speed: ⚡ Fast (1-5s per minute)
Languages: Multiple languages supported
```

## Usage Examples

### Basic Audio Transcription
```python
# Convert speech to text - the primary functionality
result = await mcp_client.call_tool("transcribe_audio", {
    "audio": "recording.wav"
})
```

### Transcription with Language Specification
```python
# Specify language for better accuracy
result = await mcp_client.call_tool("transcribe_audio", {
    "audio": "spanish_recording.wav",
    "language": "es"
})
```

### Transcription with Custom Model
```python
# Use specific transcription model
result = await mcp_client.call_tool("transcribe_audio", {
    "audio": "meeting.wav",
    "language": "en",
    "model": "whisper-1"
})
```

### Batch Transcription
```python
# Process multiple audio files
audio_files = ["meeting1.wav", "interview.mp3", "lecture.m4a"]
results = []

for audio_file in audio_files:
    result = await mcp_client.call_tool("transcribe_audio", {
        "audio": audio_file,
        "language": "en"
    })
    results.append(result)
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "action": "transcribe_audio",
  "data": {
    "transcript": "This is the transcribed text from the audio file...",
    "language": "en",
    "confidence": 0.92,
    "duration": 120.5,
    "processing_time": 3.2,
    "model_used": "whisper-1",
    "cost": 0.012
  },
  "timestamp": "2025-07-14T16:52:22.071592"
}
```

### Error Response
```json
{
  "status": "error",
  "action": "transcribe_audio",
  "data": {},
  "error": "Audio file not found: invalid_path.wav",
  "timestamp": "2025-07-14T16:52:22.071592"
}
```

## Audio Capabilities Information

### `get_audio_capabilities`

Get detailed information about supported audio features and their implementation status.

**Function Signature:**
```python
def get_audio_capabilities() -> str
```

**Returns:**
Comprehensive information about available audio features, languages, and implementation status.

**Usage:**
```python
result = await mcp_client.call_tool("get_audio_capabilities", {})
```

**Response:**
```json
{
  "status": "success",
  "action": "get_supported_features",
  "data": {
    "main_feature": "transcription",
    "supported_languages": ["en", "es", "fr", "de", "it", "pt", "zh"],
    "features": {
      "transcription": {
        "description": "Convert audio to text (main feature)",
        "status": "implemented",
        "cost_estimate": "~$0.006/minute"
      },
      "sentiment_analysis": {
        "description": "Sentiment Analysis analysis",
        "status": "placeholder",
        "implementation": "future"
      },
      "meeting_analysis": {
        "description": "Meeting Analysis analysis",
        "status": "placeholder", 
        "implementation": "future"
      }
    },
    "total_features": 8,
    "implemented_features": 1,
    "placeholder_features": 7
  }
}
```

## Audio Format Support

### Supported Formats
- **WAV** - Uncompressed audio (recommended for best quality)
- **MP3** - Compressed audio (widely supported)
- **M4A** - Apple audio format
- **FLAC** - Lossless compression
- **OGG** - Open-source audio format

### Audio Quality Recommendations
- **Sample Rate**: 16kHz or higher (44.1kHz recommended)
- **Bit Depth**: 16-bit minimum (24-bit recommended)
- **Channels**: Mono or stereo supported
- **Duration**: Up to 2 hours per file recommended
- **File Size**: Varies by format and duration

### Audio Input Methods
1. **File Path**: Local file system path
   ```python
   "audio": "/path/to/recording.wav"
   ```

2. **URL**: Direct URL to audio file
   ```python
   "audio": "https://example.com/audio.mp3"
   ```

3. **Audio Data**: For programmatic upload
   ```python
   "audio": "base64_encoded_audio_data"
   ```

## Language Support

### Supported Languages
- **English** (`en`) - Highest accuracy
- **Spanish** (`es`) - High accuracy
- **French** (`fr`) - High accuracy
- **German** (`de`) - High accuracy
- **Italian** (`it`) - Good accuracy
- **Portuguese** (`pt`) - Good accuracy
- **Chinese** (`zh`) - Good accuracy

### Language Detection
If no language is specified, the system will attempt automatic language detection during transcription.

## Model Selection

### Available Models
- **Default**: Automatically selected optimal model (typically Whisper-based)
- **whisper-1**: OpenAI Whisper for transcription
- **Custom models**: Can be specified if available in ISA configuration

### Model Recommendations
- **General Use**: Use default models for best balance of speed/accuracy
- **High Accuracy**: Specify advanced models when available
- **Multilingual**: Default models handle multiple languages well

## Performance and Costs

### Processing Time
- **Transcription**: ~1-5 seconds per minute of audio
- **Language Detection**: Included in transcription time
- **Total**: Typically 1-5 seconds per minute of audio

### Cost Structure
- **Audio Transcription**: ~$0.006 per minute
- **Cost varies by**: Audio duration, quality, and language
- **No additional costs**: For language detection or basic processing

### Cost Tracking
All operations include detailed cost information:
```json
"data": {
  "transcript": "...",
  "cost": 0.012,
  "duration": 120.5,
  "processing_time": 3.2
}
```

## Future Features (Placeholders)

The following features are defined but not yet implemented:

### Placeholder Features
- **Sentiment Analysis**: Audio emotional sentiment analysis
- **Meeting Analysis**: Meeting summaries, action items, participants
- **Topic Extraction**: Main topics and keywords identification
- **Content Classification**: Audio content categorization
- **Emotion Detection**: Detailed emotion detection and intensity
- **Speaker Detection**: Speaker identification and patterns
- **Quality Assessment**: Audio quality evaluation

These features currently return placeholder responses and will be implemented in future versions.

## Integration Examples

### React Agent Integration
```python
# In your React agent workflow
async def process_user_audio(audio_file):
    # Transcribe audio content
    result = await mcp_client.call_tool("transcribe_audio", {
        "audio": audio_file,
        "language": "en"
    })
    
    result_data = json.loads(result)
    if result_data["status"] == "success":
        transcript = result_data["data"]["transcript"]
        confidence = result_data["data"]["confidence"]
        cost = result_data["data"]["cost"]
        
        return {
            "transcript": transcript,
            "confidence": confidence,
            "cost": cost
        }
    
    return {"error": result_data["error"]}
```

### Batch Processing
```python
# Process multiple audio files
async def batch_transcribe_audio(audio_files):
    results = []
    total_cost = 0.0
    
    for audio_file in audio_files:
        result = await mcp_client.call_tool("transcribe_audio", {
            "audio": audio_file
        })
        
        result_data = json.loads(result)
        if result_data["status"] == "success":
            data = result_data["data"]
            results.append({
                "file": audio_file,
                "transcript": data["transcript"],
                "confidence": data["confidence"],
                "cost": data["cost"]
            })
            total_cost += data["cost"]
    
    print(f"Transcribed {len(results)} files for ${total_cost:.6f}")
    return results
```

### Meeting Transcription Pipeline
```python
# Complete meeting transcription workflow
async def transcribe_meeting_pipeline(meeting_audio):
    # Step 1: Transcribe the meeting
    result = await mcp_client.call_tool("transcribe_audio", {
        "audio": meeting_audio,
        "language": "en"
    })
    
    result_data = json.loads(result)
    if result_data["status"] == "success":
        data = result_data["data"]
        
        # Process transcript for meeting insights
        transcript = data["transcript"]
        
        return {
            "transcript": transcript,
            "duration": data["duration"],
            "confidence": data["confidence"],
            "cost": data["cost"],
            "word_count": len(transcript.split()),
            "estimated_speakers": transcript.count(":") + 1  # Simple speaker estimation
        }
    
    return {"error": result_data["error"]}
```

## Error Handling

### Common Error Scenarios
1. **File Not Found**
   ```json
   {"error": "Audio file not found: /path/to/missing.wav"}
   ```

2. **Unsupported Format**
   ```json
   {"error": "Unsupported audio format. Please use WAV, MP3, M4A, FLAC, or OGG"}
   ```

3. **Audio Too Long**
   ```json
   {"error": "Audio duration exceeds recommended limit"}
   ```

4. **Network/Service Error**
   ```json
   {"error": "ISA audio service temporarily unavailable"}
   ```

5. **Low Quality Audio**
   ```json
   {"error": "Audio quality too low for reliable transcription"}
   ```

### Error Handling Best Practices
```python
# Always check response status
result = await mcp_client.call_tool("transcribe_audio", params)
response = json.loads(result)

if response["status"] == "success":
    # Process successful result
    transcript = response["data"]["transcript"]
    confidence = response["data"]["confidence"]
    
    if confidence < 0.8:
        print(f"Warning: Low confidence transcription ({confidence:.2f})")
    
    print(f"Transcription: {transcript}")
    print(f"Cost: ${response['data']['cost']:.6f}")
else:
    # Handle error
    print(f"Transcription failed: {response['error']}")
    
    # Check if it's a temporary error worth retrying
    if "temporarily unavailable" in response["error"]:
        # Implement retry logic
        pass
```

## Best Practices

### Audio Quality
1. **Use high-quality recordings** with minimal background noise
2. **Ensure clear speech** - avoid overlapping speakers when possible
3. **Optimal duration** - 30 seconds to 30 minutes for best results
4. **Consistent volume** - normalize audio levels before processing

### Performance Optimization
1. **Specify language** when known to improve accuracy and speed
2. **Use appropriate file formats** - WAV for quality, MP3 for efficiency
3. **Batch similar requests** to optimize API usage
4. **Cache results** for repeated transcription of the same audio

### Cost Management
1. **Monitor cost information** in responses
2. **Preprocess audio** to remove silence and optimize duration
3. **Use appropriate quality settings** for your accuracy requirements
4. **Consider audio compression** for large files

### Security and Privacy
1. **Handle audio data securely** - files are processed but not stored permanently
2. **Use HTTPS URLs** for remote audio files
3. **Consider data retention** policies for transcripts
4. **Audit audio content** before processing sensitive materials

## Testing

Run the comprehensive test suite:

```bash
python tools/services/intelligence_service/tools/tests/test_audio.py
```

**Expected Results:**
```
==================================================
TEST SUMMARY
==================================================
Tests Passed: 5/5
Basic Audio Transcription Functionality: PASS
Language Support: PASS  
Audio Feature Information: PASS
Parameter Validation: PASS
AudioAnalyzer Integration: PASS

Success Rate: 100.0%
```

## Troubleshooting

### Audio Issues
- **Low confidence scores**: Check audio quality and language settings
- **Incomplete transcription**: Verify audio format and encoding
- **No speech detected**: Audio may be too quiet or contain no speech

### Transcription Issues
- **Wrong language detected**: Specify language parameter explicitly
- **Poor accuracy**: Consider audio quality, background noise, speaker clarity
- **Missing words**: May indicate audio quality or model limitations

### Performance Issues
- **Slow processing**: Check audio file size and network connectivity
- **High costs**: Review audio duration and optimize file sizes
- **Timeout errors**: Large files may need to be split into segments

## Summary

The Audio Tools provide a focused, production-ready solution for audio transcription through MCP integration. Key benefits include:

- **Primary Feature**: High-quality speech-to-text transcription
- **High Accuracy**: ISA service integration with state-of-the-art models
- **Flexible Input**: Support for files, URLs, and various audio formats
- **Detailed Results**: Rich transcription data with confidence scores and metadata
- **Cost Tracking**: Transparent cost information for all operations
- **Language Support**: Multiple languages with automatic detection
- **Error Handling**: Comprehensive error reporting and recovery
- **Easy Integration**: Simple MCP tool interface for any client
- **Future-Ready**: Placeholder features for advanced audio analysis

Use this tool as the primary audio transcription interface for your MCP applications. The focus is on reliable, cost-effective speech-to-text conversion with plans for future advanced audio analysis features.