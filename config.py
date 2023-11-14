from redis import Redis
from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists

redis_host = 'redis-12452.c296.ap-southeast-2-1.ec2.cloud.redislabs.com'
redis_port = 12452
REDIS_CLOUD_PASSWORD = env.str("REDIS_CLOUD_PASSWORD")
APP = env.str("APP")

redis_client = Redis(host=redis_host, port=redis_port, password=REDIS_CLOUD_PASSWORD, decode_responses=True)
configs = redis_client.hgetall(APP + ':configs')

SLACK_CHATGPT_BOT_TOKEN = configs.get("SLACK_CHATGPT_BOT_TOKEN")
SLACK_BOT_USER_OAUTH_TOKEN = configs.get("SLACK_BOT_USER_OAUTH_TOKEN")
OPENAI_API_KEY = configs.get("OPENAI_API_KEY")
MY_SLACK_USER_ID = configs.get("MY_SLACK_USER_ID")

CHATGPT_CHANNEL_PREFIXES = ('chatgpt_', 'gpt_', 'gpt4_')
CODE_INTERPRETER_PREFIXES = ('code_', 'assist_',)
DEFAULT_CHATGPT_MODEL = configs.get("DEFAULT_CHATGPT_MODEL", "gpt-3.5-turbo")
CHATGPT_MAX_TOKEN = configs.get("CHATGPT_MAX_TOKEN", 4097)

if __name__ == '__main__':
    print(configs)
