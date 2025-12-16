import io
import numpy as np
import soundfile as sf
import librosa
import whisper

model = whisper.load_model("tiny")

def transcribe(audio_bytes):
    audio, sr = sf.read(io.BytesIO(audio_bytes))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio = librosa.resample(audio, sr, 16000)
    return model.transcribe(audio.astype(np.float32))["text"]
