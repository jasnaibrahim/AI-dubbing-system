# Deployment Guide

This guide covers different deployment options for the AI Dubbing Application.

## Local Development

### Prerequisites
- Python 3.8+
- API keys for VideoDB, ElevenLabs, and OpenAI

### Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run: `python main.py`

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  ai-dubbing:
    build: .
    ports:
      - "8000:8000"
    environment:
      - VIDEODB_API_KEY=${VIDEODB_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./temp:/app/temp
```

## Cloud Deployment

### AWS EC2
1. Launch EC2 instance (t3.medium or larger)
2. Install Docker
3. Clone repository
4. Set environment variables
5. Run with Docker Compose

### Google Cloud Run
1. Build container image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Set environment variables
5. Configure scaling

### Heroku
1. Create Heroku app
2. Set environment variables
3. Deploy using Git
4. Scale dynos as needed

## Production Considerations

### Security
- Use environment variables for API keys
- Enable HTTPS
- Implement rate limiting
- Add authentication if needed

### Performance
- Use Redis for job queue
- Implement caching
- Use CDN for static files
- Monitor resource usage

### Monitoring
- Set up logging
- Monitor API usage
- Track processing times
- Set up alerts

### Scaling
- Use load balancer
- Implement horizontal scaling
- Use managed databases
- Consider serverless options
