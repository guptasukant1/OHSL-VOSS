import os
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Set up the scheduler for reminders
scheduler = BackgroundScheduler()

# Meeting Schedule Feature
def get_meeting_schedule():
    service = build('calendar', 'v3', developerKey=os.getenv("GOOGLE_API_KEY"))
    now = datetime.now(datetime.UTC).isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return events

@app.command("/schedule")
def show_schedule(ack, respond):
    ack()
    events = get_meeting_schedule()
    if not events:
        respond("No upcoming meetings found.")
    else:
        schedule = "Here are your upcoming meetings:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            schedule += f"{start} - {event['summary']}\n"
        respond(schedule)

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

# # IT Support Feature
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

# # Role and Group Management Feature
# roles = {}

# @app.command("/assign_role")
# def assign_role(ack, respond, command):
#     ack()
#     user_id = command['text'].split()[0]
#     role = command['text'].split()[1]
#     roles[user_id] = role
#     respond(f"Assigned role {role} to <@{user_id}>")

# @app.command("/create_group")
# def create_group(ack, respond, command):
#     ack()
#     group_name = command['text'].split()[0]
#     user_ids = command['text'].split()[1:]
#     channel_response = app.client.conversations_create(name=group_name)
#     channel_id = channel_response['channel']['id']
#     for user_id in user_ids:
#         app.client.conversations_invite(channel=channel_id, users=user_id)
#     respond(f"Created group {group_name} with members: {' '.join(user_ids)}")

# @app.command("/message_group")
# def message_group(ack, respond, command):
#     ack()
#     group_name = command['text'].split()[0]
#     message = ' '.join(command['text'].split()[1:])
#     channel_response = app.client.conversations_list()
#     channel_id = next(c['id'] for c in channel_response['channels'] if c['name'] == group_name)
#     app.client.chat_postMessage(channel=channel_id, text=message)
#     respond(f"Message sent to group {group_name}")

# Start the app
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
