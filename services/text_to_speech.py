import io
from gtts import gTTS

def speak(text, lang):
    code = "hi" if lang == "Hindi" else "en"
    tts = gTTS(text=text, lang=code)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf
