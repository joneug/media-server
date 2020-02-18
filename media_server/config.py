import os

# General
LOGLEVEL = os.environ.get('MS_LOGLEVEL', 'INFO').upper()
SLEEP_TIME = int(os.environ.get('MS_SLEEPTIME', 5))
WAV_FILE = os.environ.get('MS_WAV_FILE', 'audio.wav')

# Redis
REDIS_HOST = os.environ.get('MS_REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('MS_REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('MS_REDIS_DB', 0))
REDIS_INDEX = 'callees'

# VoIP Account
ACCOUNT_ID = os.environ.get('MS_ACCOUNT_ID')
ACCOUNT_USERNAME = os.environ.get('MS_ACCOUNT_USERNAME')
ACCOUNT_PASSWORD = os.environ.get('MS_ACCOUNT_PASSWORD')
