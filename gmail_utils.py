import os
import pickle
import json
import base64
from email import message_from_bytes
from email.utils import parseaddr
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'client_secret_574781370160-psnr45igs52rh091ns43bomqpfggsgof.apps.googleusercontent.com.json'
TOKEN_FILE = 'token.json'
CACHE_FILE = 'email_cache.json'

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_console()
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def extract_text_from_payload(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8', errors='ignore')
    elif payload['mimeType'] == 'text/plain':
        data = payload['body'].get('data')
        if data:
            return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8', errors='ignore')
    return "(No plain text content)"

def fetch_and_cache_unread_emails(limit=5):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=limit).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = txt['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown)")
        body = extract_text_from_payload(txt['payload'])

        email_data.append({
            "id": msg['id'],
            "subject": subject,
            "from": parseaddr(sender)[1],
            "body": body.strip()
        })

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(email_data, f, ensure_ascii=False, indent=2)

    return email_data
