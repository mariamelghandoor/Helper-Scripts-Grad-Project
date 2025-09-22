# Helper Scripts for Startup Analysis

A collection of scripts to scrape, clean, and analyze startup-related content from various sources.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

Required API keys:
- GEMINI_API_KEY: Google's Gemini API
- YOUTUBE_API_KEY: YouTube Data API v3
- SERPER_API_KEY: Serper API for web search
- GROQ_API_KEY: Groq API for validation

## Project Structure

```
Helper-Scripts-Grad-Project/
├── Data/                    # All data storage
│   ├── Cleaned/            # Cleaned text files
│   ├── Scraped/           # Raw scraped content
│   ├── Schemas/           # JSON schema outputs
│   └── Validated_Schemas/ # Validated JSON schemas
├── Scripts/                # Source code
└── main.py                # Main entry point
```

## Usage

The project supports two main pipelines:

1. YouTube Pipeline - Scrapes and analyzes startup-related YouTube content:
```bash
python main.py youtube --query "startup success stories"
```

2. Website Pipeline - Scrapes and analyzes startup-related web content:
```bash
python main.py website --query "startup failure case studies"
```

Example queries:
- "Famous startup success stories and lessons"
- "Startup failure case studies"
- "In-depth analysis of successful startups"
- "Failed business models explained"
- "Biographies of tech entrepreneurs"

## Output

The pipeline generates:
1. Raw scraped content in `Data/Scraped/`
2. Cleaned text in `Data/Cleaned/`
3. Structured JSON data in `Data/Schemas/`
4. Validated schemas in `Data/Validated_Schemas/`
