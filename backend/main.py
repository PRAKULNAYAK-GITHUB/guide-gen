from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os
import uuid
import subprocess
import json

import whisper
import cv2
import numpy as np


# ---------------- APP SETUP ----------------
app = FastAPI(title="Clueso Clone Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- DIRECTORIES ----------------
VIDEO_DIR = "uploads/videos"
AUDIO_DIR = "uploads/audio"
TRANSCRIPT_DIR = "uploads/transcripts"
SCREENSHOT_DIR = "uploads/screenshots"
STEP_DIR = "uploads/steps"
INSTRUCTION_DIR = "uploads/instructions"
VOICE_DIR = "uploads/voiceovers"

for d in [
    VIDEO_DIR,
    AUDIO_DIR,
    TRANSCRIPT_DIR,
    SCREENSHOT_DIR,
    STEP_DIR,
    INSTRUCTION_DIR,
    VOICE_DIR,
]:
    os.makedirs(d, exist_ok=True)


# ---------------- STATIC FILES ----------------
app.mount(
    "/screenshots",
    StaticFiles(directory=SCREENSHOT_DIR),
    name="screenshots"
)


# ---------------- MODELS ----------------
model = whisper.load_model("small")

PIPER_BIN = "./tools/piper/piper"
PIPER_MODEL = "./tools/voices/en_US-lessac-medium.onnx"


# ---------------- UTILS ----------------
def narration_is_rich(transcript):
    text = transcript.get("text", "").strip()
    return len(text.split()) > 20


# ---------------- STEP DETECTION (SECONDARY) ----------------
def detect_steps(video_path, job_id, threshold=30):
    cap = cv2.VideoCapture(video_path)
    prev_gray = None
    frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            if np.mean(diff) > threshold:
                frames.append(frame_count)
                cv2.imwrite(
                    f"{SCREENSHOT_DIR}/{job_id}_step_{len(frames)}.png",
                    frame
                )

        prev_gray = gray
        frame_count += 1

    cap.release()
    return frames


# ---------------- BUILD STEPS FROM FRAMES ----------------
def build_steps_from_frames(transcript, step_frames, job_id, fps=30):
    segments = transcript.get("segments", [])
    steps = []

    if not segments or not step_frames:
        return []

    for i, frame in enumerate(step_frames):
        start = frame / fps
        end = (
            step_frames[i + 1] / fps
            if i + 1 < len(step_frames)
            else segments[-1]["end"]
        )

        texts = [
            seg["text"]
            for seg in segments
            if seg["end"] >= start and seg["start"] <= end
        ]

        steps.append({
            "step_number": i + 1,
            "raw_text": " ".join(texts).strip(),
            "screenshot": f"{job_id}_step_{i + 1}.png"
        })

    return steps


# ---------------- STORY BUILDER ----------------
TRANSITIONS = ["First", "Next", "Then", "After that", "Finally"]


def infer_action(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["click", "press", "tap"]): return "click"
    if any(k in t for k in ["select", "choose"]): return "select"
    if any(k in t for k in ["type", "enter"]): return "type"
    if any(k in t for k in ["wait", "loading"]): return "wait"
    return "generic"


def build_sentence(action, raw_text):
    base = raw_text.strip()
    if len(base.split()) > 25:
        return base if base.endswith(".") else base + "."

    if action == "click":
        return f"{base}. This involves clicking the relevant button."
    if action == "select":
        return f"{base}. Select the appropriate option as shown."
    if action == "type":
        return f"{base}. Enter the required details."
    if action == "wait":
        return f"{base}. Please wait for processing to complete."

    return base if base.endswith(".") else base + "."


def generate_story_instruction(raw_text, step_number, total_steps):
    raw_text = raw_text.strip()

    if not raw_text:
        sentence = "perform the next action shown on the screen."
    else:
        sentence = build_sentence(infer_action(raw_text), raw_text)

    if step_number == 1:
        prefix = "To begin,"
    elif step_number == total_steps:
        prefix = "Finally,"
    else:
        prefix = TRANSITIONS[min(step_number - 1, len(TRANSITIONS) - 1)] + ","

    return f"Step {step_number}: {prefix} {sentence}"


# ---------------- PIPER VOICEOVER ----------------
def generate_voiceover(instructions, job_id):
    narration = "\n".join(step["instruction"] for step in instructions).strip()
    if not narration:
        return None

    voice_path = f"{VOICE_DIR}/{job_id}.wav"

    subprocess.run(
        [
            PIPER_BIN,
            "--model", PIPER_MODEL,
            "--output_file", voice_path
        ],
        input=narration.encode(),
        check=True
    )

    return voice_path if os.path.exists(voice_path) else None


# ---------------- VIDEO UPLOAD PIPELINE ----------------
@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())

    video_path = f"{VIDEO_DIR}/{job_id}.mp4"
    audio_path = f"{AUDIO_DIR}/{job_id}.wav"

    with open(video_path, "wb") as f:
        f.write(await file.read())

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ],
        check=True
    )

    transcript = model.transcribe(audio_path)
    with open(f"{TRANSCRIPT_DIR}/{job_id}.json", "w") as f:
        json.dump(transcript, f, indent=2)

    # 🔑 PRIORITY: VOICE FIRST
    if narration_is_rich(transcript):
        steps = [{
            "step_number": 1,
            "raw_text": transcript["text"],
            "screenshot": ""
        }]
    else:
        frames = detect_steps(video_path, job_id)
        steps = build_steps_from_frames(transcript, frames, job_id)

    # Absolute fallback
    if not steps:
        steps = [{
            "step_number": 1,
            "raw_text": transcript.get("text", ""),
            "screenshot": ""
        }]

    with open(f"{STEP_DIR}/{job_id}.json", "w") as f:
        json.dump(steps, f, indent=2)

    instructions = []
    for step in steps:
        instructions.append({
            "step_number": step["step_number"],
            "instruction": generate_story_instruction(
                step["raw_text"],
                step["step_number"],
                len(steps)
            ),
            "screenshot": step["screenshot"]
        })

    with open(f"{INSTRUCTION_DIR}/{job_id}.json", "w") as f:
        json.dump(instructions, f, indent=2)

    voice_path = generate_voiceover(instructions, job_id)

    return {
        "job_id": job_id,
        "steps": len(steps),
        "voiceover_file": voice_path,
        "status": "complete"
    }
