import logging
import time
from datetime import datetime
from threading import Event

import redis
from application.notification import NotificationCenter
from sipsimple.account import Account, AccountManager
from sipsimple.application import SIPApplication
from sipsimple.audio import WavePlayer
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import SIPURI, SIPCoreError, ToHeader
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.storage import FileStorage
from sipsimple.streams.rtp.audio import AudioStream
from sipsimple.threading.green import run_in_green_thread

from media_server import config


class SIPWavePlayer(SIPApplication):
    def __init__(self, run_event):
        SIPApplication.__init__(self)
        self.run_event = run_event
        self.ended = Event()
        self.session = None
        self.player = None
        self.redis_connection = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

        NotificationCenter().add_observer(self)

        self.account_manager = AccountManager()

        self.start(FileStorage(config.CONFIG_FOLDER))

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        logging.info('Application did start - registering SIP account and initializing settings')

        self.account_manager.load()

        if not self.account_manager.has_account(config.ACCOUNT_ID):
            account = Account(config.ACCOUNT_ID)
            account.auth.username = config.ACCOUNT_USERNAME
            account.auth.password = config.ACCOUNT_PASSWORD
            account.enabled = True
            account.save()
        else:
            account = self.account_manager.get_account(config.ACCOUNT_ID)

        self.account = account
        self.account_manager.start()

        settings = SIPSimpleSettings()
        # We don't need speakers or microphone
        settings.audio.input_device = None
        settings.audio.output_device = None
        settings.save()

        self.player = WavePlayer(
            SIPApplication.voice_audio_mixer,
            '%s/%s' % (config.AUDIO_FOLDER, config.AUDIO_FILE),
            loop_count=config.PLAYER_LOOP_COUNT,
            initial_delay=config.PLAYER_INITIAL_DELAY,
            pause_time=config.PLAYER_PAUSE_TIME
        )

    def next_call(self):
        logging.info('Looking for new calls to make')
        while self.run_event.is_set():
            # Has to be a valid SIP URI (e. g. 'sip:123@ipbx.local')
            callee = None

            if self.redis_connection.exists(config.REDIS_INDEX):
                callee = self.redis_connection.lpop(config.REDIS_INDEX)

            if not callee:
                logging.info('No callees to call - sleeping for %s second' % config.SLEEP_TIME)
                time.sleep(config.SLEEP_TIME)
                continue

            self.call(callee)
            break

    @run_in_green_thread
    def call(self, sip_uri):
        logging.info('Establishing session to %s' % sip_uri)
        try:
            callee = ToHeader(SIPURI.parse(sip_uri))
        except SIPCoreError:
            logging.error("Specified SIP URI '%s' is not valid" % sip_uri)
            self.next_call()
            return

        try:
            routes = DNSLookup().lookup_sip_proxy(callee.uri, ['udp']).wait()
        except DNSLookupError, e:
            logging.error('DNS lookup failed: %s' % str(e))
            self.next_call()
            return

        self.session = Session(self.account)
        self.session.connect(callee, routes, [AudioStream()])

    def _NH_SIPSessionDidStart(self, notification):
        logging.info('Session did start - starting WAV player')
        audio_stream = self.session.streams[0]
        audio_stream.bridge.add(self.player)
        self.player.play()

    def _NH_SIPSessionWillEnd(self, notification):
        logging.info('Session will end - stopping WAV player')
        audio_stream = self.session.streams[0]
        self.player.stop()
        audio_stream.bridge.remove(self.player)

    def _NH_WavePlayerDidEnd(self, notification):
        logging.info('WAV player did stop - ending session')
        self.session.end()

    def _NH_SIPSessionDidEnd(self, notification):
        logging.info('Session ended - starting next call')
        self.next_call()

    def _NH_SIPAccountRegistrationDidSucceed(self, notification):
        contact_header = notification.data.contact_header
        expires = notification.data.expires
        registrar = notification.data.registrar

        logging.info(
            'Registered contact "%s" for sip:%s at %s:%d \n'
            'Transport: %s \n'
            'Expires in %d seconds' %
            (contact_header.uri, self.account.id, registrar.address, registrar.port, registrar.transport, expires)
        )

    def _NH_SIPAccountRegistrationGotAnswer(self, notification):
        if notification.data.code >= 300:
            registrar = notification.data.registrar
            code = notification.data.code
            reason = notification.data.reason
            logging.error(
                'SIP registration failed at %s:%d \n'
                'Transport: %s \n'
                '%d %s' %
                (registrar.address, registrar.port, registrar.transport, code, reason)
            )
            self.stop()

    def _NH_SIPAccountRegistrationDidFail(self, notification):
        logging.error(
            'SIP registration failed for account %s \n'
            'Error: %s' %
            (self.account.id, notification.data.error)
        )
        self.stop()

    def _NH_SIPAccountRegistrationDidEnd(self, notification):
        logging.info('SIP registration ended')

    def _NH_SIPSessionDidFail(self, notification):
        logging.error('SIP session failed - starting next call')
        self.next_call()

    def _NH_SIPApplicationDidEnd(self, notification):
        self.ended.set()
        logging.info('Ended application')
