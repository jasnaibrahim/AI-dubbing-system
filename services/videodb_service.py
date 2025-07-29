"""
VideoDB service for video processing and management
"""
import videodb
from videodb import MediaType
from videodb.asset import VideoAsset, AudioAsset
from videodb.timeline import Timeline
from typing import Optional, Dict, Any, List
import logging
import tempfile
import os
import subprocess
import requests
from config import config

logger = logging.getLogger(__name__)

class VideoDBService:
    """Service for interacting with VideoDB API"""

    def __init__(self):
        """Initialize VideoDB connection"""
        if not config.VIDEODB_API_KEY:
            raise ValueError("VIDEODB_API_KEY is required")

        self.conn = videodb.connect(api_key=config.VIDEODB_API_KEY)
        self.collection = self.conn.get_collection()

    def upload_video(self, url: str):
        """
        Upload video from URL (YouTube or direct link)

        Args:
            url: Video URL to upload

        Returns:
            VideoDB Video object
        """
        try:
            logger.info(f"Uploading video from URL: {url}")
            video = self.conn.upload(url)
            logger.info(f"Video uploaded successfully. ID: {video.id}")
            return video
        except Exception as e:
            logger.error(f"Failed to upload video: {str(e)}")
            raise
    
    def get_video_transcript(self, video) -> Dict[str, Any]:
        """
        Extract transcript from video

        Args:
            video: VideoDB Video object

        Returns:
            Dictionary containing transcript data
        """
        try:
            logger.info(f"Indexing video for transcript extraction: {video.id}")
            
            # Index the video for spoken words
            video.index_spoken_words()
            
            # Get transcript with timestamps
            transcript_json = video.get_transcript()
            transcript_text = video.get_transcript_text()

            # Log detailed transcript information
            logger.info("=" * 80)
            logger.info("🎤 RAW TRANSCRIPT EXTRACTION RESULTS:")
            logger.info("=" * 80)
            logger.info(f"Video ID: {video.id}")
            logger.info(f"Total segments: {len(transcript_json) if transcript_json else 0}")
            logger.info(f"Full transcript text length: {len(transcript_text) if transcript_text else 0} characters")
            logger.info("")
            logger.info("📝 FULL TRANSCRIPT TEXT:")
            logger.info("-" * 40)
            logger.info(transcript_text)
            logger.info("-" * 40)
            logger.info("")

            if transcript_json:
                logger.info("🕐 DETAILED SEGMENTS WITH TIMESTAMPS:")
                logger.info("-" * 60)
                for i, segment in enumerate(transcript_json):
                    if isinstance(segment, dict):
                        start = segment.get('start', 0)
                        end = segment.get('end', 0)
                        text = segment.get('text', '')
                        confidence = segment.get('confidence', 'N/A')
                        logger.info(f"[{i+1:3d}] {start:7.2f}s - {end:7.2f}s | Conf: {confidence} | {text}")
                    else:
                        logger.info(f"[{i+1:3d}] {segment}")
                logger.info("-" * 60)
            logger.info("=" * 80)

            logger.info(f"Transcript extracted successfully for video: {video.id}")

            return {
                "text": transcript_text,
                "segments": transcript_json,
                "video_id": video.id
            }
        except Exception as e:
            logger.error(f"Failed to extract transcript: {str(e)}")
            raise

    def get_video_info(self, video) -> Dict[str, Any]:
        """
        Get video information

        Args:
            video: VideoDB Video object

        Returns:
            Dictionary with video information
        """
        try:
            return {
                "id": video.id,
                "name": getattr(video, 'name', 'Unknown'),
                "duration": getattr(video, 'length', 0),
                "url": video.generate_stream()
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            raise

    def search_video_content(self, video, query: str) -> List[Dict[str, Any]]:

        """
        Search for content within a video

        Args:
            video: VideoDB Video object
            query: Search query

        Returns:
            List of search results with timestamps
        """
        try:
            shots = video.search(query)
            return [
                {
                    "start": shot.start,
                    "end": shot.end,
                    "text": shot.text if hasattr(shot, 'text') else ""
                }
                for shot in shots
            ]
        except Exception as e:
            logger.error(f"Failed to search video content: {str(e)}")
            raise

    def create_dubbed_video(self, original_video, dubbed_audio_url: str) -> str:
        """
        Create dubbed video by replacing audio track

        Args:
            original_video: Original VideoDB Video object
            dubbed_audio_url: URL of the dubbed audio file

        Returns:
            Stream URL of the dubbed video
        """
        try:
            # Handle both video objects and dictionaries for logging
            if hasattr(original_video, 'id'):
                video_id = original_video.id
            elif isinstance(original_video, dict) and 'id' in original_video:
                video_id = original_video['id']
            else:
                video_id = str(original_video)

            logger.info(f"Creating dubbed video for: {video_id}")
            logger.info(f"Audio file path: {dubbed_audio_url}")

            # Upload the dubbed audio
            try:
                dubbed_audio = self.conn.upload(dubbed_audio_url, media_type=MediaType.audio)
                logger.info(f"Audio uploaded successfully: {dubbed_audio.id}")
            except Exception as audio_error:
                logger.error(f"Failed to upload audio: {audio_error}")
                raise

            # Create timeline for dubbing
            timeline = Timeline(self.conn)

            # Add original video (without audio)
            # Use the same video_id we determined earlier
            video_asset = VideoAsset(asset_id=video_id)
            timeline.add_inline(video_asset)

            # Add dubbed audio overlay (replace original audio)
            audio_asset = AudioAsset(asset_id=dubbed_audio.id, disable_other_tracks=True)
            timeline.add_overlay(0, audio_asset)



            # Generate the dubbed video stream
            dubbed_stream = timeline.generate_stream()
            logger.info(f"Dubbed video created successfully: {dubbed_stream}")
            return dubbed_stream
            
        except Exception as e:
            logger.error(f"Failed to create dubbed video: {str(e)}")
            raise
    

    
    def search_video_content(self, video, query: str) -> List[Dict[str, Any]]:
        """
        Search for specific content within a video
        
        Args:
            video: VideoDB Video object
            query: Search query
            
        Returns:
            List of matching segments
        """
        try:
            logger.info(f"Searching video {video.id} for: {query}")
            
            # Ensure video is indexed
            video.index_spoken_words()
            
            # Search for content
            results = video.search(query)
            shots = results.get_shots()
            
            return [
                {
                    "start": shot.start,
                    "end": shot.end,
                    "text": shot.text if hasattr(shot, 'text') else ""
                }
                for shot in shots
            ]
        except Exception as e:
            logger.error(f"Failed to search video content: {str(e)}")
            raise
