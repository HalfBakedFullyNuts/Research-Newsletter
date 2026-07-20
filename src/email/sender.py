from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64
import sys, os
from email.mime.text import MIMEText
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core")))
from config import ADMIN_EMAIL, GOOGLE_TOKEN_PATH

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

def get_gmail_service():
    creds = Credentials.from_authorized_user_file(str(Path(GOOGLE_TOKEN_PATH)), scopes=SCOPES)
    return build('gmail', 'v1', credentials=creds)

def send_email(to_address, subject, html_body):
    service = get_gmail_service()
    
    message = MIMEText(html_body, 'html', 'utf-8')
    message['to'] = to_address
    message['from'] = ADMIN_EMAIL
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()
    print(f"Email sent to {to_address}")
