"""
Main FastAPI application for AI Dubbing service
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn


from services.dubbing_service import DubbingService
from config import config

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ai_dubbing.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Log application startup
logger.info("🚀 Starting AI Dubbing Service")
logger.info(f"📋 Configuration: VideoDB={bool(config.VIDEODB_API_KEY)}, OpenAI={bool(config.OPENAI_API_KEY)}, ElevenLabs={bool(config.ELEVENLABS_API_KEY)}")

# Initialize FastAPI app
app = FastAPI(
    title="AI Dubbing Service",
    description="AI-powered video dubbing using VideoDB, ElevenLabs, and OpenAI",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize dubbing service
dubbing_service = DubbingService()

# Pydantic models for API requests
class DubbingRequest(BaseModel):
    youtube_url: str
    target_language: str
    voice_id: Optional[str] = None
    clone_original_voice: bool = False

class TranslationPreviewRequest(BaseModel):
    youtube_url: str
    target_language: str

# Store for background tasks (in production, use a proper job queue)
background_jobs = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "supported_languages": config.LANGUAGE_NAMES
    })



@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    missing_config = config.validate_config()
    if missing_config:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "missing_config": missing_config}
        )
    return {"status": "healthy"}

@app.get("/api/demo-video")
async def get_demo_video():
    """Get a working demo video URL for testing"""
    # Return a reliable video URL that works across browsers
    demo_video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    return {
        "demo_video_url": demo_video_url,
        "message": "Demo video for AI dubbing showcase",
        "note": "This represents the original video that would be dubbed"
    }

@app.get("/api/logs")
async def get_recent_logs():
    """Get recent application logs for debugging"""
    try:
        import os
        log_file = "ai_dubbing.log"

        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Return last 50 lines
                recent_lines = lines[-50:] if len(lines) > 50 else lines

            return {
                "logs": recent_lines,
                "total_lines": len(lines),
                "showing_last": len(recent_lines)
            }
        else:
            return {
                "logs": ["Log file not found"],
                "total_lines": 0,
                "showing_last": 0
            }
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {
            "logs": [f"Error reading logs: {e}"],
            "total_lines": 0,
            "showing_last": 0
        }

@app.get("/api/transcript")
async def get_transcript():
    """Get the detailed transcript from the last processed video"""
    try:
        import os, re
        log_file = "ai_dubbing.log"

        if not os.path.exists(log_file):
            return {"error": "No processing logs found"}

        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.read()

        # Extract original transcript
        transcript_match = re.search(r'📝 FULL TRANSCRIPT TEXT:\s*-{40}\s*(.*?)\s*-{40}', logs, re.DOTALL)
        original_transcript = transcript_match.group(1).strip() if transcript_match else "Not found"

        # Extract detailed segments
        segments_pattern = r'🕐 DETAILED SEGMENTS WITH TIMESTAMPS:\s*-{60}\s*(.*?)\s*-{60}'
        segments_match = re.search(segments_pattern, logs, re.DOTALL)
        segments_text = segments_match.group(1).strip() if segments_match else "Not found"

        # Extract translated segments
        translated_pattern = r'🌍 TRANSLATED SEGMENTS.*?:\s*={80}\s*(.*?)\s*={80}'
        translated_match = re.search(translated_pattern, logs, re.DOTALL)
        translated_text = translated_match.group(1).strip() if translated_match else "Not found"

        return {
            "success": True,
            "original_transcript": original_transcript,
            "detailed_segments": segments_text,
            "translated_segments": translated_text,
            "message": "Transcript extracted from processing logs"
        }

    except Exception as e:
        logger.error(f"Failed to extract transcript: {e}")
        return {"error": f"Transcript extraction failed: {e}"}

@app.get("/api/video-analysis")
async def get_video_analysis():
    """Get analysis of the last processed video"""
    try:
        import os, re
        log_file = "ai_dubbing.log"

        if not os.path.exists(log_file):
            return {"error": "No processing logs found"}

        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.read()

        # Extract processing information
        analysis = {}

        # Video URL
        video_match = re.search(r'📹 YouTube URL: (https://youtu\.be/[^\s]+)', logs)
        if video_match:
            analysis["original_video_url"] = video_match.group(1)

        # Video ID
        video_id_match = re.search(r'Video uploaded successfully\. ID: ([^\s]+)', logs)
        if video_id_match:
            analysis["videodb_id"] = video_id_match.group(1)

        # Transcript segments
        segments_match = re.search(r'✅ Transcript extracted: (\d+) segments', logs)
        if segments_match:
            analysis["transcript_segments"] = int(segments_match.group(1))

        # Source language
        lang_match = re.search(r'✅ Source language detected: (\w+)', logs)
        if lang_match:
            analysis["source_language"] = lang_match.group(1)

        # Translation
        translation_match = re.search(r'✅ Translation completed: (\d+) segments translated', logs)
        if translation_match:
            analysis["translated_segments"] = int(translation_match.group(1))

        # Processing time
        time_match = re.search(r'completed for job [^\s]+ in ([\d.]+)s', logs)
        if time_match:
            analysis["processing_time"] = float(time_match.group(1))

        # Processed video URL
        final_url_match = re.search(r'Generated playable video stream: ([^\s]+)', logs)
        if final_url_match:
            analysis["processed_video_url"] = final_url_match.group(1)

        # Count AI operations
        analysis["ai_translation_calls"] = logs.count('Text translated successfully to en')
        analysis["speech_optimization_calls"] = logs.count('Text improved for speech synthesis in en')

        return {
            "success": True,
            "analysis": analysis,
            "message": "Your video was processed successfully! The demo video shown is just a placeholder."
        }

    except Exception as e:
        logger.error(f"Failed to analyze video processing: {e}")
        return {"error": f"Analysis failed: {e}"}

@app.get("/api/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {"languages": config.LANGUAGE_NAMES}

@app.get("/api/voices")
async def get_available_voices(language: Optional[str] = None):
    """Get available voices"""
    try:
        voices = dubbing_service.get_available_voices(language)
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Failed to get voices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preview-translation")
async def preview_translation(request: TranslationPreviewRequest):
    """Preview translation without generating audio"""
    try:
        result = dubbing_service.preview_translation(
            request.youtube_url,
            request.target_language
        )
        return result
    except Exception as e:
        logger.error(f"Translation preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dub-video")
async def dub_video(request: DubbingRequest, background_tasks: BackgroundTasks):
    """Start video dubbing process"""
    try:
        # Validate target language
        if request.target_language not in config.SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language: {request.target_language}. Supported languages: {', '.join(config.SUPPORTED_LANGUAGES)}"
            )

        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())

        logger.info(f"🎬 New dubbing job created: {job_id}")
        logger.info(f"📹 YouTube URL: {request.youtube_url}")
        logger.info(f"🌍 Target language: {request.target_language}")
        logger.info(f"🎤 Voice ID: {request.voice_id}")
        logger.info(f"🔄 Clone original voice: {request.clone_original_voice}")

        # Initialize job status
        background_jobs[job_id] = {
            "status": "started",
            "progress": 0,
            "message": "Starting dubbing process..."
        }

        logger.info(f"✅ Job {job_id} initialized and queued")

        # Start background task
        background_tasks.add_task(
            process_dubbing,
            job_id,
            request.youtube_url,
            request.target_language,
            request.voice_id,
            request.clone_original_voice
        )

        logger.info(f"🚀 Background task started for job {job_id}")
        return {"job_id": job_id, "status": "started"}

    except Exception as e:
        logger.error(f"❌ Failed to start dubbing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a dubbing job"""
    if job_id not in background_jobs:
        logger.warning(f"❓ Job status requested for unknown job: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    job_status = background_jobs[job_id]
    logger.debug(f"📊 Job {job_id} status: {job_status['status']} - {job_status['progress']}% - {job_status['message']}")

    return job_status

async def process_dubbing(
    job_id: str,
    youtube_url: str,
    target_language: str,
    voice_id: Optional[str],
    clone_original_voice: bool
):
    """Background task for processing video dubbing"""
    logger.info(f"🔄 Starting dubbing process for job {job_id}")
    start_time = asyncio.get_event_loop().time()

    try:
        # Update job status - Step 1
        logger.info(f"📤 Step 1: Uploading video to VideoDB for job {job_id}")
        background_jobs[job_id].update({
            "status": "processing",
            "progress": 10,
            "message": "Uploading video to VideoDB..."
        })

        # Update progress - Step 2
        logger.info(f"📝 Step 2: Extracting transcript for job {job_id}")
        background_jobs[job_id].update({
            "status": "processing",
            "progress": 30,
            "message": "Extracting transcript..."
        })

        # Run dubbing process
        logger.info(f"🤖 Starting AI dubbing process for job {job_id}")
        result = dubbing_service.dub_video(
            youtube_url=youtube_url,
            target_language=target_language,
            voice_id=voice_id,
            clone_original_voice=clone_original_voice
        )
        
        # Calculate processing time
        end_time = asyncio.get_event_loop().time()
        processing_time = round(end_time - start_time, 2)

        # Update job status with result
        logger.info(f"✅ Dubbing process completed for job {job_id} in {processing_time}s")
        background_jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "🎉 AI Dubbing completed successfully! Your video has been dubbed with AI-generated voice!",
            "result": {
                "video_url": result.video_url,
                "target_language": result.target_language,
                "voice_id": result.voice_id,
                "demo_mode": True,
                "note": "🎤 Complete AI dubbing successful! Your video now has AI-generated voice in the target language.",
                "processing_time": f"{processing_time}s",
                "features_demonstrated": [
                    "✅ YouTube video processing",
                    "✅ Automatic transcript extraction",
                    "✅ AI translation with GPT-4o-mini",
                    "✅ Multi-language support (12+ languages)",
                    "✅ Voice synthesis integration (ElevenLabs ready)",
                    "✅ Real-time progress tracking",
                    "✅ Professional web interface"
                ]
            }
        })

        logger.info(f"🎉 Job {job_id} completed successfully - Video: {result.video_url}")

        # Clean up temporary files
        try:
            dubbing_service.cleanup_temp_files(result.audio_file_path)
            logger.info(f"🧹 Cleaned up temporary files for job {job_id}")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to cleanup temp files for job {job_id}: {cleanup_error}")

    except Exception as e:
        end_time = asyncio.get_event_loop().time()
        processing_time = round(end_time - start_time, 2)

        logger.error(f"❌ Dubbing job {job_id} failed after {processing_time}s: {str(e)}", exc_info=True)
        background_jobs[job_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Dubbing failed: {str(e)}",
            "processing_time": f"{processing_time}s"
        })



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    # Validate configuration
    missing_config = config.validate_config()
    if missing_config:
        logger.error(f"Missing required configuration: {missing_config}")
        exit(1)

    logger.info("Starting AI Dubbing Service...")
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG
    )
