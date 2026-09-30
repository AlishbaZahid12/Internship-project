# Sight Assist

**A voice-first AI assistant for blind and visually impaired users.**

Sight Assist helps users with two everyday problems:

1. **Understanding their surroundings**: say *"describe"* and the app tells you what objects are around you and where (left, center, right).
2. **Checking medicines and food for safety**: say *"scan"* and the app reads a product label, identifies the product, and compares it against **your own stored allergies and medical conditions**. It then speaks a verdict: **safe**, **risky** or **unknown**.

The whole experience works by voice in **English and Urdu**. A Streamlit web dashboard is included for sighted caregivers to review and edit profiles and scan history.

> Built as an internship project. See `Sight_Assist_Project_Report.docx` for the full report.

---

## How It Works

| Feature | Pipeline |
| --- | --- |
| **Scene description** | Camera frame → YOLOv8 object detection → left/center/right position logic → spoken sentence |
| **Product scanning** | Camera frame → EasyOCR → knowledge lookup (OpenFDA → Open Food Facts → local JSON) → embedding-based relevance check → risk check against user profile → spoken verdict → saved to scan history |
| **Voice interface** | Microphone → speech recognition (English, falls back to Urdu) → command router → service → spoken reply in the detected language |

**Verdicts**

- **Safe**: no conflict found between the identified product and the user's profile.
- **Risky**: an ingredient or warning matches a stored allergy or condition; the conflicting item is named aloud.
- **Unknown**: the product could not be identified with confidence. The system never reports "safe" just because it failed to identify something.

**Note on retrieval:** the project uses sentence-transformer embeddings (all-MiniLM-L6-v2) for semantic matching and for rejecting false matches from garbled OCR. Verdicts are produced by rule-based logic; a generative LLM is not part of the current pipeline (see Future Work).

---

## Architecture

The code is layered so components can be swapped without rewriting the app:

- **Presentation**: `main.py` (voice + camera loop) and `app.py` (Streamlit dashboard)
- **Services**: auth, profile, vision, risk, scan and voice logic (`services/`)
- **Repositories**: one class per database table (`database/repositories/`)
- **Interfaces**: abstract classes for the detector, OCR, embedding model, speech-to-text and text-to-speech
- **Data**: MySQL (users, profiles, allergies, conditions, scan history) plus local JSON knowledge bases (`data/`)

## Tech Stack

Python 3.12 · OpenCV · Ultralytics YOLOv8 · EasyOCR · sentence-transformers · scikit-learn · OpenFDA API · Open Food Facts API · MySQL · SpeechRecognition · gTTS · pygame · deep-translator · Streamlit · pandas · bcrypt · python-dotenv

---

## Setup

**Requirements:** Python 3.12, MySQL server, a webcam, a microphone and an internet connection (speech recognition, text-to-speech, translation and the live APIs need it).

```bash
# 1. Clone the repository
git clone https://github.com/AlishbaZahid12/Internship-project.git
cd Internship-project

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
```

**Database**

1. Start MySQL and create a database (for example `sight_assist`).
2. Run the schema file: `database/schema.sql`.
3. Create a `.env` file in the project root with your database settings (use the variable names your `core` config expects):

```env
DB_HOST=localhost
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=sight_assist
```

> The `.env` file is git-ignored and must never be committed.

---

## Running the Project

**Voice + camera assistant (main application)**

```bash
python main.py
```

Signup, login, profile setup and all commands are done by voice. Say **"one / two / three"** for menu options.

| Voice command | What it does |
| --- | --- |
| `describe` | Captures a frame and describes nearby objects and their positions |
| `scan` | Reads a medicine/food label and speaks a safety verdict for your profile |

**Web dashboard (for sighted users / caregivers)**

```bash
streamlit run app.py
```

Then open **http://localhost:8501**. From the dashboard you can:

- Log in and view or edit age, gender, allergies and medical conditions
- Review scan history with colour-coded verdicts
- Launch the voice assistant

Changes made in the dashboard show up immediately in the voice assistant, and vice versa, because both use the same service layer.

---

## Project Structure

```
blind_assist/
├── main.py               # Voice + camera assistant entry point
├── app.py                # Streamlit dashboard entry point
├── core/                 # Config and logging
├── data/                 # Local medicine and food knowledge bases (JSON)
├── database/             # Connection, schema.sql, repositories
├── rag/                  # Embeddings, knowledge base, OpenFDA / Open Food Facts clients
├── services/             # Auth, profile, vision, risk, scan services
├── voice/                # Speech recognition and text-to-speech engines
└── logs/                 # Runtime logs (git-ignored)
```

---

## Testing

Testing was done through manual end-to-end runs, with standalone scripts for each component (camera, embeddings, OpenFDA client). Verified scenarios include:

- Voice signup/login with PIN confirmation and duplicate-username rejection
- Profile creation and editing of allergies and conditions
- Scene description with correct left/center/right placement
- Scanning a real paracetamol package, with correct identification via the local knowledge base
- Risky verdict when ingredients match a stored allergy; safe verdict when no conflict exists
- "Unknown" verdict when OCR text is too garbled to identify
- Scan history logging, visible by voice and in the dashboard
- Automatic English/Urdu switching

## Known Limitations

- Speech recognition accuracy depends on microphone quality and background noise.
- OCR struggles with curved, damaged or poorly lit packaging; garbled text leads to an "unknown" verdict.
- OpenFDA only covers US-registered drugs; Pakistani brands rely on the small local JSON database.
- An internet connection is required (no offline mode).
- Verdicts are a decision aid, **not medical advice**. Users should always confirm with a doctor or pharmacist.

## Future Work

- LLM-based explanation layer that explains a verdict in plain language, grounded only in retrieved label text, while the rule-based logic keeps the final safety decision
- Emergency-contact alerts through a paid SMS gateway with proper registration for Pakistani numbers
- Larger regional medicine and food databases
- Barcode scanning with audio guidance
- Improved OCR pre-processing and multi-frame scanning

---

## Author

**Alishba Zahid**: internship project, 2026
