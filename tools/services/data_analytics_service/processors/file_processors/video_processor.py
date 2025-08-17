#!/usr/bin/env python3
"""
Video Processor

Handles video processing including frame analysis, object detection, 
and audio extraction for video files.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import cv2
import numpy as np

# Import will be done dynamically to avoid circular imports

logger = logging.getLogger(__name__)

@dataclass
class VideoFrame:
    """Video frame with analysis"""
    frame_number: int
    timestamp: float
    objects: List[Dict[str, Any]]
    description: str
    key_frame: bool
    motion_score: float

@dataclass
class ObjectDetection:
    """Object detection result"""
    object_class: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    tracking_id: Optional[str] = None

@dataclass
class VideoAnalysisResult:
    """Complete video analysis result"""
    duration: float
    frame_count: int
    fps: float
    resolution: Tuple[int, int]
    key_frames: List[VideoFrame]
    object_summary: Dict[str, Any]
    audio_analysis: Optional[Dict[str, Any]]
    scene_changes: List[float]
    motion_analysis: Dict[str, Any]
    processing_time: float

class VideoProcessor:
    """
    Video processor for comprehensive video analysis.
    
    Capabilities:
    - Frame-by-frame analysis
    - Object detection and tracking
    - Scene change detection
    - Motion analysis
    - Audio extraction and analysis
    - Key frame extraction
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # Initialize processors lazily to avoid circular imports
        self._audio_processor = None
        self._vlm_processor = None
        
        # Video processing settings
        self.key_frame_interval = self.config.get('key_frame_interval', 30)  # frames
        self.max_frames_to_analyze = self.config.get('max_frames_to_analyze', 100)
        self.scene_change_threshold = self.config.get('scene_change_threshold', 0.3)
        self.motion_threshold = self.config.get('motion_threshold', 0.1)
        
        # Object detection settings
        self.object_detection_model = self.config.get('object_detection_model', 'yolo')
        self.detection_confidence = self.config.get('detection_confidence', 0.5)
    
    async def analyze_video(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Comprehensive video analysis.
        
        Args:
            file_path: Path to video file
            options: Analysis options
            
        Returns:
            Complete video analysis results
        """
        try:
            options = options or {}
            
            # Validate file
            if not Path(file_path).exists():
                return {'error': 'Video file not found', 'success': False}
            
            # Get video info
            video_info = await self._get_video_info(file_path)
            
            # Extract and analyze key frames
            frame_analysis = await self._analyze_frames(file_path, options)
            
            # Detect objects across frames
            object_analysis = await self._analyze_objects(file_path, options)
            
            # Analyze motion and scene changes
            motion_analysis = await self._analyze_motion(file_path, options)
            
            # Extract and analyze audio if present
            audio_analysis = None
            if options.get('analyze_audio', True) and video_info.get('has_audio'):
                audio_analysis = await self._extract_and_analyze_audio(file_path, options)
            
            # Combine results
            combined_result = await self._combine_video_analysis(
                video_info, frame_analysis, object_analysis, motion_analysis, audio_analysis
            )
            
            return {
                'file_path': file_path,
                'analysis': combined_result,
                'processing_time': combined_result.processing_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_key_frames(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract key frames from video.
        
        Args:
            file_path: Path to video file
            options: Extraction options
            
        Returns:
            Key frame extraction results
        """
        try:
            options = options or {}
            
            key_frames = await self._extract_key_frames(file_path, options)
            
            return {
                'file_path': file_path,
                'key_frames': key_frames,
                'frame_count': len(key_frames),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Key frame extraction failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def detect_objects(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect objects in video frames.
        
        Args:
            file_path: Path to video file
            options: Detection options
            
        Returns:
            Object detection results
        """
        try:
            options = options or {}
            
            result = await self._analyze_objects(file_path, options)
            
            return {
                'file_path': file_path,
                'objects': result.get('objects', []),
                'object_summary': result.get('object_summary', {}),
                'processing_time': result.get('processing_time', 0.0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def analyze_motion(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze motion in video.
        
        Args:
            file_path: Path to video file
            options: Motion analysis options
            
        Returns:
            Motion analysis results
        """
        try:
            options = options or {}
            
            result = await self._analyze_motion(file_path, options)
            
            return {
                'file_path': file_path,
                'motion_analysis': result,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Motion analysis failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def _get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic video file information."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {'error': 'Could not open video file'}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # Check for audio track (simplified)
            has_audio = True  # Would check actual audio track
            
            return {
                'duration': duration,
                'frame_count': frame_count,
                'fps': fps,
                'resolution': (width, height),
                'has_audio': has_audio,
                'file_size': Path(file_path).stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Video info extraction failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_frames(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze video frames using VLM."""
        import time
        start_time = time.time()
        
        try:
            # Extract key frames
            key_frames = await self._extract_key_frames(file_path, options)
            
            # Analyze each key frame with VLM
            analyzed_frames = []
            for frame_info in key_frames:
                if 'frame_path' in frame_info:
                    # Use intelligence service for frame analysis
                    try:
                        from tools.services.intelligence_service.vision.image_analyzer import ImageAnalyzer
                        analyzer = ImageAnalyzer()
                        vlm_result = await analyzer.analyze(
                            image=frame_info['frame_path'],
                            prompt="Analyze this video frame comprehensively. Describe what you see, identify objects, and provide context."
                        )
                        
                        if vlm_result.success:
                            frame_info['vlm_analysis'] = {
                                'description': vlm_result.response,
                                'model_used': vlm_result.model_used
                            }
                    except Exception as e:
                        logger.warning(f"VLM analysis failed for frame: {e}")
                        frame_info['vlm_analysis'] = {'description': 'Analysis unavailable'}
                    
                    analyzed_frames.append(frame_info)
            
            return {
                'analyzed_frames': analyzed_frames,
                'frame_count': len(analyzed_frames),
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            return {
                'analyzed_frames': [],
                'frame_count': 0,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _extract_key_frames(self, file_path: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key frames from video."""
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return []
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            key_frames = []
            frame_interval = max(1, frame_count // self.max_frames_to_analyze)
            
            frame_num = 0
            while frame_num < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                timestamp = frame_num / fps
                
                # Save frame temporarily for analysis
                temp_frame_path = f"/tmp/frame_{frame_num}.jpg"
                cv2.imwrite(temp_frame_path, frame)
                
                # Calculate motion score (simplified)
                motion_score = await self._calculate_frame_motion_score(frame, frame_num)
                
                key_frames.append({
                    'frame_number': frame_num,
                    'timestamp': timestamp,
                    'frame_path': temp_frame_path,
                    'motion_score': motion_score,
                    'key_frame': frame_num % self.key_frame_interval == 0
                })
                
                frame_num += frame_interval
                
                if len(key_frames) >= self.max_frames_to_analyze:
                    break
            
            cap.release()
            return key_frames
            
        except Exception as e:
            logger.error(f"Key frame extraction failed: {e}")
            return []
    
    async def _analyze_objects(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze objects in video frames."""
        import time
        start_time = time.time()
        
        try:
            # Mock object detection - would use actual object detection model
            objects_by_frame = []
            object_summary = {
                'total_objects': 0,
                'unique_objects': set(),
                'object_counts': {},
                'object_timeline': []
            }
            
            # Extract frames for object detection
            key_frames = await self._extract_key_frames(file_path, options)
            
            for frame_info in key_frames:
                frame_objects = await self._detect_objects_in_frame(frame_info)
                objects_by_frame.append({
                    'frame_number': frame_info['frame_number'],
                    'timestamp': frame_info['timestamp'],
                    'objects': frame_objects
                })
                
                # Update summary
                for obj in frame_objects:
                    object_summary['total_objects'] += 1
                    object_summary['unique_objects'].add(obj['object_class'])
                    
                    obj_class = obj['object_class']
                    object_summary['object_counts'][obj_class] = object_summary['object_counts'].get(obj_class, 0) + 1
            
            # Convert set to list for JSON serialization
            object_summary['unique_objects'] = list(object_summary['unique_objects'])
            
            return {
                'objects': objects_by_frame,
                'object_summary': object_summary,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Object analysis failed: {e}")
            return {
                'objects': [],
                'object_summary': {},
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _detect_objects_in_frame(self, frame_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect objects in a single frame."""
        try:
            # Mock object detection - would use actual model like YOLO
            mock_objects = [
                {
                    'object_class': 'person',
                    'confidence': 0.9,
                    'bbox': (100, 100, 200, 300),
                    'tracking_id': 'person_1'
                },
                {
                    'object_class': 'car',
                    'confidence': 0.8,
                    'bbox': (300, 200, 400, 300),
                    'tracking_id': 'car_1'
                }
            ]
            
            return mock_objects
            
        except Exception as e:
            logger.error(f"Object detection in frame failed: {e}")
            return []
    
    async def _analyze_motion(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze motion in video."""
        import time
        start_time = time.time()
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return {'error': 'Could not open video file'}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            motion_scores = []
            scene_changes = []
            prev_frame = None
            
            # Analyze motion for sample frames
            frame_interval = max(1, frame_count // 100)  # Sample 100 frames
            
            for frame_num in range(0, frame_count, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                timestamp = frame_num / fps
                
                if prev_frame is not None:
                    # Calculate motion score
                    motion_score = await self._calculate_motion_between_frames(prev_frame, frame)
                    motion_scores.append({
                        'timestamp': timestamp,
                        'motion_score': motion_score
                    })
                    
                    # Detect scene changes
                    if motion_score > self.scene_change_threshold:
                        scene_changes.append(timestamp)
                
                prev_frame = frame.copy()
            
            cap.release()
            
            # Calculate motion statistics
            if motion_scores:
                avg_motion = sum(score['motion_score'] for score in motion_scores) / len(motion_scores)
                max_motion = max(score['motion_score'] for score in motion_scores)
                min_motion = min(score['motion_score'] for score in motion_scores)
            else:
                avg_motion = max_motion = min_motion = 0.0
            
            return {
                'motion_scores': motion_scores,
                'scene_changes': scene_changes,
                'motion_statistics': {
                    'average_motion': avg_motion,
                    'max_motion': max_motion,
                    'min_motion': min_motion,
                    'scene_change_count': len(scene_changes)
                },
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Motion analysis failed: {e}")
            return {
                'motion_scores': [],
                'scene_changes': [],
                'motion_statistics': {},
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _calculate_frame_motion_score(self, frame: np.ndarray, frame_num: int) -> float:
        """Calculate motion score for a single frame."""
        try:
            # Simple motion estimation based on edge density
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            motion_score = np.sum(edges > 0) / edges.size
            
            return float(motion_score)
            
        except Exception as e:
            logger.error(f"Motion score calculation failed: {e}")
            return 0.0
    
    async def _calculate_motion_between_frames(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate motion between two frames."""
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # Calculate frame difference
            diff = cv2.absdiff(gray1, gray2)
            
            # Calculate motion score
            motion_score = np.sum(diff > 30) / diff.size
            
            return float(motion_score)
            
        except Exception as e:
            logger.error(f"Motion calculation failed: {e}")
            return 0.0
    
    async def _extract_and_analyze_audio(self, file_path: str, options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and analyze audio from video."""
        try:
            # Extract audio from video (would use ffmpeg)
            audio_path = f"/tmp/extracted_audio_{Path(file_path).stem}.wav"
            
            # Mock audio extraction
            logger.info(f"Audio extraction not fully implemented for {file_path}")
            
            # Analyze extracted audio
            # audio_result = await self.audio_processor.analyze_audio(audio_path, options)
            # return audio_result
            
            return {
                'transcript': 'Mock audio transcript',
                'speakers': [],
                'emotions': [],
                'processing_time': 0.0
            }
            
        except Exception as e:
            logger.error(f"Audio extraction and analysis failed: {e}")
            return None
    
    async def _combine_video_analysis(self, video_info: Dict[str, Any],
                                    frame_analysis: Dict[str, Any],
                                    object_analysis: Dict[str, Any],
                                    motion_analysis: Dict[str, Any],
                                    audio_analysis: Optional[Dict[str, Any]]) -> VideoAnalysisResult:
        """Combine all video analysis results."""
        try:
            # Create VideoFrame objects
            key_frames = []
            for frame_data in frame_analysis.get('analyzed_frames', []):
                key_frames.append(VideoFrame(
                    frame_number=frame_data['frame_number'],
                    timestamp=frame_data['timestamp'],
                    objects=frame_data.get('objects', []),
                    description=frame_data.get('vlm_analysis', {}).get('description', ''),
                    key_frame=frame_data.get('key_frame', False),
                    motion_score=frame_data.get('motion_score', 0.0)
                ))
            
            # Calculate total processing time
            total_processing_time = (
                frame_analysis.get('processing_time', 0) +
                object_analysis.get('processing_time', 0) +
                motion_analysis.get('processing_time', 0)
            )
            
            if audio_analysis:
                total_processing_time += audio_analysis.get('processing_time', 0)
            
            return VideoAnalysisResult(
                duration=video_info.get('duration', 0.0),
                frame_count=video_info.get('frame_count', 0),
                fps=video_info.get('fps', 0.0),
                resolution=video_info.get('resolution', (0, 0)),
                key_frames=key_frames,
                object_summary=object_analysis.get('object_summary', {}),
                audio_analysis=audio_analysis,
                scene_changes=motion_analysis.get('scene_changes', []),
                motion_analysis=motion_analysis.get('motion_statistics', {}),
                processing_time=total_processing_time
            )
            
        except Exception as e:
            logger.error(f"Video analysis combination failed: {e}")
            return VideoAnalysisResult(
                duration=0.0,
                frame_count=0,
                fps=0.0,
                resolution=(0, 0),
                key_frames=[],
                object_summary={},
                audio_analysis=None,
                scene_changes=[],
                motion_analysis={},
                processing_time=0.0
            )
    
    def get_supported_formats(self) -> List[str]:
        """Get supported video formats."""
        return ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm']
    
    def set_key_frame_interval(self, interval: int):
        """Set key frame extraction interval."""
        self.key_frame_interval = max(1, interval)
    
    def set_max_frames_to_analyze(self, max_frames: int):
        """Set maximum number of frames to analyze."""
        self.max_frames_to_analyze = max(10, max_frames)
    
    def set_detection_confidence(self, confidence: float):
        """Set object detection confidence threshold."""
        self.detection_confidence = max(0.0, min(1.0, confidence))