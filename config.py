"""
Configuration module for AI Dubbing Application
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class"""
    
    # API Keys
    VIDEODB_API_KEY = os.getenv("VIDEODB_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Application settings
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # Supported languages
    SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,es,fr,de,it,pt,ru,ja,ko,zh,hi,ar").split(",")
    
    # Language mappings
    LANGUAGE_NAMES = {
        "en": "English",
        "es": "Spanish", 
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "hi": "Hindi",
        "ar": "Arabic"
    }
    
    # ElevenLabs settings
    ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
    ELEVENLABS_VOICE_SETTINGS = {
        "stability": 0.75,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }
    
    # OpenAI settings
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MAX_TOKENS = 4000
    
    # VideoDB settings
    VIDEODB_BASE_URL = "https://api.videodb.io"
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """
        Validate configuration and return list of missing required settings
        
        Returns:
            List of missing configuration keys
        """
        missing = []
        
        if not cls.VIDEODB_API_KEY:
            missing.append("VIDEODB_API_KEY")
        if not cls.ELEVENLABS_API_KEY:
            missing.append("ELEVENLABS_API_KEY")
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
            
        return missing

# Create global config instance
config = Config()
