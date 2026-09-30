# Sight Assist — Blind Assistance Project

An AI system for blind users that:
1. **Describes surroundings** on voice command ("describe") using computer vision.
2. **Scans medicine/food products** ("scan") and warns the user if it conflicts
   with their stored allergies or medical conditions, using OCR + embeddings (RAG).

## Setup (one-time)

### Mac/Linux
```bash
bash setup.sh
```

### Windows
```bat
setup.bat
```

This creates a `venv/` folder and installs everything in `requirements.txt`.

## After setup

1. **Configure your database** — open `config.py` and set your MySQL password.
2. **Create the database + tables**:
   ```bash
   python database/db_connection.py
   ```
   You should see: `✅ Database 'blind_assist_db' and tables initialized successfully.`
3. **Activate the environment** whenever you come back to work on this:
   - Mac/Linux: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate.bat`
4. **Run the app** (once built): `streamlit run app.py`

## Project Structure
```
blind_assist/
├── app.py                  # Streamlit main app (Phase 4)
├── config.py                # DB + model settings
├── requirements.txt
├── setup.sh / setup.bat     # environment setup scripts
├── database/
│   ├── schema.sql           # table definitions
│   ├── db_connection.py     # connection + init script
│   └── models.py            # all DB CRUD functions
├── auth/
│   └── auth_handler.py      # signup/login (bcrypt hashed passwords)
├── vision/                  # scene description + product scanning (Phase 2)
├── voice/                   # speech-to-text / text-to-speech (Phase 2)
├── rag/                     # embeddings + risk reasoning (Phase 3)
├── data/                    # seed knowledge base for RAG
└── utils/                   # shared helper functions
```

## Requirements
- Python 3.10+
- MySQL Server installed and running locally
- A working webcam and microphone (for the vision/voice modules)
