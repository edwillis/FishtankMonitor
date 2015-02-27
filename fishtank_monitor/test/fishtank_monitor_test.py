import unittest
import fishtank_monitor as ftm
import config
import notifications
import serial_monitor
import scheduler
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
        config.config_filename = './test/fishtank_monitor.cfg'
        config.read_config()

    def setUp(self):
        self.monitor = serial_monitor.SerialMonitor(config.serial_device)
        self.monitor.stop = False
        notifications.time_last_warned = 0
        self.monitor.ph = None
        self.monitor.temperature = None
        self.monitor.ard = None

    def test_basic(self):
        lines = [b'T:21.0\nP:6.5\n']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_odd_prefix(self):
        lines = [b'.0\nP:5.5\nT:21.0\nP:6.5\n']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_odd_pre_and_postfix(self):
        lines = [b'.0\nP:5.5\nT:21.0\nP:6.5\nT:20.5\nP:']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 20.5)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_bad_temp(self):
        lines = [b'T:1.0\nP:6.5\n']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        notifier = notifications.NotifyWarnings()
        notifier(ftm.conn, self.monitor)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 1.0)
        self.assertNotEqual(notifier.time_last_warned, 0)

    def test_bad_ph(self):
        lines = [b'T:21.0\nP:5.5\n']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        notifier = notifications.NotifyWarnings()
        notifier(ftm.conn, self.monitor)
        self.assertEqual(self.monitor.ph, 5.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertNotEqual(notifier.time_last_warned, 0)

    def test_inform(self):
        notifier = notifications.NotifyInformationalReports()
        notifier(ftm.conn, self.monitor)
        self.assertNotEqual(notifier.time_last_informed, 0)

    def test_notify_calibration(self):
        now = time.time()
        then = now - (30*24*60*60 + 1)
        config.last_calibration = then
        notifier = notifications.NotifyCalibration()
        notifier(ftm.conn, self.monitor)
        self.assertNotEqual(then, config.last_calibration)

    def test_config(self):
        self.assertEqual(config.serial_device, '/dev/ttyS0')
        self.assertEqual(config.SMTP_host, 'smtphost')
        self.assertEqual(config.SMTP_port, 0)
        self.assertEqual(config.SMTP_user, 'username')
        self.assertEqual(config.SMTP_password, 'password')
        self.assertEqual(config.SMTP_use_ttls, True)
        self.assertEqual(config.send_reports_interval, 0)
        self.assertEqual(config.send_warnings_interval, 0)
        self.assertEqual(config.email_to_address, 'you@domain.com')
        self.assertEqual(config.email_from_address, 'pi@domain.com')
        self.assertEqual(config.months_between_calibrations, 0)
        self.assertEqual(config.x10_retries, 3)
        self.assertEqual(config.x10_light_code, 'i8')
        self.assertEqual(len(config.lights_on_times), 2)
        self.assertEqual(len(config.lights_off_times), 2)
        self.assertEqual(config.lights_on_times[0], '7:00')
        self.assertEqual(config.lights_on_times[1], '15:00')
        self.assertEqual(config.lights_off_times[0], '11:00')
        self.assertEqual(config.lights_off_times[1], '22:30')

    def test_scheduler_time_parsing(self):
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(''))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(' '))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(' :'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(': '))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(' :  '))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string('1:1'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(' 1:00'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string(' 10:00'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string('10:00 '))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string('10:000'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string('10:0'))
        self.assertFalse(scheduler.LightScheduler._is_valid_time_string('100:00'))
        self.assertTrue(scheduler.LightScheduler._is_valid_time_string('1:10'))
        self.assertTrue(scheduler.LightScheduler._is_valid_time_string('01:10'))
        self.assertTrue(scheduler.LightScheduler._is_valid_time_string('11:11'))

    def test_scheduler(self):
        old_validator = scheduler.LightScheduler._is_valid_time_string
        old_config_on_times = config.lights_on_times
        old_config_off_times = config.lights_off_times
        try:
            scheduler.LightScheduler._is_valid_time_string = lambda x:  True
            now = time.time()
        finally:
            scheduler.LightScheduler._is_valid_time_string = old_validator
            config.lights_on_times = old_config_on_times
            config.lights_off_times = old_config_off_times

    def tearDown(self):
        self.monitor.stop = True
        self.monitor = None

unittest.main()
