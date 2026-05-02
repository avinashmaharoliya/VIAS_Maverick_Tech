import speech_recognition as sr

recognizer = sr.Recognizer()

def listen():
    with sr.Microphone() as source:
        print("?? Listening...")

        # keep this simple and stable
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        recognizer.pause_threshold = 1.5
        try:
            audio = recognizer.listen(
                source,
                timeout=5,              # wait for speech start
                phrase_time_limit=6     # max speaking time
            )
        except sr.WaitTimeoutError:
            print("? No speech detected")
            return ""

    try:
        text = recognizer.recognize_google(audio).lower()
        print("??", text)
        return text

    except sr.UnknownValueError:
        print("? Could not understand audio")
        return ""

    except sr.RequestError as e:
        print("? API error:", e)
        return ""
    
def parse_command(text):

    if not text:
        return (None, None)

    text = text.lower().strip()
    # ===== NAVIGATION =====
    if "navigate" in text:

        for loc in ["jaydeva", "home", "college"]:
            if loc in text:
                return ("navigate", loc)

        return ("navigate", None)
    # CALL
    if "call" in text:
        return ("call", None)

    # MESSAGE
    if "message" in text:
        return ("message", text)

    # GROQ / DESCRIBE
    if any(x in text for x in ["what", "describe", "any", "door", "where", "how", "many","does","say"]):
        return ("describe", text)

    # FALL OK
    if any(x in text for x in ["ok", "okay", "i am ok","fine","i am fine"]):
        return ("ok", None)

    return (None, text)