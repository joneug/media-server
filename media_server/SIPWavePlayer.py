import logging
from datetime import datetime
from threading import Event

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
import redis
import time
import threading

class SIPWavePlayer(SIPApplication):
    def __init__(self, run_event):
        SIPApplication.__init__(self)
        self.run_event = run_event
        self.ended = Event()
        self.callee = None
        self.session = None
        self.player = None
        notification_center = NotificationCenter()
        notification_center.add_observer(self)
        self.account_manager = AccountManager()
        self.start(FileStorage('config'))
        self.wave_file = 'audio/%s' % config.WAV_FILE
        self.redis_connection = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

    def next_call(self):
        while self.run_event.is_set():
            # Has to be a valid SIP URI (e. g. 'sip:123@ipbx.local')
            callee = None

            if self.redis_connection.exists(config.REDIS_INDEX):
                callee = self.redis_connection.lpop(config.REDIS_INDEX)

            if not callee:
                logging.info('No callees to call - sleeping for %s second' % config.SLEEP_TIME)
                time.sleep(config.SLEEP_TIME)
                continue
        
            logging.info('Calling %s' % callee)
            self.call(callee)
            break

    @run_in_green_thread
    def call(self, target):
        self.callee = target

        try:
            self.callee = ToHeader(SIPURI.parse(self.callee))
        except SIPCoreError:
            print 'Specified SIP URI is not valid'
            #self.stop()
            return
        
        try:
            routes = DNSLookup().lookup_sip_proxy(self.callee.uri, ['udp']).wait()
        except DNSLookupError, e:
            print 'DNS lookup failed: %s' % str(e)
        else:
            self.session = Session(self.account)
            self.session.connect(self.callee, routes, [AudioStream()])

    def _NH_SIPSessionDidStart(self, notification):
        logging.info('SIPSessionDidStart')
        session = notification.sender
        audio_stream = session.streams[0]
        audio_stream.bridge.add(self.player)
        self.player.play()

    def _NH_SIPSessionWillEnd(self, notification):
        logging.info('SIPSessionWillEnd')
        session = notification.sender
        audio_stream = session.streams[0]
        self.player.stop()
        audio_stream.bridge.remove(self.player)

    def _NH_WavePlayerDidEnd(self, notification):
        logging.info('WavePlayerDidEnd')
        self.session.end()
        #self.stop()
    
    def _NH_SIPSessionDidEnd(self, notification):
        logging.info('SIPSessionDidEnd')
        self.next_call()
        #self.stop()

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        logging.info('SIPApplicationDidStart')

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

        self.player = WavePlayer(SIPApplication.voice_audio_mixer, self.wave_file, loop_count=3, initial_delay=1,
                                 pause_time=1)

    def _NH_SIPSessionGotRingIndication(self, notification):
        print 'Ringing!'

    def _NH_SIPAccountRegistrationDidSucceed(self, notification):
        contact_header = notification.data.contact_header
        expires = notification.data.expires
        registrar = notification.data.registrar

        print '%s Registered contact "%s" for sip:%s at %s:%d;transport=%s (expires in %d seconds).\n' % (
            datetime.now().replace(microsecond=0), contact_header.uri, self.account.id, registrar.address,
            registrar.port, registrar.transport, expires)

    def _NH_SIPAccountRegistrationGotAnswer(self, notification):
        if notification.data.code >= 300:
            registrar = notification.data.registrar
            code = notification.data.code
            reason = notification.data.reason
            print '%s Registration failed at %s:%d;transport=%s: %d %s\n' % (
                datetime.now().replace(microsecond=0), registrar.address, registrar.port, registrar.transport, code,
                reason)

    def _NH_SIPAccountRegistrationDidFail(self, notification):
        print '%s Failed to register contact for sip:%s: %s (retrying in %.2f seconds)\n' % (
            datetime.now().replace(microsecond=0), self.account.id, notification.data.error,
            notification.data.retry_after)
        self.success = False

    def _NH_SIPAccountRegistrationDidEnd(self, notification):
        print '%s Registration ended.\n' % datetime.now().replace(microsecond=0)

    def _NH_SIPSessionDidFail(self, notification):
        print 'Failed to connect'
        #self.stop()

    def _NH_SIPApplicationDidEnd(self, notification):
        self.ended.set()
