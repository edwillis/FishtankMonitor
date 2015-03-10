import sys
import os
import unittest
import fishtank_monitor as ftm
import config
import notifications
import serial_monitor
import scheduler
import threading
import time
import datetime
import dateutil

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
        ''' @test Test parsing the serial json object in a perfect case'''

        lines = [b'{"temperature":21.0, "ph":6.5}']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_odd_prefix(self):
        ''' @test Test parsing the serial json object when there is unparseable data before
        the valid json'''

        lines = [b'.0, "ph" :5.5}\n{"temperature":21.0, "ph":6.5}']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_odd_pre_and_postfix(self):
        ''' @test Test parsing the serial json object when there is unparseable data before
        and after the valid json'''

        lines = [b'.0, "ph":5.5}\n{"temperature":21.0, "ph":6.5}\n{"temperature":20.5, "ph":4.0']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertEqual(notifications.time_last_warned, 0)

    def test_bad_temp(self):
        ''' @test Test that notifications are triggered when an out of bounds temperature
        reading is seen'''

        lines = [b'{"temperature":1.0, "ph":6.5}\n']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        notifier = notifications.NotifyWarnings()
        notifier(ftm.conn, self.monitor)
        self.assertEqual(self.monitor.ph, 6.5)
        self.assertEqual(self.monitor.temperature, 1.0)
        self.assertNotEqual(notifier.time_last_warned, 0)

    def test_bad_ph(self):
        ''' @test Test that notifications are triggered when an out of bounds ph
        reading is seen'''

        lines = [b'{"temperature":21.0, "ph":5.5}']
        self.monitor.ard = FakeSerial(lines)
        self.monitor.start()
        time.sleep(SLEEP_INT)
        notifier = notifications.NotifyWarnings()
        notifier(ftm.conn, self.monitor)
        self.assertEqual(self.monitor.ph, 5.5)
        self.assertEqual(self.monitor.temperature, 21.0)
        self.assertNotEqual(notifier.time_last_warned, 0)

    def test_inform(self):
        ''' @test Test informational notifications trigger when explicitly called'''

        notifier = notifications.NotifyInformationalReports()
        notifier(ftm.conn, self.monitor)
        self.assertNotEqual(notifier.time_last_informed, 0)

    def test_notify_calibration(self):
        ''' @test Test the calibration notifications are triggered when called and
        when the elapsed time has expired'''

        now = time.time()
        then = now - (30*24*60*60 + 1)
        config.last_calibration = then
        notifier = notifications.NotifyCalibration()
        notifier(ftm.conn, self.monitor)
        self.assertNotEqual(then, config.last_calibration)

    def test_config(self):
        ''' @test Exhaustively test the config file parsing and resulting data'''

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
        self.assertEqual(config.daylight_tz, -240)
        self.assertEqual(config.standard_tz, -300)
        self.assertEqual(config.ph_pin, 'A2')
        self.assertEqual(config.temperature_pin, 'A1')

    def test_scheduler_time_parsing(self):
        ''' @test Test the time series parsing for the LightScheduler '''

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
        ''' @test Test the scheduler calls the registered functors on specified time
        intervals.  This test is timeconsuming and will not be run unless the
        environment variable RUN is set to all.'''

        if os.environ.get('RUN') != 'all':
            print("\nskipping test_scheduler - use test.sh all to run")
            return

        def new_call(self):
            if not hasattr(self, 'count'):
                self.count = 0
            self.count += 1

        old_validator = scheduler.LightScheduler._is_valid_time_string
        old_call = scheduler.LightScheduler.__call__
        old_config_on_times = config.lights_on_times
        old_config_off_times = config.lights_off_times
        try:
            scheduler.LightScheduler._is_valid_time_string = lambda x, y:  True
            scheduler.LightFunctor.__call__ = new_call
            times = []
            for i in range(3):
                times.append((datetime.datetime.now() + datetime.timedelta(minutes = 1+i)).strftime("%H:%M"))
            config.lights_on_times = times
            config.lights_off_times = times
            s = scheduler.LightScheduler()
            s.start()
            time.sleep(4*60)
            self.assertEqual(s._on.count, 3)
            self.assertEqual(s._off.count, 3)
        finally:
            scheduler.LightScheduler._is_valid_time_string = old_validator
            scheduler.LightFunctor.__call__ = old_call
            config.lights_on_times = old_config_on_times
            config.lights_off_times = old_config_off_times

    def tearDown(self):
        self.monitor.stop = True
        self.monitor = None

unittest.main()
