"""
Streamlit dashboard for Sight Assist.
This is a sighted-user / caregiver dashboard for account setup and
reviewing history - the actual accessible experience for a blind user
is the voice+camera assistant (main.py), launched from here or directly.

Run with: streamlit run app.py
"""

import os
import subprocess
import sys

import pandas as pd
import streamlit as st

from services.auth_service import AuthService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from core.exceptions import AuthenticationError, DuplicateUserError, ValidationError

st.set_page_config(page_title="Sight Assist Dashboard", page_icon="🦯", layout="wide")

auth = AuthService()
profile_service = ProfileService()
scan_service = ScanService()

if "user" not in st.session_state:
    st.session_state.user = None


# ---------------------------------------------------------
# SIDEBAR: LOGIN / SIGNUP
# ---------------------------------------------------------

def render_auth_sidebar():
    st.sidebar.title("Sight Assist")

    if st.session_state.user:
        st.sidebar.success(f"Logged in as {st.session_state.user['full_name']}")
        if st.sidebar.button("Log out"):
            st.session_state.user = None
            st.rerun()
        return

    mode = st.sidebar.radio("Account", ["Login", "Sign up"])

    if mode == "Login":
        with st.sidebar.form("login_form"):
            username = st.text_input("Username")
            pin = st.text_input("4-digit PIN", type="password", max_chars=4)
            submitted = st.form_submit_button("Log in")

        if submitted:
            try:
                user = auth.login(username, pin)
                st.session_state.user = user
                st.rerun()
            except AuthenticationError as e:
                st.sidebar.error(str(e))

    else:
        with st.sidebar.form("signup_form"):
            full_name = st.text_input("Full name")
            username = st.text_input("Choose a username")
            pin = st.text_input("Choose a 4-digit PIN", type="password", max_chars=4)
            submitted = st.form_submit_button("Create account")

        if submitted:
            try:
                user = auth.signup(full_name, username, pin)
                st.session_state.user = user
                st.sidebar.success("Account created.")
                st.rerun()
            except (DuplicateUserError, ValidationError) as e:
                st.sidebar.error(str(e))


# ---------------------------------------------------------
# TAB 1: PROFILE
# ---------------------------------------------------------

def render_profile_tab(user_id: int):
    data = profile_service.get_full_profile(user_id)
    profile = data["profile"]

    st.subheader("Personal details")
    col1, col2 = st.columns(2)
    age = col1.number_input("Age", min_value=0, max_value=130,
                             value=profile["age"] if profile else 0)
    gender = col2.text_input("Gender", value=profile["gender"] if profile else "")

    if st.button("Save personal details"):
        try:
            profile_service.save_profile(user_id, age, gender)
            st.success("Saved.")
            st.rerun()
        except ValidationError as e:
            st.error(str(e))

    st.divider()

    col_a, col_c = st.columns(2)

    with col_a:
        st.subheader("Allergies")
        for a in data["allergies"]:
            row1, row2 = st.columns([4, 1])
            row1.write(f"• {a['allergy_name']} ({a['severity']})")
            if row2.button("Remove", key=f"rm_allergy_{a['allergy_name']}"):
                profile_service.remove_allergy(user_id, a["allergy_name"])
                st.rerun()

        with st.form("add_allergy_form", clear_on_submit=True):
            new_allergy = st.text_input("Add allergy")
            if st.form_submit_button("Add") and new_allergy:
                profile_service.add_allergy(user_id, new_allergy)
                st.rerun()

    with col_c:
        st.subheader("Medical conditions")
        for c in data["conditions"]:
            row1, row2 = st.columns([4, 1])
            row1.write(f"• {c}")
            if row2.button("Remove", key=f"rm_condition_{c}"):
                profile_service.remove_condition(user_id, c)
                st.rerun()

        with st.form("add_condition_form", clear_on_submit=True):
            new_condition = st.text_input("Add condition")
            if st.form_submit_button("Add") and new_condition:
                profile_service.add_condition(user_id, new_condition)
                st.rerun()


# ---------------------------------------------------------
# TAB 2: SCAN HISTORY
# ---------------------------------------------------------

def render_history_tab(user_id: int):
    history = scan_service.get_history(user_id, limit=50)

    if not history:
        st.info("No scans yet. Use the voice assistant to scan a product.")
        return

    df = pd.DataFrame(history)[["scanned_at", "scanned_item_name", "verdict", "reason"]]
    df.columns = ["When", "Item", "Verdict", "Reason"]

    def highlight_verdict(row):
        color = {"safe": "#d4edda", "risky": "#f8d7da", "unknown": "#fff3cd"}.get(row["Verdict"], "")
        return [f"background-color: {color}"] * len(row)

    st.dataframe(df.style.apply(highlight_verdict, axis=1), use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# TAB 3: LAUNCH ASSISTANT
# ---------------------------------------------------------

def render_launch_tab():
    st.subheader("Voice + Camera Assistant")
    st.write(
        "This launches the full accessible assistant: voice-driven login, "
        "profile setup, and the live camera for 'describe' and 'scan'. "
        "It opens its own window and console, separate from this dashboard."
    )

    if st.button("Launch Assistant", type="primary"):
        project_root = os.path.dirname(os.path.abspath(__file__))
        user_id = st.session_state.user["user_id"]
        try:
            subprocess.Popen(
                [sys.executable, "-m", "main", "--user-id", str(user_id)],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            st.success("Assistant launched — a new console window should appear, "
                       "already logged in as you.")
        except Exception as e:
            st.error(f"Failed to launch: {e}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

render_auth_sidebar()

st.title("🦯 Sight Assist Dashboard")

if not st.session_state.user:
    st.info("Log in or sign up from the sidebar to view your profile and scan history.")
else:
    user_id = st.session_state.user["user_id"]
    tab1, tab2, tab3 = st.tabs(["Profile", "Scan History", "Launch Assistant"])

    with tab1:
        render_profile_tab(user_id)
    with tab2:
        render_history_tab(user_id)
    with tab3:
        render_launch_tab()