import os
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize Slack app and OpenAI
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Set up the scheduler for reminders
scheduler = BackgroundScheduler()

# # Meeting Schedule Feature
# def get_meeting_schedule():
#     service = build('calendar', 'v3', developerKey=os.getenv("GOOGLE_API_KEY"))
#     now = datetime.datetime.utcnow().isoformat() + 'Z'
#     events_result = service.events().list(
#         calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime'
#     ).execute()
#     events = events_result.get('items', [])
#     return events

# @app.command("/schedule")
# def show_schedule(ack, respond):
#     ack()
#     events = get_meeting_schedule()
#     if not events:
#         respond("No upcoming meetings found.")
#     else:
#         schedule = "Here are your upcoming meetings:\n"
#         for event in events:
#             start = event['start'].get('dateTime', event['start'].get('date'))
#             schedule += f"{start} - {event['summary']}\n"
#         respond(schedule)

# # Reminders Feature
# def send_reminder(event):
#     channel_id = '#general'
#     message = f"Reminder: {event['summary']} at {event['start'].get('dateTime', event['start'].get('date'))}"
#     app.client.chat_postMessage(channel=channel_id, text=message)

# def check_for_upcoming_events():
#     events = get_meeting_schedule()
#     now = datetime.datetime.utcnow().isoformat() + 'Z'
#     for event in events:
#         start = event['start'].get('dateTime', event['start'].get('date'))
#         if start > now:
#             send_reminder(event)

# scheduler.add_job(check_for_upcoming_events, 'interval', minutes=10)
# scheduler.start()

# IT Support Feature
# @app.message("help")
# def handle_help(message, say):
#     user_query = message['text']
#     predefined_responses = {
#         "password reset": "To reset your password, go to the following link...",
#         "VPN issue": "To resolve VPN issues, try the following steps..."
#     }
#     response = predefined_responses.get(user_query.lower(), "Please contact IT support at it-support@example.com.")
#     say(response)

# # Summarize Transcript Feature
# @app.command("/summarize")
# def summarize_transcript(ack, respond, command):
#     ack()
#     file_id = command['text'].strip()
#     file_info = app.client.files_info(file=file_id)
#     file_url = file_info['file']['url_private']
#     headers = {'Authorization': 'Bearer ' + os.getenv('SLACK_BOT_TOKEN')}
#     response = requests.get(file_url, headers=headers)
#     transcript = response.text

#     summary_response = openai.Completion.create(
#         engine="text-davinci-003",
#         prompt=f"Summarize the following transcript:\n{transcript}",
#         max_tokens=150
#     )
#     summary = summary_response['choices'][0]['text']
#     respond(summary)

# Role and Group Management Feature

def get_user_id_by_username(username):
    users_list = app.client.users_list()
    users = users_list['members']
    for user in users:
        if 'name' in user and user['name'] == username:
            return user['id']
        if 'profile' in user:
            profile = user['profile']
            if 'display_name' in profile and profile['display_name'] == username:
                return user['id']
            if 'real_name' in profile and profile['real_name'] == username:
                return user['id']
    return None

roles = {}

def assign_role(user_id, role):
    roles[user_id] = role

def get_role(user_id):
    return roles.get(user_id, "No role assigned")


@app.command("/assign_role")
def assign_role_command(ack, respond, command):
    ack()
    text_parts = command['text'].split()
    if len(text_parts) < 2:
        respond("Please provide a user and a role. Example: `/assign_role @username role`")
        return
    
    username = text_parts[0]
    role = ' '.join(text_parts[1:])
    
    if username.startswith('@'):
        username = username[1:]  # Remove the '@' character

    users_list = app.client.users_list()
    user_id = None
    for user in users_list['members']:
        if 'name' in user and user['name'] == username:
            user_id = user['id']
            break

    if not user_id:
        respond(f"User {username} not found.")
        return

    assign_role(user_id, role)
    respond(f"Assigned role {role} to <{user_id}>")


@app.command("/get_role")
def get_role_command(ack, respond, command):
    ack()
    username = command['text'].strip()
    
    if username.startswith('@'):
        username = username[1:]  # Remove the '@' character

    users_list = app.client.users_list()
    user_id = None
    for user in users_list['members']:
        if 'name' in user and user['name'] == username:
            user_id = user['id']
            break

    if not user_id:
        respond(f"User {username} not found.")
        return

    role = get_role(user_id)
    respond(f"<{user_id}> has the role: {role}")


@app.command("/create_group")
def create_group(ack, respond, command):
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

    channel_response = app.client.conversations_create(name=group_name)
    channel_id = channel_response['channel']['id']
    for user_id in user_ids:
        app.client.conversations_invite(channel=channel_id, users=user_id)
    respond(f"Created group {group_name} with members: {' '.join(usernames)}")


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
