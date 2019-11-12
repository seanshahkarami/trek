from glob import glob
from serial import Serial
from threading import Thread, Event
from queue import Queue
from time import sleep, time
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
            sleep(1)


csq_marginal = 9
csq_ok = 14
csq_good = 19
csq_excellent = 30


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
    display.append('\033[0m] {} / {}'.format(csq, csq_excellent))
    return ''.join(display)


def log_task(messages):
    with open('data.log', 'a') as logfile:
        latest_csq = 0
        latest_gps_time = ''
        latest_gps_lat = ''
        latest_gps_lon = ''

        while True:
            msg = messages.get()

            # log lines for later
            if msg.startswith('+CSQ') or msg.startswith('$GPGGA'):
                print(int(time()), msg, file=logfile)

            match = re.search(r'CSQ.*?(\d+),(\d+)', msg)

            if match is not None:
                latest_csq = int(match.group(1))

            if msg.startswith('$GPGGA'):
                fields = msg.split(',')
                latest_gps_time = fields[1]
                latest_gps_lat = '{} {}'.format(
                    round(float(fields[2]), 3), fields[3])
                latest_gps_lon = '{} {}'.format(
                    round(float(fields[4]), 3), fields[5])

            # draw ui
            print('\033[H')
            print('GPS Time:', latest_gps_time)
            print('GPS Lat:', latest_gps_lat)
            print('GPS Lon:', latest_gps_lon)
            print('CSQ:', make_csq_display(latest_csq))


def main():
    messages = Queue()
    done = Event()

    devices = glob('/dev/cu.usbmodem*01')

    if len(devices) < 2:
        print('Could not find at least 2 serial devices.')
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