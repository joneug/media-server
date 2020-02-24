import logging
import time
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
    """
    Application class for a SIP application that calls SIP URIs found in a redis database and plays a specified WAV file

    Parameters
    ----------
    run_event : threading.Event
        Event that is cleared once the application should end. Otherwise the application will keep looking for new calls
        to make.

    Methods
    -------
    next_call()
        Looks for new calls to make and starts them.
    """

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

    def next_call(self):
        """
        Looks for new calls to make and starts them.

        This function looks in the specified redis database at the specified index for SIP URIs to call. It requires
        valid SIP URIs (e. g. 'sip:123@ipbx.local').
        """
        logging.info('Looking for new calls to make')
        while self.run_event.is_set():
            callee = None

            if self.redis_connection.exists(config.REDIS_INDEX):
                callee = self.redis_connection.lpop(config.REDIS_INDEX)

            if not callee:
                logging.info('No callees to call - sleeping for %s seconds' % config.SLEEP_TIME)
                time.sleep(config.SLEEP_TIME)
                continue

            self._call(callee)
            break

    @run_in_green_thread
    def _call(self, sip_uri):
        """
        Initializes a call a given SIP URI.

        Parameters
        ----------
        sip_uri : str
            The SIP URI to call.
        """
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

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        """
        Notification handler triggered after application start.

        Parameters
        ----------
        notification
            The notification.
        """
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

    def _NH_SIPApplicationDidEnd(self, notification):
        """
        Notification handler triggered after application end.

        Parameters
        ----------
        notification
            The notification.
        """
        self.ended.set()
        logging.info('Ended application')

    def _NH_SIPSessionDidStart(self, notification):
        """
        Notification handler triggered after session start.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.info('Session did start - starting WAV player')
        session = notification.sender
        audio_stream = session.streams[0]
        audio_stream.bridge.add(self.player)
        self.player.play()

    def _NH_SIPSessionWillEnd(self, notification):
        """
        Notification handler triggered before session end.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.info('Session will end - stopping WAV player')
        session = notification.sender
        audio_stream = session.streams[0]
        self.player.stop()
        audio_stream.bridge.remove(self.player)

    def _NH_WavePlayerDidEnd(self, notification):
        """
        Notification handler triggered after player ended.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.info('WAV player did stop - ending session')
        self.session.end()

    def _NH_SIPSessionDidFail(self, notification):
        """
        Notification handler triggered after session failure.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.error('SIP session failed - starting next call')
        self.next_call()

    def _NH_SIPSessionDidEnd(self, notification):
        """
        Notification handler triggered after session end.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.info('Session ended - starting next call')
        self.next_call()

    def _NH_SIPAccountRegistrationGotAnswer(self, notification):
        """
        Notification handler triggered after received answer for SIP account registration.

        Parameters
        ----------
        notification
            The notification.
        """
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
            self.next_call()

    def _NH_SIPAccountRegistrationDidSucceed(self, notification):
        """
        Notification handler triggered after successful SIP account registration.

        Parameters
        ----------
        notification
            The notification.
        """
        contact_header = notification.data.contact_header
        expires = notification.data.expires
        registrar = notification.data.registrar

        logging.info(
            'Registered contact "%s" for sip:%s at %s:%d \n'
            'Transport: %s \n'
            'Expires in %d seconds' %
            (contact_header.uri, self.account.id, registrar.address, registrar.port, registrar.transport, expires)
        )

    def _NH_SIPAccountRegistrationDidFail(self, notification):
        """
        Notification handler triggered after failed SIP account registration.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.error(
            'SIP registration failed for account %s \n'
            'Error: %s' %
            (self.account.id, notification.data.error)
        )
        self.next_call()

    def _NH_SIPAccountRegistrationDidEnd(self, notification):
        """
        Notification handler triggered after ended SIP account registration.

        Parameters
        ----------
        notification
            The notification.
        """
        logging.info('SIP registration ended')
