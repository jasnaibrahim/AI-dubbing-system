"""
Translation service using OpenAI API for multi-language support
"""
import openai
from typing import List, Dict, Any, Optional
import logging
import json
from config import config
import os

os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),  # Log file
        logging.StreamHandler()               # Also print to console
    ]
)
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

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception("Translation service temporarily unavailable - rate limit exceeded. Please try again later.")
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise Exception("Translation service authentication failed. Please check API key.")
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise
    
    def translate_transcript_segments(self, segments: List[Dict[str, Any]], target_language: str) -> List[Dict[str, Any]]:
        """
        Translate transcript segments while preserving timing information using a batching strategy.

        Args:
            segments: List of transcript segments with timing.
            target_language: Target language code.

        Returns:
            List of translated segments with preserved timing.
        """
        try:
            logger.info(f"Translating {len(segments)} transcript segments to {target_language} using batching.")

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

            # Create a simple mapping: segment index -> text to translate
            texts_to_translate = {}

            for i, segment in enumerate(filtered_segments):
                text = segment.get('text', '').strip()
                # Include ALL non-empty text, even single characters
                if text and text != '-':
                    texts_to_translate[str(i)] = text
                    logger.info(f"📝 Adding segment {i} for translation: '{text}'")

            if not texts_to_translate:
                logger.warning("No valid text segments found to translate.")
                return []

            # Create a JSON string from the dictionary to pass to the model.
            json_input = json.dumps(texts_to_translate, indent=2, ensure_ascii=False)
            target_lang_name = config.LANGUAGE_NAMES.get(target_language, target_language)

            prompt = f"""
Translate the text values in the following JSON object from their original language to {target_lang_name}.
- Respond with a valid JSON object only.
- The JSON object must have the same keys as the input.
- The value for each key in your response should be the translated text corresponding to that key's original text.
- Maintain the original meaning, tone, and style. Do not add any extra explanations or text outside of the JSON object.

Input JSON:
{json_input}
"""

            logger.info(f"Sending batch translation request to OpenAI model: {config.OPENAI_MODEL}")
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": f"You are an expert translation engine. Your task is to translate the text in the provided JSON object to {target_lang_name} and return a valid JSON object."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.1, # Slightly non-zero for better natural language, but still deterministic
                response_format={"type": "json_object"} # Use JSON mode for reliable output
            )

            response_content = response.choices[0].message.content.strip()
            logger.info(f"🤖 OpenAI Response: {response_content[:500]}...")

            # Parse the JSON response from the model
            translated_texts_map = json.loads(response_content)
            logger.info(f"📊 Translated {len(translated_texts_map)} items from OpenAI")

            translated_segments = []

            # Process all filtered segments
            for i, segment in enumerate(filtered_segments):
                original_text = segment.get('text', '').strip()

                # Check if this segment was translated
                if str(i) in translated_texts_map:
                    translated_text = translated_texts_map[str(i)]
                    logger.info(f"✅ Segment {i}: '{original_text}' → '{translated_text}'")
                else:
                    # For untranslated segments, try to translate individually
                    if original_text and original_text != '-' and len(original_text) > 0:
                        logger.warning(f"⚠️ Segment {i} missing from batch translation: '{original_text}'")
                        try:
                            # Fallback: translate individual segment
                            individual_translation = self.translate_text(original_text, target_language)
                            translated_text = individual_translation
                            logger.info(f"🔄 Individual translation: '{original_text}' → '{translated_text}'")
                        except Exception as e:
                            logger.error(f"❌ Individual translation failed for '{original_text}': {e}")
                            translated_text = original_text
                    else:
                        translated_text = original_text

                # Create the new translated segment dictionary
                translated_segment = segment.copy()
                translated_segment['text'] = translated_text
                translated_segment['original_text'] = original_text
                translated_segments.append(translated_segment)

            logger.info(f"✅ Successfully translated {len(translated_segments)} segments in a single batch.")
            return translated_segments

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception("Translation service temporarily unavailable - rate limit exceeded. Please try again later.")
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise Exception("Translation service authentication failed. Please check API key.")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from OpenAI: {e}")
            logger.error(f"Raw model response: {response_content}")
            raise Exception("Translation service returned invalid response format.")
        except Exception as e:
            logger.error(f"Failed to translate transcript segments: {e}")
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
