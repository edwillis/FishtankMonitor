## @package notifications
#  Functor class hierarchy responsible for user notification of significant events
#
#  This module defines a class hierarchy of functors used to send emailed
#  communications to the user when:
#
#  * conditions in the tank become unsafe
#  * the user-specified informational period has arrived
#  * it's time to redo the ph sensor calibration
#
#  @author  Ed Willis
#  @copyright Ed Willis, 2015, all rights reserved
#  @license  This software is released into the public domain

import smtplib
import pygal
import time
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from log import get_logger
import config

logger = get_logger(__name__)

## The notification base class
#
#  Defines email helper methods and a common template method functor
#  interface for callers to trigger evaluation of the notification
#  schedule and emailed communications should the conditions meet the
#  notifier-specific criteria.
class NotifierBase:

    ## The functor method to be provided by derived classes
    #
    #  @param conn the database connection to use if needed
    #  @param monitor the serial monitor from which to see the current
    #         temperature and ph
    def __call__(self, conn, monitor):
        pass

    ## Email sending helper method
    #
    #  Using the configuration specified in the config file, open a
    #  connection to the user's mail server and send the argument email
    #  using the user's credentials.
    #
    # @param [in] email the MIMETest object to send
    @staticmethod
    def _send_email(email):
        s = smtplib.SMTP(config.SMTP_host, config.SMTP_port)
        s.ehlo()
        if config.SMTP_use_ttls:
            s.starttls()
        s.ehlo()
        s.login(config.SMTP_user, config.SMTP_password)
        logger.info("sending emails")
        s.sendmail(config.email_to_address, [config.email_to_address], email.as_string())
        s.quit()

## Send emails when bad temperature or ph readings are seen
#
#  Examine the current ph and temperature values and warn the user by email if
#  they exceed limits
class NotifyWarnings(NotifierBase):

    ## The last time we warned the user by email
    time_last_warned = 0

    def __call__(self, conn, monitor):
        ph_bad = False
        temp_bad = False
        msg = ''
        if monitor.ph and (monitor.ph < 6.0 or monitor.ph > 8.0):
            logger.warning("ph is bad: %r" %monitor.ph)
            ph_bad = True
        if monitor.temperature and (monitor.temperature < 20 or monitor.temperature > 28):
            logger.warning("temperature is bad: %r" %monitor.temperature)
            temp_bad = True
        if ph_bad:
            msg += 'Fishtank PH level is unsafe:  %r\n'%monitor.ph
            logger.warn("unsafe ph, will email")
        if temp_bad:
            msg += 'Fishtank temperature is unsafe:  %r\n'%monitor.temperature
            logger.warn("unsafe temperature, will email")
        if msg and time.time() - self.time_last_warned > config.send_warnings_interval:
            self.time_last_warned = time.time()
            logger.info("setting time_last_warned to %r" %self.time_last_warned)
            if config.send_warnings_interval > 0:
                logger.info("sending warning email")
                msg = MIMEText(msg)
                msg['Subject'] = 'Fishtank monitor warning'
                msg['From'] = config.email_from_address
                msg['To'] = config.email_to_address
                self._send_email(msg)

## Send the user periodic informational reports (with graphs)
#
#  Determine how long it's been since we sent the user an informational
#  report if one is due.  Include a graphic plotting ph and temperature
#  values over time.
class NotifyInformationalReports(NotifierBase):

    time_last_informed = 0

    def __call__(self, conn, monitor):
        if time.time() - self.time_last_informed > config.send_reports_interval:
            self.time_last_informed = time.time()
            logger.info("setting time_last_informed to %r" %self.time_last_informed)
            if config.send_reports_interval > 0:
                logger.info("sending daily report (time_last_informed is %r)"%self.time_last_informed)
                chart = pygal.DateY(title='Fishtank PH and Temperature over time', x_label_rotation=20)
                values = conn.execute('select ph, temp, time from measurements order by time desc limit 1000').fetchall()
                ph_values = [ i[0] for i in values ]
                temp_values = [ i[1] for i in values ]
                time_values = [ i[2] for i in values ]
                timespan = time_values[0] - time_values[-1]
                ph_values = list(zip(time_values, ph_values))
                temp_values = list(zip(time_values, temp_values))
                chart.add('PH', ph_values)
                logger.debug("PH:  %r" %ph_values)
                chart.add('Temperature', temp_values)
                logger.debug("Temperature:  %r" %temp_values)
                chart.x_label_format = "%Y-%m-%d"
                chart.render_to_file('chart.svg')
                msg = MIMEMultipart()
                msg.attach(MIMEText('Daily measurements from your fishtank monitor.'))
                msg['Subject'] = 'Fishtank status'
                msg['From'] = config.email_from_address
                msg['To'] = config.email_to_address
                with open('chart.svg', 'rb') as f:
                    msg.attach(MIMEImage(f.read(), name='chart.svg', _subtype="svg"))
                self._send_email(msg)

## Send the user reminder emails when their PH monitor is due for calibration
class NotifyCalibration(NotifierBase):

    def __call__(self, conn, monitor):
        now = time.time()
        logger.debug("NotifyCalibration about to check if it's time")
        if (now - config.last_calibration)/(30*24*60*60) > config.months_between_calibrations:
            logger.info("calibration period expired - setting last calibration  to %r" %now)
            config.last_calibration = now
            if config.months_between_calibrations > 0:
                logger.info("calibration noifications are enabled, writing last cal to db")
                conn.execute('insert into settings values (%r)' %config.last_calibration)
                conn.commit()
                logger.info("it's time to calibrate, sending email")
                msg = MIMEText(msg)
                msg['Subject'] = 'Fishtank ph monitor calibration is due'
                msg['From'] = config.email_from_address
                msg['To'] = config.email_to_address
                self._send_email(msg)

## Global list of notitification functors
_notifiers = None

## Lazy instantiator for the global list of functors
def get_notifiers():
    global _notifiers
    if _notifiers is None:
        _notifiers = [NotifyCalibration(), NotifyInformationalReports(), NotifyWarnings()]
    return _notifiers
