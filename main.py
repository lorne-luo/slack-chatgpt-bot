# from https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311
import logging
import traceback
from expiringdict import ExpiringDict
from environs import Env
import openai
from openai import RateLimitError, BadRequestError, OpenAI
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App
import config

# Event API & Web API
app = App(token=config.SLACK_BOT_USER_OAUTH_TOKEN)
client = WebClient(config.SLACK_BOT_USER_OAUTH_TOKEN)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

chatgpt_channels = ExpiringDict(max_len=100, max_age_seconds=8 * 3600)


def is_self(user_id):
    """is your self"""
    return user_id == config.MY_SLACK_USER_ID


def is_chatgpt_channel(channel_id):
    """if channel name starts with `chatgpt_`, you wanna talk to chatgpt
    return existing bool and channel topic
    """
    if channel_id in chatgpt_channels:
        return chatgpt_channels[channel_id]['model'], chatgpt_channels[channel_id]['topic']

    channel_infos = client.conversations_info(channel=channel_id)
    logging.debug(channel_infos)

    if not channel_infos['channel']['is_member']:
        # chatgpt bot not join this channel yet
        client.conversations_join(channel=channel_id)

    channel_name = channel_infos['channel']['name_normalized'].lower()

    if any([channel_name.startswith(prefix.lower()) for prefix in config.CHATGPT_CHANNEL_PREFIXES]):
        channel_topic = channel_infos.get('channel', '').get('topic', '').get('value', '')
        channel_description = channel_infos.get('channel', '').get('purpose', '').get('value', '')

        gpt_model = 'gpt-4-1106-preview' if channel_name.startswith('gpt4_') else config.DEFAULT_CHATGPT_MODEL
        topic = f"{channel_topic}. {channel_description}"
        chatgpt_channels[channel_id] = {"topic": topic, "model": gpt_model}
        return gpt_model, topic

    if any([channel_name.startswith(prefix.lower()) for prefix in config.CODE_INTERPRETER_PREFIXES]):
        channel_topic = channel_infos.get('channel', '').get('topic', '').get('value', '')
        channel_description = channel_infos.get('channel', '').get('purpose', '').get('value', '')
        gpt_model = 'code_interpreter'
        topic = f"{channel_topic}. {channel_description}"
        chatgpt_channels[channel_id] = {"topic": topic, "model": gpt_model}
        return gpt_model, topic

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

        gpt_model, channel_topic = is_chatgpt_channel(channel_id)
        if not gpt_model:
            return

        if gpt_model.startswith('gpt-'):
            # normal gpt 3.5 or 4
            try:
                chat_history = get_chat_history(channel_id, channel_topic, limit=0)
                response_text = request_chatgpt(prompt, chat_history, gpt_model)
            except (RateLimitError, BadRequestError) as ex:
                response_text = f'*Error:* {ex}\n\n'
            except Exception as ex:
                response_text = f'*Error:* {ex}\n\n'
                response_text += traceback.format_exc()
        elif gpt_model == 'code_interpreter':
            response_text = 'Not implemented'
        else:
            raise f'Uknown gpt model {gpt_model}'
        client.chat_postMessage(channel=channel_id, text=response_text)


def request_chatgpt(text, context, model=config.DEFAULT_CHATGPT_MODEL):
    response = openai_client.chat.completions.create(  # 1. Change the function Completion to ChatCompletion
        model=model,
        messages=context + [
            {'role': 'user', 'content': text}
        ],
        temperature=0.8,
        top_p=0.8,
    )
    content = response.choices[0].message.content
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
    SocketModeHandler(app, config.SLACK_CHATGPT_BOT_TOKEN).start()
