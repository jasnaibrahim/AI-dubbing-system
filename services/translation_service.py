"""
Translation service using OpenAI API for multi-language support
"""
import openai
from typing import List, Dict, Any, Optional
import logging
import json
from config import config

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for translating text using OpenAI API"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'es', 'fr', 'de')
            source_language: Source language code (default: 'auto' for auto-detection)
            
        Returns:
            Translated text
        """
        try:
            target_lang_name = config.LANGUAGE_NAMES.get(target_language, target_language)
            
            if source_language == "auto":
                prompt = f"""
                Translate the following text to {target_lang_name}. 
                Maintain the original tone, style, and meaning. 
                If the text is already in {target_lang_name}, return it as is.
                
                Text to translate:
                {text}
                
                Translation:
                """
            else:
                source_lang_name = config.LANGUAGE_NAMES.get(source_language, source_language)
                prompt = f"""
                Translate the following text from {source_lang_name} to {target_lang_name}.
                Maintain the original tone, style, and meaning.
                
                Text to translate:
                {text}
                
                Translation:
                """
            
            logger.info(f"Using OpenAI model: {config.OPENAI_MODEL}")
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": f"Translate the following text to {target_lang_name}. Return only the translation, no explanations."},
                    {"role": "user", "content": text}
                ],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0
            )
            
            translated_text = response.choices[0].message.content.strip()

            # Clean up common LLM response patterns
            unwanted_patterns = [
                "Here is the translation:",
                "Here's the translation:",
                "The translation is:",
                "Translation:",
                "Translated:",
                "The text appears to be",
                "Here is the",
                "This translates to:",
                "In English:",
                "In Spanish:",
                "In French:",
                "The word means:",
                "This means:"
            ]

            for pattern in unwanted_patterns:
                if pattern.lower() in translated_text.lower():
                    # Find the pattern and take everything after it
                    parts = translated_text.split(pattern)
                    if len(parts) > 1:
                        translated_text = parts[-1].strip()
                        break

            # Remove quotes if the entire text is wrapped in them
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1].strip()
            if translated_text.startswith("'") and translated_text.endswith("'"):
                translated_text = translated_text[1:-1].strip()

            logger.info(f"Text translated successfully to {target_language}")
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise
    
    def translate_transcript_segments(self, segments: List[Dict[str, Any]], target_language: str) -> List[Dict[str, Any]]:
        """
        Translate transcript segments while preserving timing information
        
        Args:
            segments: List of transcript segments with timing
            target_language: Target language code
            
        Returns:
            List of translated segments with preserved timing
        """
        try:
            logger.info(f"Translating {len(segments)} transcript segments to {target_language}")

            # Filter out empty/silence segments before processing
            filtered_segments = []
            empty_segments = 0

            for segment in segments:
                if isinstance(segment, dict):
                    text = segment.get('text', '').strip()
                    # Skip empty segments, silence markers, and very short segments
                    if text and text != '-' and len(text) > 1:
                        filtered_segments.append(segment)
                    else:
                        empty_segments += 1
                elif hasattr(segment, 'text'):
                    text = segment.text.strip()
                    if text and text != '-' and len(text) > 1:
                        filtered_segments.append(segment)
                    else:
                        empty_segments += 1
                else:
                    # Keep non-standard segments for safety
                    filtered_segments.append(segment)

            logger.info(f"📊 Filtered segments: {len(filtered_segments)} valid, {empty_segments} empty/silence segments removed")

            # Log all original transcript segments (filtered)
            logger.info("=" * 80)
            logger.info("📝 VALID TRANSCRIPT SEGMENTS (after filtering):")
            logger.info("=" * 80)
            for i, segment in enumerate(filtered_segments):
                if isinstance(segment, dict):
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', 0)
                    text = segment.get('text', '')
                    logger.info(f"[{i+1:2d}] {start_time:6.2f}s - {end_time:6.2f}s: {text}")
                elif hasattr(segment, 'text'):
                    start_time = getattr(segment, 'start', 0)
                    end_time = getattr(segment, 'end', 0)
                    text = segment.text
                    logger.info(f"[{i+1:2d}] {start_time:6.2f}s - {end_time:6.2f}s: {text}")
                else:
                    logger.info(f"[{i+1:2d}] {str(segment)}")
            logger.info("=" * 80)

            # Use filtered segments for translation
            segments = filtered_segments

            translated_segments = []

            # Process segments individually to avoid LLM formatting issues
            for segment in segments:
                try:
                    # Extract text from segment
                    if isinstance(segment, dict) and 'text' in segment:
                        original_text = segment['text']
                    elif hasattr(segment, 'text'):
                        original_text = segment.text
                    else:
                        original_text = str(segment)

                    # Skip empty texts
                    if not original_text.strip():
                        continue

                    # Translate individual segment
                    translated_text = self.translate_text(original_text, target_language)

                    # Clean up any unwanted formatting from LLM
                    translated_text = translated_text.strip()
                    # Remove common LLM response patterns
                    if translated_text.startswith(("Here's", "The translation", "Translated:", "Translation:")):
                        lines = translated_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith(("Here's", "The translation", "Translated:", "Translation:", "-", "*")):
                                translated_text = line
                                break

                    # Create translated segment
                    translated_segment = segment.copy() if isinstance(segment, dict) else {
                        'start': getattr(segment, 'start', 0),
                        'end': getattr(segment, 'end', 0),
                        'text': getattr(segment, 'text', str(segment))
                    }
                    translated_segment['text'] = translated_text
                    translated_segment['original_text'] = original_text
                    translated_segments.append(translated_segment)

                except Exception as e:
                    logger.error(f"Failed to translate segment '{original_text}': {e}")
                    # Keep original segment if translation fails
                    translated_segment = segment.copy() if isinstance(segment, dict) else {
                        'start': getattr(segment, 'start', 0),
                        'end': getattr(segment, 'end', 0),
                        'text': getattr(segment, 'text', str(segment))
                    }
                    translated_segment['original_text'] = original_text
                    translated_segments.append(translated_segment)
            
            # Log all translated segments
            logger.info("=" * 80)
            logger.info(f"🌍 TRANSLATED SEGMENTS ({target_language.upper()}):")
            logger.info("=" * 80)
            for i, segment in enumerate(translated_segments):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                original_text = segment.get('original_text', '')
                translated_text = segment.get('text', '')
                logger.info(f"[{i+1:2d}] {start_time:6.2f}s - {end_time:6.2f}s:")
                logger.info(f"     Original: {original_text}")
                logger.info(f"     Translated: {translated_text}")
                logger.info("")
            logger.info("=" * 80)

            logger.info(f"Successfully translated {len(translated_segments)} segments")
            return translated_segments
            
        except Exception as e:
            logger.error(f"Failed to translate transcript segments: {str(e)}")
            raise
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language code
        """
        try:
            prompt = f"""
            Detect the language of the following text and return only the ISO 639-1 language code (e.g., 'en', 'es', 'fr').
            
            Text:
            {text[:500]}  # Limit text for efficiency
            
            Language code:
            """
            
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a language detection expert. Return only the ISO 639-1 language code."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            detected_language = response.choices[0].message.content.strip().lower()
            logger.info(f"Detected language: {detected_language}")
            return detected_language
            
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            return "en"  # Default to English
    
    def improve_translation_for_speech(self, text: str, target_language: str) -> str:
        """
        Improve translation specifically for speech synthesis

        Args:
            text: Text to improve
            target_language: Target language code

        Returns:
            Improved text for speech synthesis
        """
        # DISABLED: Speech optimization is causing LLM to respond with instructions
        # instead of optimizing the actual text. Returning original text for now.
        logger.info(f"Speech optimization disabled - using original text for {target_language}")
        return text
