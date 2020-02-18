import logging
import time
import redis
from media_server import config
from .SIPWavePlayer import SIPWavePlayer

def main():
    logging.basicConfig(level=config.LOGLEVEL, format='%(asctime)s [%(levelname)s] %(message)s')

    logging.info('Connecting to redis')
    redis_connection = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

    while True:
        # Has to be a valid SIP URI (e. g. 'sip:123@ipbx.local')
        callee = None

        if redis_connection.exists(config.REDIS_INDEX):
            callee = redis_connection.lpop(config.REDIS_INDEX)

        if not callee:
            logging.info('No callees to call - sleeping for %s second' % config.SLEEP_TIME)
            time.sleep(config.SLEEP_TIME)
            continue
        
        logging.info('Calling %s' % callee)
        
        player = SIPWavePlayer()
        player.call(callee)
        if player.session:
            player.session.end()
        player.ended.wait()
        del(player)

        logging.info('Call to %s ended' % callee)

if __name__ == '__main__':
    main()
