# Automated Walkthrough Generation using Speech Recognition and Computer Vision

## Overview
This project automatically converts software usage videos into narrated step-by-step tutorial walkthroughs. The system processes video recordings, extracts speech instructions, detects visual actions, and generates a structured tutorial with synthesized narration.

The pipeline works fully offline without relying on cloud APIs.

---

## Key Features
- Automatic tutorial generation from screen recordings
- Offline speech-to-text transcription
- Visual step detection using computer vision
- Structured instruction generation
- Text-to-speech narration
- Final tutorial video generation

---

## Technologies Used
- Python
- FastAPI
- React
- FFmpeg
- Whisper (offline speech-to-text)
- OpenCV
- Piper TTS

---

## System Pipeline


Video Upload
↓
Audio Extraction (FFmpeg)
↓
Speech Transcription (Whisper)
↓
Frame Processing (OpenCV)
↓
Step Detection
↓
Instruction Generation
↓
Narration (Piper TTS)
↓
Final Tutorial Video


---

## Project Structure


automated-walkthrough-generator/
│
├── backend/
│ ├── transcription.py
│ ├── step_detector.py
│ └── pipeline.py
│
├── frontend/
│ └── React UI
│
├── video_processing/
│ └── ffmpeg_utils.py
│
├── requirements.txt
└── README.md

---

## Installation
```bash
git clone https://github.com/yourusername/automated-walkthrough-generator.git
cd automated-walkthrough-generator
pip install -r requirements.txt
Running the System

Start backend:

python app.py

Start frontend:

npm install
npm start
Example Workflow

Upload screen recording
Extract audio
Generate transcription
Detect visual actions
Create tutorial narration
Generate final tutorial video


Future Improvements:


Automatic UI element detection
LLM-based instruction generation
Multi-language tutorial generation
Browser extension integration
