import speech_recognition as sr

r = sr.Recognizer()
with sr.Microphone() as mic:
    print("Say something…")
    r.adjust_for_ambient_noise(mic, duration=0.5)
    audio = r.listen(mic)

try:
    text = r.recognize_google(audio, language="ar-EG")  # "en-US" for English
    print("You said:", text)
except sr.UnknownValueError:
    print("Could not understand audio")
except sr.RequestError as e:
    print("API error:", e)