# from https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311
import logging
import traceback
from pprint import pprint

from expiringdict import ExpiringDict

from environs import Env

env = Env()
env.read_env()

import openai
from openai.error import RateLimitError, InvalidRequestError
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App

SLACK_BOT_TOKEN = env.str("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = env.str("SLACK_APP_TOKEN")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
MY_USER_ID = env.str("MY_USER_ID", None)
CHATGPT_CHANNEL_PREFIXES = ('chatgpt_', 'gpt')
CHATGPT_ENGINE_NAME = "gpt-3.5-turbo"
MAX_TOKEN = 4097

# Event API & Web API
app = App(token=SLACK_BOT_TOKEN)
client = WebClient(SLACK_BOT_TOKEN)

chatgpt_channels = ExpiringDict(max_len=100, max_age_seconds=8 * 3600)


def is_self(user_id):
    """is your self"""
    return user_id == MY_USER_ID


def is_chatgpt_channel(channel_id):
    """if channel name starts with `chatgpt_`, you wanna talk to chatgpt
    return existing bool and channel topic
    """
    if channel_id in chatgpt_channels:
        return True, chatgpt_channels[channel_id]

    channel_infos = client.conversations_info(channel=channel_id)
    logging.debug(channel_infos)

    if not channel_infos['channel']['is_member']:
        # chatgpt bot not join this channel yet
        client.conversations_join(channel=channel_id)

    channel_name = channel_infos['channel']['name_normalized'].lower()

    if any([channel_name.startswith(prefix.lower()) for prefix in CHATGPT_CHANNEL_PREFIXES]):
        channel_topic = channel_infos.get('channel', '').get('topic', '').get('value', '')
        channel_description = channel_infos.get('channel', '').get('purpose', '').get('value', '')
        chatgpt_channels[channel_id] = f"{channel_topic}. {channel_description}"

        return True, chatgpt_channels[channel_id]

    return False, None


def get_chat_history(channel_id, topic='', limit=10):
    """get chat history by channel id, format as chatgpt wanted"""
    chat_context = []

    response = client.conversations_history(channel=channel_id, limit=limit)
    messages = response['messages']

    for message in messages:
        role = 'assistant' if 'bot_id' in message else 'user'
        content = message['text']
        if not content.startswith('Error:'):
            chat_context.append({"role": role, "content": content})

    chat_context = [
                       {"role": "system", "content": topic},
                       {'role': 'user', 'content': topic}
                   ] + list(reversed(chat_context))
    return chat_context


@app.event("message")
def chatgpt_channel(event, logger):
    """sent channel topic and descript as chatgpt conversation context"""
    user = event['user']

    if subtype := event.get("subtype", None):
        logging.info(f"Message subtype = {subtype}, skip.")
        return
    prompt = event['text']
    logging.info(f"Sent: {prompt}")

    channel_type = event.get('channel_type', None)
    channel_id = event.get("channel", None)
    if channel_type == 'channel' and channel_id:

        is_chatgpt, channel_topic = is_chatgpt_channel(channel_id)
        if is_chatgpt:
            try:
                chat_history = get_chat_history(channel_id, channel_topic)
                response_text = request_chatgpt(prompt, chat_history)
            except (RateLimitError, InvalidRequestError) as ex:
                response_text = f'*Error:* {ex}\n\n'
            except Exception as ex:
                response_text = f'*Error:* {ex}\n\n'
                response_text += traceback.format_exc()
            client.chat_postMessage(channel=channel_id,
                                    text=response_text)


def request_chatgpt(text, context):
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(  # 1. Change the function Completion to ChatCompletion
        model='gpt-3.5-turbo',
        messages=context + [
            {'role': 'user', 'content': text}
        ],
        temperature=0
    )
    content = response['choices'][0]['message']['content']
    return content


# be mentioned in none channel (im)
@app.event("app_mention")
def handle_message_events(body, logger):
    prompt = str(body["event"]["text"]).split(">")[1]
    # Log message
    logging.info('Sent: ' + prompt)

    channel_id = body["event"].get("channel", None)

    chat_history = get_chat_history(channel_id)
    response_text = request_chatgpt(prompt, chat_history)
    client.chat_postMessage(channel=channel_id,
                            text=response_text)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
