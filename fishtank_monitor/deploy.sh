sudo killall python3.2
cd /home/pi/FishtankMonitor/fishtank_monitor/sketchbook/fish_tank_display/
ino build -m alamode
ino upload -p /dev/ttyS0 -m alamode
cd 
sudo /home/pi/python3.2/bin/activate
cd /home/pi/FishtankMonitor/fishtank_monitor/
sudo /home/pi/python3.2/bin/python3.2 fishtank_monitor.py &


