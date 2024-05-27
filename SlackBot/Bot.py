import os
import slack
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
load_dotenv()

app = Flask(__name__)
# handler = SlackRequestHandler(app)
slack_event_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], '/slack/events', app)
# env_path = Path('.') / '.env'
# load_dotenv(dotenv_path=env_path)

client = slack.WebClient(token=os.environ['SLACK_BOT_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

@slack_event_adapter.on('message')
def message(data):
    print(data)
    event = data.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    if BOT_ID != user_id:
        client.chat_postMessage(channel=channel_id, text=text)

# @slack_event_adapter.on('app_mention')
# @app.command("/mention")
# def 
roles = {}

# @app.command("/assign_role")
# @app.route('/assign-role', methods=['POST'])
# def assign_role(ack, respond, command):
#     ack()
#     user_id = command['text'].split()[0]
#     role = command['text'].split()[1]
#     roles[user_id] = role
#     respond(f"Assigned role {role} to <@{user_id}>")
#     return Response(), 200

@app.route('/assign-role', methods=['POST'])
def assign_role():
    data = request.form
    # print(data)
    user_id = data.get('user_id')
    text = data.get('text')
    channel_id = data.get('channel_id')
    client.chat_postMessage(channel=channel_id, text='Assigned role {} to <@{}>'.format(text, user_id))
    return Response(), 200

# Reminders Feature
def send_reminder(event):
    channel_id = '#general'
    message = f"Reminder: {event['summary']} at {event['start'].get('dateTime', event['start'].get('date'))}"
    app.client.chat_postMessage(channel=channel_id, text=message)


# @app.route("/assign-role", methods=["POST"])
# def assign_role(ack, respond, command):
#     ack()
#     text = command['text']
#     parts = text.split()
    
#     if len(parts) != 2:
#         respond("Please provide both username and role in the format: @username role.")
#         return
    
#     username, role = parts
#     if not username.startswith('@'):
#         respond("Please use @username format for the username.")
#         return
    
#     # Remove the "@" character to get the username
#     username = username[1:]

#     try:
#         # Use the Slack API to get the user ID from the username
#         response = app.client.users_lookupByEmail(email=username)
#         if not response['ok']:
#             respond(f"User {username} not found.")
#             return

#         user_id = response['user']['id']
#         roles[user_id] = role
#         respond(f"Assigned role {role} to {username}.")
#     except Exception as e:
#         respond(f"Failed to assign role: {str(e)}")


if __name__ == "__main__":
    app.run(debug=True, port=3500)