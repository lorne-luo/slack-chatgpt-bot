# from https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311
import logging

from environs import Env

env = Env()
env.read_env()

import os
import openai
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App


SLACK_BOT_TOKEN = env.str("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = env.str("SLACK_APP_TOKEN")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
chatgpt_engine = "gpt-3.5-turbo"

# Event API & Web API
app = App(token=SLACK_BOT_TOKEN)
client = WebClient(SLACK_BOT_TOKEN)


# This gets activated when the bot is tagged in a channel
@app.event("app_mention")
def handle_message_events(body, logger):
    # Create prompt for ChatGPT
    prompt = str(body["event"]["text"]).split(">")[1]

    # Log message
    logging.info('Msg Received: '+prompt)

    # Let thre user know that we are busy with the request
    # response = client.chat_postMessage(channel=body["event"]["channel"],
    #                                    thread_ts=body["event"]["event_ts"],
    #                                    text=f"Hello from your bot! :robot_face: \nThanks for your request, I'm on it!")

    # Check ChatGPT
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        engine=chatgpt_engine,
        prompt=prompt,
        max_tokens=4096,
        n=1,
        stop=None,
        temperature=0.5).choices[0].text

    # Reply to thread
    api_response = client.chat_postMessage(channel=body["event"]["channel"],
                                       thread_ts=body["event"]["event_ts"],
                                       text=response)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
