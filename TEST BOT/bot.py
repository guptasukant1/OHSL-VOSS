# from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import json
import requests
import datetime
from slack_sdk.errors import SlackApiError
import time
load_dotenv()

# Initialize Slack app and Falcon LLM via Hugging Face Inference API
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
app = App(token = SLACK_BOT_TOKEN)

API_TOKEN = os.getenv("API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"
# API_URL=os.getenv('API_URL')
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# Set up the scheduler for reminders
scheduler = BackgroundScheduler()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Meeting Schedule Feature
def get_google_calendar_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is created
    # automatically when the authorization flow completes for the first time.
    creds_path = os.path.join(os.path.dirname(__file__), 'credential.json')
    token_path = os.path.join(os.path.dirname(__file__), 'tokens.json')

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=3500)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_upcoming_events():
    service = get_google_calendar_service()
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events


@app.command("/schedule")
def get_events(ack, respond):
    ack()
    events = get_upcoming_events()
    if not events:
        respond("No upcoming events found.")
        return
    
    response_text = "Upcoming events:\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        response_text += f"{start} - {event['summary']}\n"
    
    respond(response_text)

# Reminders Feature
reminder_channel_id = None

@app.command("/set_reminder")
def set_reminder_channel(ack, respond, command):
    global reminder_channel_id
    ack()
    channel_name = command['text'].strip()

    try:
        # To convert channel name to channel ID
        response = app.client.conversations_list()
        channels = response['channels']
        channel_id = None
        for channel in channels:
            if channel['name'] == channel_name:
                channel_id = channel['id']
                break
        
        if channel_id is None:
            respond(f"Channel #{channel_name} not found.")
            return
        
        reminder_channel_id = channel_id
        respond(f"Reminders will be sent to <#{channel_id}>.")
    except Exception as e:
        respond(f"Failed to set reminder channel: {str(e)}")

def send_reminder(event):
    if reminder_channel_id is None:
        return
    message = f"Reminder: {event['summary']} at {event['start'].get('dateTime', event['start'].get('date'))}"
    app.client.chat_postMessage(channel=reminder_channel_id, text=message)

def check_for_upcoming_events():
    events = get_upcoming_events()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if start > now:
            send_reminder(event)


scheduler.add_job(check_for_upcoming_events, 'interval', minutes=10)
scheduler.start()

# File Summarization Feature
user_latest_file = {}

@app.event("file_shared")
def handle_file_shared(event, say):
    file_id = event["file"]["id"]
    user_id = event["user_id"]

    try:
        # Store the latest file uploaded by the user
        user_latest_file[user_id] = file_id
        say(f"File uploaded successfully {file_id} . You can now use /summarize to summarize it.")
    except SlackApiError as e:
        say(f"Error: {e.response['error']}")


@app.command('/summarize')
def summarize_transcript(ack, respond, command):
    ack()
    user_id = command['user_id']
    text = command['text'].strip()

    # Determine which file to summarize
    if text:
        # User provided a file ID
        file_id = text
    else:
        # Use the latest file uploaded by the user
        file_id = user_latest_file.get(user_id)
        if not file_id:
            respond("No file found. Please upload a file first or provide a file ID.")
            return

    # Retrieve file info
    try:
        file_info = app.client.files_info(file=file_id)
        file_url = file_info['file']['url_private']
        # respond(f"{file_url} : {file_info}")
    except SlackApiError as e:
        respond(f"Error retrieving file info: {e.response['error']}")
        return

    # Download the file content
    headers = {'Authorization': f"Bearer {SLACK_BOT_TOKEN}"}
    response = requests.get(file_url, headers=headers)

    if response.status_code != 200:
        respond(f"Failed to retrieve file: {response.status_code}")
        return
    else: 
        # respond(f"File retrieved successfully\n {response.text}")
        respond(f"File retrieved successfully\n")


    transcript = response.text
    # print(response)

    # Summarize using Falcon 7B model
    summary = summarize_with_falcon(transcript)
    respond(summary)

