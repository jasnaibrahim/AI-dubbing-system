# AI Dubbing / Multi-Language Video Generation

A powerful AI-driven application that automatically dubs videos into multiple languages using VideoDB, ElevenLabs, and OpenAI APIs.

## Features

- 🎥 **YouTube Video Processing**: Direct YouTube link support
- 🌍 **Multi-Language Support**: 12+ languages including English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, Chinese, Hindi, and Arabic
- 🎙️ **AI Voice Cloning**: High-quality voice synthesis using ElevenLabs
- 🤖 **Smart Translation**: Context-aware translation using OpenAI GPT-4
- ⚡ **Fast Processing**: Leverages VideoDB's serverless video infrastructure
- 🎬 **Professional Quality**: Studio-quality dubbing output
- 🌐 **Web Interface**: User-friendly web application

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YouTube URL   │───▶│    VideoDB      │───▶│   Transcript    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Dubbed Video   │◀───│   ElevenLabs    │◀───│   OpenAI GPT-4  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- VideoDB API Key
- ElevenLabs API Key  
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd videodb
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
python main.py
```

5. Open your browser and navigate to `http://localhost:8000`

## API Keys Setup

### VideoDB
1. Visit [VideoDB Console](https://console.videodb.io)
2. Sign up for a free account
3. Get your API key from the dashboard

### ElevenLabs
1. Visit [ElevenLabs](https://elevenlabs.io)
2. Create an account
3. Get your API key from settings

### OpenAI
1. Visit [OpenAI Platform](https://platform.openai.com)
2. Create an account
3. Generate an API key

## Usage

### Web Interface
1. Open the web application
2. Paste a YouTube URL
3. Select target language
4. Choose voice settings
5. Click "Generate Dubbing"
6. Download the dubbed video

### API Usage
```python
from dubbing_service import DubbingService

service = DubbingService()
result = service.dub_video(
    youtube_url="https://www.youtube.com/watch?v=example",
    target_language="es",
    voice_id="optional_voice_id"
)
print(f"Dubbed video URL: {result.video_url}")
```

## Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)
- Hindi (hi)
- Arabic (ar)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue on GitHub.
