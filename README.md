# 📢 Media Server

This repository contains code for a SIP application that calls SIP URIs provided in a redis database and play a given
WAV file. The code was adapted from [saghul/sipsimple-examples](https://github.com/saghul/sipsimple-examples). It uses
the [SIP SIMPLE library](https://github.com/AGProjects/python-sipsimple).

The application runs as a service and can be deployed using Docker. The following environment variables can be specified
to configure the application:

* `ACCOUNT_ID`: Specifies the SIP account ID (e. g. `123@ipbx.local`).
* `ACCOUNT_USERNAME`: Specifies the SIP account username.
* `ACCOUNT_PASSWORD`: Specifies the SIP account password.
* `REDIS_HOST`: Specifies the redis host (defaults to localhost).
* `REDIS_PORT`: Specifies the redis port (defaults to 6379).
* `REDIS_DB`: Specifies the redis database (defaults to 0).
* `LOGLEVEL`: Specifies the log level (defaults to INFO).
* `SLEEP_TIME`: Specifies the time interval to sleep during active polling (defaults to 5).
* `AUDIO_FILE`: Specifies the WAV file to play during calls. These have to be placed in the `audio` folder (defaults to `audio.wav`).
* `PLAYER_LOOP_COUNT`: Specifies the number of times to play the WAV file (defaults to 3).
* `PLAYER_INITIAL_DELAY`: Specifies the initial delay in seconds before playing the WAV file (defaults to 1).
* `PLAYER_PAUSE_TIME`: Specifies the pause time in seconds between play loops (defaults to 1).
