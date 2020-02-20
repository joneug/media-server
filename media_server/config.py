import os

# General
LOGLEVEL = os.environ.get('MS_LOGLEVEL', 'INFO').upper()
SLEEP_TIME = int(os.environ.get('MS_SLEEP_TIME', 5))
CONFIG_FOLDER = 'config'
AUDIO_FOLDER = 'audio'
AUDIO_FILE = os.environ.get('MS_WAV_FILE', 'audio.wav')
PLAYER_LOOP_COUNT = int(os.environ.get('MS_PLAYER_LOOP_COUNT', 3))
PLAYER_INITIAL_DELAY = int(os.environ.get('MS_PLAYER_INITIAL_DELAY', 1))
PLAYER_PAUSE_TIME = int(os.environ.get('MS_PLAYER_PAUSE_TIME', 1))

# Redis
REDIS_HOST = os.environ.get('MS_REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('MS_REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('MS_REDIS_DB', 0))
REDIS_INDEX = 'callees'

# SIP Account
ACCOUNT_ID = os.environ.get('MS_ACCOUNT_ID')
ACCOUNT_USERNAME = os.environ.get('MS_ACCOUNT_USERNAME')
ACCOUNT_PASSWORD = os.environ.get('MS_ACCOUNT_PASSWORD')
