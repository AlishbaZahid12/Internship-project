"""
Main entry point: fully voice-driven signup/login, profile management
(view/edit/add/remove), scan history, and live describe/scan commands.
Every menu recognizes both English and Urdu words. The reply language
(via VoiceService) automatically follows whichever language was last
spoken, handled in voice_service.py / speech_recognition_engine.py.

Run directly with:      python -m main
Run pre-logged-in with: python -m main --user-id 3
"""

import argparse
import queue
import threading
import time

import cv2

from services.auth_service import AuthService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.vision_service import VisionService
from services.risk_service import RiskService
from services.voice_service import VoiceService
from vision.yolo_detector import YoloObjectDetector
from vision.easyocr_engine import EasyOCREngine
from voice.hybrid_tts_engine import HybridTextToSpeech
from voice.speech_recognition_engine import GoogleSpeechToText
from rag.embedding_model import SentenceTransformerEmbedding
from rag.knowledge_base import KnowledgeBase
from core.exceptions import AuthenticationError, DuplicateUserError, ValidationError
from utils.helpers import extract_number, has_word
from config import APP_CONFIG


def print_header(text):
    print("\n" + "=" * 50)
    print(text)
    print("=" * 50)


def ask_word_choice(voice: VoiceService, prompt: str, options: dict, retries: int = 3):
    """
    options: {"login": ["login", "log", "URDU_WORD"], ...}
    Speaks the prompt, listens, and returns the matching key, or None.
    """
    for _ in range(retries):
        heard = voice.ask_text(prompt, retries=1)
        if not heard:
            continue
        for key, words in options.items():
            if has_word(heard, *words):
                return key
        voice.speak("Sorry, I didn't catch that.")
    return None


# ---------------------------------------------------------
# SIGNUP / LOGIN / EXIT
# ---------------------------------------------------------

def voice_signup_or_login(auth: AuthService, voice: VoiceService):
    print_header("SIGHT ASSIST")

    while True:
        choice = ask_word_choice(
            voice,
            "Welcome to Sight Assist. Say signup, login, or exit.",
            {
                "signup": ["signup", "sign", "\u0633\u0627\u0626\u0646", "\u0627\u06a9\u0627\u0624\u0646\u0679"],
                "login": ["login", "log", "\u0644\u0627\u06af"],
                "exit": ["exit", "quit", "\u0628\u0627\u06c1\u0631", "\u0628\u0646\u062f"],
            },
        )

        if choice == "signup":
            user = do_voice_signup(auth, voice)
            if user:
                return user
        elif choice == "login":
            user = do_voice_login(auth, voice)
            if user:
                return user
        elif choice == "exit":
            voice.speak("Goodbye.")
            return "EXIT"


def do_voice_signup(auth: AuthService, voice: VoiceService):
    full_name = voice.ask_confirmed_text("What is your full name?")
    username = voice.ask_confirmed_text("Please choose a username.")
    pin = voice.ask_pin("Please speak a 4 digit PIN to use as your password.", digit_length=4)

    if not full_name or not username or not pin:
        voice.speak("Signup could not be completed. Let's try again from the start.")
        return None

    try:
        user = auth.signup(full_name, username, pin)
        voice.speak(f"Account created successfully. Welcome, {user['full_name']}.")
        return user
    except (DuplicateUserError, ValidationError) as e:
        voice.speak(f"Signup failed. {str(e)}")
        return None


def do_voice_login(auth: AuthService, voice: VoiceService):
    username = voice.ask_confirmed_text("Please say your username.")
    pin = voice.ask_pin("Please speak your 4 digit PIN.", digit_length=4)

    if not username or not pin:
        voice.speak("Login could not be completed. Let's try again.")
        return None

    try:
        user = auth.login(username, pin)
        voice.speak(f"Welcome back, {user['full_name']}.")
        return user
    except AuthenticationError as e:
        voice.speak(f"Login failed. {str(e)}")
        return None


# ---------------------------------------------------------
# SHARED PROFILE HELPERS
# ---------------------------------------------------------

def _ask_age(voice: VoiceService):
    for _ in range(3):
        text = voice.ask_confirmed_text("Please say your age.")
        age = extract_number(text) if text else None
        if age and 0 < age <= 130:
            return age
        voice.speak("That didn't sound like a valid age.")
    return None


