from fastapi import APIRouter, HTTPException
import speech_recognition as sr

router = APIRouter(tags=["Speech-to-Text"])

@router.get("/speech-to-text/mic")
def speech_to_text_mic():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as mic:
            r.adjust_for_ambient_noise(mic, duration=1)
            print("🎤 Listening... speak now!")
            audio = r.listen(mic, timeout=5, phrase_time_limit=10)

        text = r.recognize_google(audio, language="en-US")  # change to "ar-EG" for Arabic
        return {"transcription": text}

    except sr.WaitTimeoutError:
        raise HTTPException(status_code=408, detail="No speech detected (timeout).")
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Speech not understood.")
    except sr.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Google API error: {e}")