def summarize_with_falcon(transcript):
    payload = {
        "inputs": f"Please summarize the following text into 2 lines and extract the key information only`: {transcript}",
        "parameters": {
            "max_length": 8000,
            "num_return_sequences": 1
        }
    }

    # response = requests.post(API_URL, headers=headers, json=payload)

    # if response.status_code != 200:
    #     return f"Error summarizing with Falcon: {response.status_code} - {response.text}"

    # try:
    #     result = response.json()
    #     summary = result[0]['generated_text']
    #     print(response)
    # except (ValueError, KeyError, IndexError) as e:
    #     return f"Error parsing response: {str(e)}"

    # return summary
    options = {
        "method": "POST",
        "contentType": "application/json",
        "headers": {
            "Authorization": f"Bearer {API_TOKEN}"
        },
        "payload": json.dumps(payload),
        "muteHttpExceptions": True
    }

    try:
        response = requests.post(API_URL, headers=options["headers"], json=payload)
        print("Response Status Code:", response.status_code)  # Debugging: Print status code
        print("Response Text:", response.text)  # Debugging: Print response text
        data = response.json()
        print("Response JSON Data:", data)  # Debugging: Print parsed JSON data
        if data and len(data) > 0 and 'generated_text' in data[0]:
            return data[0]['generated_text']
        elif data and 'error' in data:
            return f"Error from Falcon API: {data['error']}"
        else:
            return "No summary available."
    except Exception as e:
        return f"Error fetching summary: {str(e)}"

# Function to query the LLM
def query_llm(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

# Command to provide IT support using LLM
@app.command("/ask_it")
def ask_it(ack, respond, command):
    ack()
    user_question = command['text']
    
    payload = {
        "inputs": user_question,
        "parameters": {
            "max_length": 500,
            "num_return_sequences": 1
        }
    }
    
    try:
        llm_response = query_llm(payload)
        answer = llm_response[0]['generated_text']
        respond(answer)
    except Exception as e:
        respond(f"Failed to get a response from the IT support LLM: {str(e)}")


user_cache = {}

# Group Management Feature
def get_user_id_by_username(username):
    if username in user_cache:
        return user_cache[username]

    try:
        users_list = app.client.users_list()
        for user in users_list['members']:
            if user['name'] == username:
                user_cache[username] = user['id']
                return user['id']
    except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
            retry_after = int(e.response.headers.get('Retry-After', 1))
            time.sleep(retry_after)
            return get_user_id_by_username(username)
        else:
            raise e

    return None

@app.command("/create_group")
def create_group(ack, respond, command):
    ack()
    text_parts = command['text'].split()
    group_name = text_parts[0]
    usernames = text_parts[1:]
    user_ids = []

    for username in usernames:
        if username.startswith('@'):
            username = username[1:]  # Removes the '@' character from name calls
        user_id = get_user_id_by_username(username)
        if user_id:
            user_ids.append(user_id)
        else:
            respond(f"User {username} not found.")
            return

    try:
        channel_response = app.client.conversations_create(name=group_name)
        channel_id = channel_response['channel']['id']
        for user_id in user_ids:
            app.client.conversations_invite(channel=channel_id, users=user_id)
        respond(f"Created group {group_name} with members: {' '.join(usernames)}")
    except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
            retry_after = int(e.response.headers.get('Retry-After', 1))
            time.sleep(retry_after)
            respond("Rate limit hit. Please try again later.")
        else:
            respond(f"Failed to create group: {e.response['error']}")


@app.command("/message_group")
def message_group(ack, respond, command):
    ack()
    group_name = command['text'].split()[0]
    message = ' '.join(command['text'].split()[1:])
    channel_response = app.client.conversations_list()
    channel_id = next(c['id'] for c in channel_response['channels'] if c['name'] == group_name)
    app.client.chat_postMessage(channel=channel_id, text=message)
    respond(f"Message sent to group {group_name}")

@app.command("/add_to_group")
def add_to_group(ack, respond, command):
    ack()
    text_parts = command['text'].split()
    group_name = text_parts[0]
    usernames = text_parts[1:]
    user_ids = []

    for username in usernames:
        if username.startswith('@'):
            username = username[1:]  # Remove the '@' character
        user_id = get_user_id_by_username(username)
        if user_id:
            user_ids.append(user_id)
        else:
            respond(f"User {username} not found.")
            return

    channel_response = app.client.conversations_list()
    channel_id = next((c['id'] for c in channel_response['channels'] if c['name'] == group_name), None)
    if not channel_id:
        respond(f"Group {group_name} not found.")
        return

    for user_id in user_ids:
        app.client.conversations_invite(channel=channel_id, users=user_id)
    respond(f"Added members to group {group_name}: {' '.join(usernames)}")

# Start the app
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()