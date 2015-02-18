import unittest
import fishtank_monitor as ftm
import threading
import time

class FakeSerial():

    def __init__(self, lines):
        self.lines = lines

    def readline(self):
        try:
            ret = self.lines[0]
            self.lines = self.lines[1:]
            return ret
        except:
            return b''

SLEEP_INT = 0.25

class TestFishTankMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ftm.config_filename = './test/fishtank_monitor.cfg'
        ftm.read_config()

    def setUp(self):
        self.monitor = threading.Thread(target = ftm.monitor_serial)
        self.monitor.daemon = True
        ftm.monitor_serial.stop = False
        ftm.time_last_notified = 0
        ftm.ph = None
        ftm.temperature = None
        ftm.ard = None

    def test_basic(self):
        lines = [b'T:21.0\nP:6.5\n']
        ftm.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(ftm.ph, 6.5)
        self.assertEqual(ftm.temperature, 21.0)
        self.assertEqual(ftm.time_last_notified, 0)

    def test_odd_prefix(self):
        lines = [b'.0\nP:5.5\nT:21.0\nP:6.5\n']
        ftm.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(ftm.ph, 6.5)
        self.assertEqual(ftm.temperature, 21.0)
        self.assertEqual(ftm.time_last_notified, 0)

    def test_odd_pre_and_postfix(self):
        lines = [b'.0\nP:5.5\nT:21.0\nP:6.5\nT:20.5\nP:']
        ftm.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(ftm.ph, 6.5)
        self.assertEqual(ftm.temperature, 20.5)
        self.assertEqual(ftm.time_last_notified, 0)

    def test_bad_temp(self):
        lines = [b'T:1.0\nP:6.5\n']
        ftm.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        ftm.notify_if_required()
        self.assertEqual(ftm.ph, 6.5)
        self.assertEqual(ftm.temperature, 1.0)
        self.assertNotEqual(ftm.time_last_notified, 0)

    def test_bad_ph(self):
        lines = [b'T:21.0\nP:5.5\n']
        ftm.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        ftm.notify_if_required()
        self.assertEqual(ftm.ph, 5.5)
        self.assertEqual(ftm.temperature, 21.0)
        self.assertNotEqual(ftm.time_last_notified, 0)

    def test_config(self):
        self.assertEqual(ftm.SMTP_host, 'smtphost')
        self.assertEqual(ftm.SMTP_port, 0)
        self.assertEqual(ftm.SMTP_user, 'username')
        self.assertEqual(ftm.SMTP_password, 'password')
        self.assertEqual(ftm.SMTP_use_ttls, True)
        self.assertEqual(ftm.send_reports_interval, 0)
        self.assertEqual(ftm.send_warnings_interval, 0)
        self.assertEqual(ftm.email_to_address, 'you@domain.com')
        self.assertEqual(ftm.email_from_address, 'pi@domain.com')


    def tearDown(self):
        ftm.monitor_serial.stop = True
        self.monitor = None

unittest.main()
