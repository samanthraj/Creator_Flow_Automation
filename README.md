#Creator_Flow_Automation

An autonomous AI-assisted YouTube automation platform that monitors newly uploaded videos, transcribes content locally, generates optimized titles/descriptions/thumbnails using LLMs, and automatically updates YouTube metadata through APIs.

## Features

- Automatic detection of newly uploaded YouTube videos
- Local audio transcription using OpenAI Whisper
- AI-generated viral title suggestions
- AI-generated YouTube descriptions and tags
- Automated thumbnail generation pipeline
- Thumbnail critic loop with retry optimization
- YouTube API integration for automatic publishing updates
- Workflow automation for creator productivity
- Persistent logging and processed-video tracking
- Context-aware content generation

---

# Workflow Architecture

Upload Detection  
↓  
Audio Extraction using yt-dlp  
↓  
Whisper Transcription (Local AI)  
↓  
Groq LLaMA Content Generation  
↓  
Thumbnail Generation Pipeline  
↓  
Thumbnail Critic & Retry Loop  
↓  
YouTube Metadata Update via API  

---

# Technologies Used

## AI & Automation
- Python
- OpenAI Whisper
- Groq API (LLaMA 3.3 70B)
- Prompt Engineering
- Workflow Automation

## Media Processing
- Pillow
- Pollinations AI
- yt-dlp
- FFmpeg

## Backend & APIs
- YouTube Data API v3
- REST APIs
- OAuth Authentication

---

# Key Engineering Concepts

- AI Workflow Orchestration
- Autonomous Content Optimization
- Retry/Critic Loop Systems
- Polling Architecture
- Persistent State Management
- Caching Optimization
- Modular System Design
- Local + Cloud AI Hybrid Architecture

---

# Example Capabilities

## Metadata Automation
- Generates 5 optimized viral title candidates
- Selects best-performing title
- Creates SEO-aware descriptions
- Generates hashtags and tags automatically

## Thumbnail System
- AI-generated cinematic backgrounds
- Dynamic face compositing
- Automated background removal
- Contrast-aware text placement
- Readability optimization using critic loop

---

# Performance Optimizations

- Whisper model loaded globally for faster runtime performance
- Cached background removal for repeated thumbnail generation
- Retry-based thumbnail quality improvement pipeline

---

# Folder Structure

```bash
youtubeagent/
│
├── agent.py
├── thumbnails/
├── logs/
├── models/
├── temp/
├── credentials/
├── my_photos/
└── README.md
