import speech_recognition as sr

recognizer = sr.Recognizer()

def listen():
    with sr.Microphone() as source:
        audio = recognizer.listen(source, phrase_time_limit=3)

    try:
        return recognizer.recognize_google(audio).lower()
    except:
        return ""


def parse_command(text):
    if "call" in text:
        return "call", text

    if "message" in text:
        return "message", text

    if "around" in text or "see" in text:
        return "scene", text

    if "i am okay" in text:
        return "ok", text

    return None, text