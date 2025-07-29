# API Documentation

## Overview
The AI Dubbing Service provides REST API endpoints for video dubbing functionality.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API uses API keys configured in environment variables. No additional authentication is required for endpoints.

## Endpoints

### Health Check
Check the health status of the service.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy"
}
```

### Get Supported Languages
Retrieve list of supported languages for dubbing.

**Endpoint:** `GET /api/languages`

**Response:**
```json
{
  "languages": {
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
}
```

### Get Available Voices
Retrieve list of available voices for speech synthesis.

**Endpoint:** `GET /api/voices`

**Query Parameters:**
- `language` (optional): Filter voices by language code

**Response:**
```json
{
  "voices": [
    {
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "name": "Rachel",
      "category": "premade",
      "description": "Young Adult Female"
    }
  ]
}
```

### Preview Translation
Generate a translation preview without creating audio.

**Endpoint:** `POST /api/preview-translation`

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "target_language": "es"
}
```

**Response:**
```json
{
  "original_transcript": {
    "text": "Hello, welcome to our video...",
    "segments": [
      {
        "start": 0.0,
        "end": 3.5,
        "text": "Hello, welcome to our video"
      }
    ],
    "video_id": "video_123"
  },
  "translated_transcript": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Hola, bienvenidos a nuestro video",
      "original_text": "Hello, welcome to our video"
    }
  ],
  "source_language": "en",
  "target_language": "es",
  "video_id": "video_123"
}
```

### Start Video Dubbing
Initiate the video dubbing process.

**Endpoint:** `POST /api/dub-video`

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "target_language": "es",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "clone_original_voice": false
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started"
}
```

### Check Job Status
Monitor the progress of a dubbing job.

**Endpoint:** `GET /api/job-status/{job_id}`

**Response (Processing):**
```json
{
  "status": "processing",
  "progress": 45,
  "message": "Generating dubbed audio..."
}
```

**Response (Completed):**
```json
{
  "status": "completed",
  "progress": 100,
  "message": "Dubbing completed successfully!",
  "result": {
    "video_url": "https://stream.videodb.io/v/abc123",
    "target_language": "es",
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  }
}
```

**Response (Failed):**
```json
{
  "status": "failed",
  "progress": 0,
  "message": "Dubbing failed: Invalid YouTube URL"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Job not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limits
- No rate limits currently implemented
- Consider implementing rate limiting for production use

## SDK Usage Examples

### Python
```python
import requests

# Start dubbing
response = requests.post('http://localhost:8000/api/dub-video', json={
    'youtube_url': 'https://www.youtube.com/watch?v=example',
    'target_language': 'es'
})
job_id = response.json()['job_id']

# Check status
status_response = requests.get(f'http://localhost:8000/api/job-status/{job_id}')
print(status_response.json())
```

### JavaScript
```javascript
// Start dubbing
const response = await fetch('/api/dub-video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        youtube_url: 'https://www.youtube.com/watch?v=example',
        target_language: 'es'
    })
});
const { job_id } = await response.json();

// Check status
const statusResponse = await fetch(`/api/job-status/${job_id}`);
const status = await statusResponse.json();
console.log(status);
```

## Webhooks (Future Enhancement)
Future versions may support webhooks for job completion notifications:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "video_url": "https://stream.videodb.io/v/abc123"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```
