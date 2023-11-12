import sys

from redis import Redis
from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists


class RedisEnv:
    pass


redis_host = 'redis-12452.c296.ap-southeast-2-1.ec2.cloud.redislabs.com'
redis_port = 12452
REDIS_CLOUD_PASSWORD = env.str("REDIS_CLOUD_PASSWORD")
APP = 'slack:'

redis_client = Redis(host=redis_host, port=redis_port, password=REDIS_CLOUD_PASSWORD, decode_responses=True)


def get(name, default_value=sys.maxsize, type_method=str):
    key = APP + name
    is_exist = redis_client.exists(key)
    if is_exist:
        return type_method(redis_client.get(key))
    else:
        if default_value == sys.maxsize:
            raise Exception(f"Can't found config item `{name}`")
        return default_value


SLACK_CHATGPT_BOT_TOKEN = get("SLACK_CHATGPT_BOT_TOKEN")
SLACK_BOT_USER_OAUTH_TOKEN = get("SLACK_BOT_USER_OAUTH_TOKEN")
OPENAI_API_KEY = get("OPENAI_API_KEY")
MY_SLACK_USER_ID = get("MY_SLACK_USER_ID")

CHATGPT_CHANNEL_PREFIXES = ('chatgpt_', 'gpt_', 'gpt4_')
DEFAULT_CHATGPT_MODEL = get("DEFAULT_CHATGPT_MODEL", "gpt-3.5-turbo")
CHATGPT_MAX_TOKEN = get("CHATGPT_MAX_TOKEN", 4097)
