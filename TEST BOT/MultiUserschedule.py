from dotenv import load_dotenv
import requests

import os
import json
import datetime
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

load_dotenv()

# Initialize Slack app and Falcon LLM via Hugging Face Inference APICLIENT_SECRETS_FILE
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')


API_TOKEN = os.getenv("API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# Set up the scheduler for reminders
# scheduler = BackgroundScheduler()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


REDIRECT_URI = 'http://localhost:3000/oauth2callback'

# In-memory storage for user credentials
user_credentials = {}

def get_flow(state=None):
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )

@app.command("/schedule")
def schedule_command(ack, respond, command):
    ack()
    user_id = command['user_id']

    if user_id in user_credentials:
        # User is already authenticated, get their calendar events
        creds = Credentials.from_authorized_user_info(user_credentials[user_id], SCOPES)
        events = get_user_events(creds)
        respond(format_events(events))
    else:
        # User needs to authenticate, redirect them to the OAuth2 URL
        flow = get_flow()
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        # Store the state for later verification
        user_credentials[user_id] = {'state': state}
        respond(f"Please [authorize this app]({authorization_url}) to view your calendar events.")

def oauth2callback(state, code):
    user_id = None
    for uid, creds in user_credentials.items():
        if creds.get('state') == state:
            user_id = uid
            break
    
    if not user_id:
        return "User not found", 400

    flow = get_flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Store the credentials for the user
    user_credentials[user_id] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    return "Authentication successful! You can now use the /schedule command in Slack."

def get_user_events(creds):
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])

def format_events(events):
    if not events:
        return "No upcoming events found."
    
    formatted_events = "Your upcoming events:\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        formatted_events += f"- {event['summary']} at {start}\n"
    return formatted_events

# @app.route("/oauth2callback")
# def handle_oauth2callback(req, res):
#     code = req.params['code']
#     state = req.params['state']
#     message = oauth2callback(state, code)
#     res.send(message)

class OAuth2Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        state = query_components.get("state", [None])[0]
        code = query_components.get("code", [None])[0]
        message = oauth2callback(state, code)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))

def run_oauth_server(server_class=HTTPServer, handler_class=OAuth2Handler, port=3000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    oauth_thread = threading.Thread(target=run_oauth_server)
    oauth_thread.daemon = True
    oauth_thread.start()
    
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()