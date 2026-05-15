"""Firebase接続・認証ユーティリティ"""

from pathlib import Path

import firebase_admin
import requests
from firebase_admin import credentials, firestore

_KEY_FILE = Path(__file__).parent / "serviceAccountKey.json"
FIREBASE_API_KEY = "AIzaSyAnZixCpZL56unu85N7XyY3FE9iHdp8oyk"

if not firebase_admin._apps:
    cred = credentials.Certificate(str(_KEY_FILE))
    firebase_admin.initialize_app(cred)

db = firestore.client()


def sign_in(email: str, password: str) -> dict | None:
    """メール/パスワードでFirebase認証。成功時にユーザー情報dictを返す。"""
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )
    try:
        resp = requests.post(
            url,
            json={"email": email, "password": password, "returnSecureToken": True},
            headers={"Referer": "http://localhost:8501"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        import streamlit as st
        st.session_state["_login_error"] = resp.json().get("error", {}).get("message", "認証エラー")
    except requests.RequestException as e:
        import streamlit as st
        st.session_state["_login_error"] = str(e)
    return None


def is_allowed_user(email: str) -> bool:
    """allowedUsersコレクションで許可されているか確認。"""
    doc = db.collection("allowedUsers").document(email).get()
    return doc.exists and doc.to_dict().get("active", False)