def _get_items(profile_service: ProfileService, user_id: int, kind: str) -> list:
    data = profile_service.get_full_profile(user_id)
    if kind == "allergy":
        return [a["allergy_name"] for a in data["allergies"]]
    return data["conditions"]


def _add_item(profile_service, user_id, kind, name):
    if kind == "allergy":
        profile_service.add_allergy(user_id, name)
    else:
        profile_service.add_condition(user_id, name)


def _update_item(profile_service, user_id, kind, old, new):
    if kind == "allergy":
        profile_service.update_allergy(user_id, old, new)
    else:
        profile_service.update_condition(user_id, old, new)


def _remove_item(profile_service, user_id, kind, name):
    if kind == "allergy":
        profile_service.remove_allergy(user_id, name)
    else:
        profile_service.remove_condition(user_id, name)


# ---------------------------------------------------------
# FIRST-TIME PROFILE SETUP
# ---------------------------------------------------------

def run_voice_profile_setup(profile_service: ProfileService, voice: VoiceService, user_id: int):
    if profile_service.get_full_profile(user_id)["profile"]:
        return  # already set up

    voice.speak("Let's set up your medical profile.")

    age = _ask_age(voice)
    if age is None:
        voice.speak("I couldn't get your age. You can add it later from profile management.")

    gender = voice.ask_confirmed_text("Please say your gender.")

    try:
        profile_service.save_profile(user_id, age, gender)
    except ValidationError as e:
        voice.speak(f"There was a problem saving your profile: {e}")
        return

    while voice.ask_yes_no("Would you like to add an allergy?"):
        allergy = voice.ask_confirmed_text("Please say the allergy name.")
        if allergy:
            profile_service.add_allergy(user_id, allergy)
            voice.speak(f"Added {allergy} to your allergies.")

    while voice.ask_yes_no("Would you like to add a medical condition?"):
        condition = voice.ask_confirmed_text("Please say the medical condition.")
        if condition:
            profile_service.add_condition(user_id, condition)
            voice.speak(f"Added {condition} to your medical conditions.")

    voice.speak("Your profile is now set up.")


# ---------------------------------------------------------
# PROFILE MANAGEMENT (view / edit / add / remove)
# ---------------------------------------------------------

def run_profile_management(profile_service: ProfileService, voice: VoiceService, user_id: int):
    voice.speak("Profile management.")

    while True:
        choice = ask_word_choice(
            voice,
            "Say profile to hear it, personal for age and gender, allergies, conditions, or back.",
            {
                "profile": ["profile", "hear", "\u067e\u0631\u0648\u0641\u0627\u0626\u0644"],
                "personal": ["personal", "age", "gender", "\u0630\u0627\u062a\u06cc", "\u0639\u0645\u0631"],
                "allergies": ["allergy", "allergies", "\u0627\u0644\u0631\u062c\u06cc"],
                "conditions": ["condition", "conditions", "\u0628\u06cc\u0645\u0627\u0631\u06cc"],
                "back": ["back", "exit", "done", "\u0648\u0627\u067e\u0633"],
            },
        )

        if choice == "profile":
            _speak_full_profile(profile_service, voice, user_id)
        elif choice == "personal":
            _edit_personal_details(profile_service, voice, user_id)
        elif choice == "allergies":
            _manage_list(profile_service, voice, user_id, "allergy")
        elif choice == "conditions":
            _manage_list(profile_service, voice, user_id, "condition")
        elif choice == "back" or choice is None:
            voice.speak("Returning to the camera.")
            return


def _edit_personal_details(profile_service: ProfileService, voice: VoiceService, user_id: int):
    profile = profile_service.get_full_profile(user_id)["profile"]
    if not profile:
        voice.speak("You don't have a profile yet.")
        return

    choice = ask_word_choice(
        voice, "Say age, gender, or back.",
        {
            "age": ["age", "\u0639\u0645\u0631"],
            "gender": ["gender", "\u062c\u0646\u0633"],
            "back": ["back", "exit", "\u0648\u0627\u067e\u0633"],
        },
    )
    notes = profile["notes"] or ""

    if choice == "age":
        age = _ask_age(voice)
        if age:
            profile_service.save_profile(user_id, age, profile["gender"], notes)
            voice.speak(f"Your age is now {age}.")
    elif choice == "gender":
        gender = voice.ask_confirmed_text("Please say your gender.")
        if gender:
            profile_service.save_profile(user_id, profile["age"], gender, notes)
            voice.speak(f"Your gender is now {gender}.")


