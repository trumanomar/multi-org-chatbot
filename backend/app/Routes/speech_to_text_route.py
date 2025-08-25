from fastapi import APIRouter, HTTPException
import speech_recognition as sr

router = APIRouter(tags=["Speech-to-Text"])

@router.get("/speech-to-text/mic")
def recognize_speech():
    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 قول أي حاجة (عربي أو إنجليزي)...")
        r.adjust_for_ambient_noise(source, duration=1)  
        
        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=15)
        except Exception as e:
            print("⚠️ Error while listening:", e)
            return ""

    text = ""
    try:
        text = r.recognize_google(audio, language="ar-EG")
        print("✅ Recognized (Arabic):", text)
    except sr.UnknownValueError:
        try:
            text = r.recognize_google(audio, language="en-US")
            print("✅ Recognized (English):", text)
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
        except sr.RequestError as e:
            print("⚠️ Could not request results;", e)
    except sr.RequestError as e:
        print("⚠️ Could not request results;", e)

    return {"text": text}


if __name__ == "__main__":
    recognize_speech()
