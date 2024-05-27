import os
import slack
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
load_dotenv()

app = Flask(__name__)
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



if __name__ == "__main__":
    app.run(debug=True, port=3500)