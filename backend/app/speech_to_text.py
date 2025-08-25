from fastapi import APIRouter, HTTPException
import speech_recognition as sr

router = APIRouter(tags=["Speech-to-Text"])

@router.get("/speech-to-text/mic")

def recognize_speech():
    r = sr.Recognizer()

    # Use microphone as source
    with sr.Microphone() as source:
        print("🎤 Say something (English or Arabic)...")
        r.adjust_for_ambient_noise(source)  
        audio =  r.listen(source, timeout=5, phrase_time_limit=7)


    # Try recognizing first in English, then fallback to Arabic
    try:
        text = r.recognize_google(audio, language="en-US")
        print("✅ Recognized (English):", text)
    except:
        try:
            text = r.recognize_google(audio, language="ar-EG")
            print("✅ Recognized (Arabic):", text)
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            text = ""
        except sr.RequestError as e:
            print("⚠️ Could not request results; {0}".format(e))
            text = ""

    return text


if __name__ == "__main__":
    recognize_speech()
