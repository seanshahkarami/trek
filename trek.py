from glob import glob
from serial import Serial
from threading import Thread, Event
from queue import Queue
import time
import re
import sys


def device_task(device, messages, done):
    with Serial(device, 115200, timeout=1) as ser:
        while True:
            ser.write(b'AT+CSQ\r\n')
            while True:
                if done.is_set():
                    return
                try:
                    line = ser.readline().decode()
                except UnicodeDecodeError:
                    continue
                if len(line) == 0:
                    break
                messages.put(line.strip())
            time.sleep(1)


csq_marginal = 9
csq_ok = 14
csq_good = 19
csq_excellent = 30


def csq_name(csq):
    if csq <= csq_marginal:
        return 'marginal'
    elif csq <= csq_ok:
        return 'ok'
    elif csq <= csq_good:
        return 'good'
    elif csq <= csq_excellent:
        return 'excellent'
    else:
        return 'searching'


def make_csq_display(csq):
    display = []

    # reset color and add opening [
    display.append('\033[0m[')

    for i in range(1, csq_excellent + 1):
        # set color
        if i <= csq_marginal:
            display.append('\033[31m')
        elif i <= csq_ok:
            display.append('\033[33m')
        elif i <= csq_good:
            display.append('\033[32m')
        elif i <= csq_excellent:
            display.append('\033[34m')

        # add marker
        if i <= csq:
            display.append('#')
        else:
            display.append('.')

    # reset color and add closing ]
    display.append('\033[0m] {} / {} ({})'.format(csq,
                                                  csq_excellent, csq_name(csq)))
    return ''.join(display)


def log_task(messages):
    logpath = 'data.log'
    with open(logpath, 'a') as logfile:
        latest_csq = 0
        latest_gps_time = ''
        latest_gps_lat = ''
        latest_gps_lon = ''
        time_since_modem_data = time.monotonic()
        time_since_gps_data = time.monotonic()

        while True:
            msg = messages.get()

            # log lines for later
            if msg.startswith('+CSQ') or msg.startswith('$GPGGA'):
                print(int(time.time()), msg, file=logfile)

            match = re.search(r'CSQ.*?(\d+),(\d+)', msg)

            if match is not None:
                latest_csq = int(match.group(1))
                time_since_modem_data = time.monotonic()

            if msg.startswith('$GPGGA'):
                fields = msg.split(',')
                latest_gps_time = fields[1]
                try:
                    lat = round(float(fields[2])/100, 3)
                    lon = round(float(fields[4])/100, 3)
                    latest_gps_lat = '{} {}'.format(lat, fields[3])
                    latest_gps_lon = '{} {}'.format(lon, fields[5])
                    time_since_gps_data = time.monotonic()
                except ValueError:
                    pass

            if time.monotonic() - time_since_gps_data >= 30:
                latest_gps_lat = ''
                latest_gps_lon = ''

            # draw ui
            print('\033[2J')
            print('\033[H')
            print('GPS Time:', latest_gps_time)
            print('GPS Lat:', latest_gps_lat)
            print('GPS Lon:', latest_gps_lon)
            print('CSQ:', make_csq_display(latest_csq))
            print('Log File:', logpath)
            print()
            print('Time Since GPS Data: {}s ago'.format(
                round(time.monotonic() - time_since_gps_data)))
            print('Time Since Modem Data: {}s ago'.format(
                round(time.monotonic() - time_since_modem_data)))


def main():
    messages = Queue()
    done = Event()

    devices = glob('/dev/cu.usbmodem*01')

    if len(devices) < 2:
        print('Could not find at least 2 serial devices. Please make sure a modem and GPS are connected.')
        sys.exit(1)

    for device in devices:
        t = Thread(target=device_task, args=(device, messages, done))
        t.start()

    try:
        log_task(messages)
    finally:
        done.set()


if __name__ == '__main__':
    main()
