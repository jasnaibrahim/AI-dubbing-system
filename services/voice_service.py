"""
Voice cloning and audio generation service using ElevenLabs API
"""
import requests
import tempfile
import os
from typing import List, Dict, Any
import logging
from config import config

logger = logging.getLogger(__name__)

class VoiceService:
    """Service for voice cloning and audio generation using ElevenLabs"""
    
    def __init__(self):
        """Initialize ElevenLabs service"""
        self.base_url = "https://api.elevenlabs.io/v1"
        self._update_api_key()

    def _update_api_key(self):
        """Update API key from config (allows for dynamic updates)"""
        if not config.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is required")

        self.api_key = config.ELEVENLABS_API_KEY
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices from ElevenLabs
        
        Returns:
            List of available voices with their details
        """
        try:
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            voices_data = response.json()
            voices = voices_data.get("voices", [])

            # Add gender and age info to voice names for better selection
            for voice in voices:
                labels = voice.get("labels", {})
                gender = labels.get("gender", "unknown")
                age = labels.get("age", "unknown")
                original_name = voice.get("name", "Unknown")

                # Enhance voice name with gender/age info
                voice["display_name"] = f"{original_name} ({gender}, {age})"
                voice["gender"] = gender
                voice["age"] = age

            logger.info(f"Retrieved {len(voices)} available voices")
            return voices
            
        except Exception as e:
            logger.error(f"Failed to get available voices: {str(e)}")
            logger.info("🎭 Falling back to demo voices for hackathon demo")
            # Return demo voices for development/demo
            return [
                {
                    "voice_id": "demo_multilingual_1",
                    "name": "Demo Multilingual Voice",
                    "category": "demo",
                    "description": "Demo voice for AI dubbing showcase"
                },
                {
                    "voice_id": "demo_english_1",
                    "name": "Demo English Voice",
                    "category": "demo",
                    "description": "Demo voice for English content"
                }
            ]
    
    def clone_voice_from_audio(self, audio_file_path: str, voice_name: str, description: str = "") -> str:
        """
        Clone a voice from audio sample
        
        Args:
            audio_file_path: Path to audio file for voice cloning
            voice_name: Name for the cloned voice
            description: Description of the voice
            
        Returns:
            Voice ID of the cloned voice
        """
        try:
            url = f"{self.base_url}/voices/add"
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'files': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
                }
                data = {
                    'name': voice_name,
                    'description': description
                }
                headers = {"xi-api-key": self.api_key}
                
                response = requests.post(url, files=files, data=data, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                voice_id = result.get("voice_id")
                
                logger.info(f"Voice cloned successfully. Voice ID: {voice_id}")
                return voice_id
                
        except Exception as e:
            logger.error(f"Failed to clone voice: {str(e)}")
            raise
    
    def generate_speech(self, text: str, voice_id: str, model_id: str = "eleven_multilingual_v2") -> bytes:
        """
        Generate speech from text using specified voice

        Args:
            text: Text to convert to speech
            voice_id: ID of the voice to use
            model_id: ElevenLabs model ID to use

        Returns:
            Audio data as bytes
        """
        try:
            # Refresh API key to ensure we have the latest one
            self._update_api_key()

            url = f"{self.base_url}/text-to-speech/{voice_id}"

            data = {
                "text": text[:1000],  # Limit text length for demo
                "model_id": model_id,
                "voice_settings": config.ELEVENLABS_VOICE_SETTINGS
            }

            logger.info(f"🎤 Generating speech with voice {voice_id} and model {model_id}")
            logger.info(f"🔊 Voice settings: {config.ELEVENLABS_VOICE_SETTINGS}")
            logger.info(f"🔑 Using API key: {self.api_key[:20]}...")
            logger.info(f"📡 Request URL: {url}")

            response = requests.post(url, json=data, headers=self.headers)

            logger.info(f"📊 Response status: {response.status_code}")

            if response.status_code == 401:
                logger.error("ElevenLabs API key is invalid or expired")
                logger.error(f"📄 Response body: {response.text}")
                raise Exception("ElevenLabs API authentication failed. Please check your API key.")
            elif response.status_code == 422:
                logger.error(f"Invalid voice ID: {voice_id}")
                logger.error(f"📄 Response body: {response.text}")
                raise Exception(f"Voice ID {voice_id} is not valid. Please check available voices.")
            elif response.status_code != 200:
                logger.error(f"ElevenLabs API error: {response.status_code}")
                logger.error(f"📄 Response body: {response.text}")

            response.raise_for_status()

            logger.info(f"Speech generated successfully for voice {voice_id}: {len(response.content)} bytes")
            return response.content

        except Exception as e:
            logger.error(f"Failed to generate speech: {str(e)}")
            raise


    
    def generate_speech_with_timestamps(self, segments: List[Dict[str, Any]], voice_id: str) -> str:
        """
        Generate speech for multiple segments and combine them

        Args:
            segments: List of text segments with timing information
            voice_id: ID of the voice to use

        Returns:
            Path to the generated audio file
        """
        try:
            logger.info(f"🎤 Generating speech for {len(segments)} segments using voice: {voice_id}")
            logger.info(f"🔊 Voice ID being used: {voice_id}")

            # Log all segments that will be synthesized
            logger.info("=" * 80)
            logger.info("🎤 VOICE SYNTHESIS INPUT SEGMENTS:")
            logger.info("=" * 80)
            for i, segment in enumerate(segments):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                text = segment.get('text', '')
                logger.info(f"[{i+1:2d}] {start_time:6.2f}s - {end_time:6.2f}s: {text}")
            logger.info("=" * 80)

            # Create temporary file for combined audio
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_audio_file.close()

            # For now, we'll concatenate all text and generate single audio
            # In a production system, you'd want to handle timing more precisely
            segment_texts = []
            for segment in segments:
                text = segment.get('text', '').strip()
                # Clean up any separator artifacts that might have leaked through
                text = text.replace('---SEGMENT---', '').replace('###SEPARATOR###', '').strip()
                if text:  # Only add non-empty text
                    segment_texts.append(text)

            combined_text = " ".join(segment_texts)

            logger.info("🗣️ COMBINED TEXT FOR VOICE SYNTHESIS:")
            logger.info("-" * 60)
            logger.info(combined_text)
            logger.info("-" * 60)
            logger.info(f"Total characters: {len(combined_text)}")
            logger.info(f"Estimated speech duration: ~{len(combined_text) / 10:.1f} seconds")

            try:
                # Check if this is a demo voice ID
                if voice_id.startswith("demo_"):
                    logger.warning(f"Demo voice ID detected: {voice_id}")
                    logger.info("🎭 Voice synthesis unavailable - using demo mode")
                    return "DEMO_MODE_NO_AUDIO"

                # Generate speech for combined text
                logger.info(f"🎤 Attempting to generate speech with voice: {voice_id}")
                audio_data = self.generate_speech(combined_text, voice_id)

                # Write audio data to file
                with open(temp_audio_file.name, 'wb') as f:
                    f.write(audio_data)

                logger.info(f"✅ Combined audio saved to: {temp_audio_file.name}")
                return temp_audio_file.name

            except Exception as api_error:
                logger.warning(f"❌ ElevenLabs API failed: {api_error}")
                logger.info("🎭 Voice synthesis unavailable - falling back to demo mode")
                return "DEMO_MODE_NO_AUDIO"

        except Exception as e:
            logger.error(f"Failed to generate speech with timestamps: {str(e)}")
            raise
    
    def get_voice_info(self, voice_id: str) -> Dict[str, Any]:
        """
        Get information about a specific voice
        
        Args:
            voice_id: ID of the voice
            
        Returns:
            Voice information
        """
        try:
            url = f"{self.base_url}/voices/{voice_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            voice_info = response.json()
            logger.info(f"Retrieved info for voice {voice_id}")
            return voice_info
            
        except Exception as e:
            logger.error(f"Failed to get voice info: {str(e)}")
            raise
    
    def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a cloned voice
        
        Args:
            voice_id: ID of the voice to delete
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.base_url}/voices/{voice_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Voice {voice_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete voice: {str(e)}")
            return False
    
    def get_default_voice_id(self, language: str = "en") -> str:
        """
        Get a default voice ID for the specified language

        Args:
            language: Language code

        Returns:
            Default voice ID for the language
        """
        try:
            # First, try to get available voices to use real voice IDs
            voices = self.get_available_voices()

            if voices and not voices[0].get("voice_id", "").startswith("demo_"):
                # Try to find a male voice for the language first
                male_voices = [v for v in voices if v.get("gender") == "male"]

                if male_voices:
                    # Use the first male voice available
                    male_voice = male_voices[0]
                    voice_id = male_voice.get("voice_id")
                    voice_name = male_voice.get("name")
                    logger.info(f"Using male voice: {voice_id} ({voice_name})")
                    return voice_id

                # If no male voices, use the first available voice
                first_voice_id = voices[0].get("voice_id")
                logger.info(f"Using first available voice: {first_voice_id} ({voices[0].get('name')})")
                return first_voice_id

            # If no voices available, use actual working voice IDs from your account
            # Using male voices as defaults for variety
            language_defaults = {
                "en": "IKne3meq5aSn9XLyUdCD",  # Charlie (young male)
                "es": "JBFqnCBsd6RMkjVDRZzb",  # George (middle-aged male)
                "fr": "N2lVS1w4EtoT3dr4eOWO",  # Callum (middle-aged male)
                "de": "TX3LPaxmHKxFdv7VOQHJ",  # Liam (young male)
                "it": "bIHbv24MWmeRgasZH58o",  # Will (young male)
                "pt": "cjVigY5qzO86Huf0OWal",  # Eric (middle-aged male)
                "ru": "iP95p4xoKVk53GoZ742B",  # Chris (middle-aged male)
                "ja": "nPczCjzI2devNBz1zQrb",  # Brian (middle-aged male)
                "ko": "onwK4e9ZLuTAKqWW03F9",  # Daniel (middle-aged male)
                "zh": "pqHfZKP75CvOlQylNhV4",  # Bill (old male)
                "hi": "IKne3meq5aSn9XLyUdCD",  # Charlie (fallback)
                "ar": "onwK4e9ZLuTAKqWW03F9"   # Daniel (middle-aged male)
            }

            default_voice_id = language_defaults.get(language, "EXAVITQu4vr4xnSDxMaL")
            logger.info(f"Using default voice for {language}: {default_voice_id}")
            return default_voice_id

        except Exception as e:
            logger.error(f"Failed to get default voice: {str(e)}")
            logger.info("🎭 Using demo voice for hackathon showcase")
            # Ultimate fallback to demo voice
            return "demo_multilingual_1"  # Demo voice for showcase