def _manage_list(profile_service: ProfileService, voice: VoiceService,
                 user_id: int, kind: str):
    plural = "allergies" if kind == "allergy" else "medical conditions"

    while True:
        choice = ask_word_choice(
            voice, f"Your {plural}. Say add, edit, remove, or back.",
            {
                "add": ["add", "\u0634\u0627\u0645\u0644"],
                "edit": ["edit", "change", "\u062a\u0628\u062f\u06cc\u0644"],
                "remove": ["remove", "delete", "\u06c1\u0679\u0627"],
                "back": ["back", "exit", "\u0648\u0627\u067e\u0633"],
            },
        )

        if choice == "back" or choice is None:
            return

        if choice == "add":
            name = voice.ask_confirmed_text(f"Please say the {kind} name.")
            if name:
                _add_item(profile_service, user_id, kind, name)
                voice.speak(f"Added {name}.")

        elif choice in ("edit", "remove"):
            items = _get_items(profile_service, user_id, kind)
            if not items:
                voice.speak(f"You have no {plural} saved.")
                continue

            index = voice.ask_choice(f"Which {kind}?", items)
            if index is None:
                voice.speak("Cancelled.")
                continue
            old = items[index]

            if choice == "edit":
                new = voice.ask_confirmed_text(f"Please say the new name for {old}.")
                if new:
                    _update_item(profile_service, user_id, kind, old, new)
                    voice.speak(f"Changed {old} to {new}.")
            else:
                if voice.ask_yes_no(f"Remove {old}?"):
                    _remove_item(profile_service, user_id, kind, old)
                    voice.speak(f"Removed {old}.")


def _speak_full_profile(profile_service: ProfileService, voice: VoiceService, user_id: int):
    data = profile_service.get_full_profile(user_id)
    profile = data["profile"]

    if not profile:
        voice.speak("You don't have a profile set up yet.")
        return

    parts = [f"You are {profile['age'] or 'of unknown age'}, {profile['gender']}."]

    if data["allergies"]:
        parts.append("Your allergies are: "
                     + ", ".join(a["allergy_name"] for a in data["allergies"]) + ".")
    else:
        parts.append("You have no allergies on file.")

    if data["conditions"]:
        parts.append("Your medical conditions are: " + ", ".join(data["conditions"]) + ".")
    else:
        parts.append("You have no medical conditions on file.")

    voice.speak(" ".join(parts))


# ---------------------------------------------------------
# SCAN HISTORY
# ---------------------------------------------------------

def speak_scan_history(scan_service: ScanService, voice: VoiceService,
                        user_id: int, limit: int = 5):
    history = scan_service.get_history(user_id, limit=limit)

    if not history:
        voice.speak("You have no scan history yet.")
        return

    voice.speak(f"Here are your last {len(history)} scans.")
    for entry in history:
        item_name = entry["scanned_item_name"] or "an unidentified item"

        if entry["verdict"] == "safe":
            voice.speak(f"{item_name}: marked safe.")
        elif entry["verdict"] == "risky":
            voice.speak(f"{item_name}: marked risky. {entry['reason']}")
        else:
            voice.speak(f"{item_name}: could not be determined.")


# ---------------------------------------------------------
# LIVE CAMERA SESSION
# ---------------------------------------------------------

def voice_listener_thread(voice: VoiceService, command_queue: queue.Queue,
                           stop_event: threading.Event):
    while not stop_event.is_set():
        if voice.is_listener_paused():
            time.sleep(0.2)
            continue

        started = time.time()
        heard = voice.listen(timeout=3, phrase_time_limit=6, quiet=True)
        if not heard:
            continue

        if voice.speech_overlapped(started):
            print(f"[IGNORED - assistant was speaking] '{heard}'")
            continue

        print(f"[COMMAND HEARD] '{heard}'")
        command_queue.put(heard.lower())


