import smtplib
import pygal
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from log import get_logger
import config

logger = get_logger(__name__)

class NotifierBase:

    def __call__(self, conn, monitor):
        pass

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

class NotifyWarnings(NotifierBase):

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

_notifiers = None

def get_notifiers():
    global _notifiers
    if _notifiers is None:
        _notifiers = [NotifyCalibration(), NotifyInformationalReports(), NotifyWarnings()]
    return _notifiers