def run_camera_session(vision: VisionService, voice: VoiceService,
                        risk_service: RiskService, profile_service: ProfileService,
                        scan_service: ScanService, user_id: int):
    voice.speak("Camera is now live. Say describe, scan, history, profile, or exit.")
    print_header("Camera is live. Voice: describe / scan / history / profile / exit "
                 "(keys d / s / q also work)")

    cap = cv2.VideoCapture(APP_CONFIG.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, APP_CONFIG.camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, APP_CONFIG.camera_height)

    if not cap.isOpened():
        voice.speak("I could not access the camera.")
        return

    command_queue = queue.Queue()
    stop_event = threading.Event()
    threading.Thread(
        target=voice_listener_thread, args=(voice, command_queue, stop_event), daemon=True
    ).start()

    describe_words = ["describe", "\u0628\u06cc\u0627\u0646"]
    scan_words = ["scan", "\u0627\u0633\u06a9\u06cc\u0646"]
    history_words = ["history", "\u062a\u0627\u0631\u06cc\u062e"]
    profile_words = ["profile", "\u067e\u0631\u0648\u0641\u0627\u0626\u0644"]
    exit_words = ["exit", "quit", "\u0628\u0627\u06c1\u0631", "\u0628\u0646\u062f"]

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed.")
            break

        display_frame = cv2.resize(frame, (480, 360))
        cv2.putText(display_frame, "describe / scan / history / profile / exit",
            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow("Sight Assist - Live Camera", display_frame)

        key = cv2.waitKey(1) & 0xFF

        command = None
        try:
            command = command_queue.get_nowait()
        except queue.Empty:
            pass

        if key == ord('q') or (command and has_word(command, *exit_words)):
            voice.speak("Closing camera. Goodbye.")
            break

        elif key == ord('d') or (command and has_word(command, *describe_words)):
            sentence = vision.describe_scene(frame)
            print(f"[DESCRIBE] {sentence}")
            voice.speak(sentence)

        elif key == ord('s') or (command and has_word(command, *scan_words)):
            voice.speak("Reading label, please hold steady.")
            extracted_text = vision.scan_product_label(frame)
            result = risk_service.check_product(user_id, extracted_text)

            if result["verdict"] == "safe":
                message = f"This appears safe for you. {result['reason']}"
            elif result["verdict"] == "risky":
                message = f"Warning! {result['reason']}"
            else:
                message = f"I could not determine safety. {result['reason']}"

            print(f"[SCAN:{result['verdict']}] {message}")
            voice.speak(message)

        elif command and has_word(command, *history_words):
            speak_scan_history(scan_service, voice, user_id)

        elif command and has_word(command, *profile_words):
            with voice.listener_paused():
                run_profile_management(profile_service, voice, user_id)
            while not command_queue.empty():
                command_queue.get_nowait()
            voice.speak("Back to the camera.")

    stop_event.set()
    cap.release()
    cv2.destroyAllWindows()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, default=None,
                        help="Skip voice login and use this already-authenticated user (set by the dashboard).")
    args = parser.parse_args()

    auth = AuthService()
    profile_service = ProfileService()
    scan_service = ScanService()

    tts = HybridTextToSpeech()
    stt = GoogleSpeechToText()
    voice = VoiceService(stt, tts)

    if args.user_id is not None:
        from database.repositories.user_repository import UserRepository
        user = UserRepository().find_by_id(args.user_id)
        if not user:
            print(f"No user found with id {args.user_id}")
            return
        voice.speak(f"Welcome, {user['full_name']}.")
    else:
        user = voice_signup_or_login(auth, voice)
        if user == "EXIT":
            return

    user_id = user["user_id"]
    run_voice_profile_setup(profile_service, voice, user_id)

    print_header("Loading models (this may take a moment)...")
    voice.speak("Loading, please wait.")
    detector = YoloObjectDetector()
    ocr = EasyOCREngine()
    vision = VisionService(detector, ocr)

    embedding_model = SentenceTransformerEmbedding()
    knowledge_base = KnowledgeBase(embedding_model)
    risk_service = RiskService(knowledge_base)

    run_camera_session(vision, voice, risk_service, profile_service, scan_service, user_id)

    print_header("Session ended. Goodbye!")


if __name__ == "__main__":
    main()