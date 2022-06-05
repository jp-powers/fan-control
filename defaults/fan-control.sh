#!/bin/sh

PIDFILE="/root/fan-control/fan-control.pid"

# This file provides start, stop, and restart options for fan-control.py

name=fan-control

rc_start() {
    echo "Starting Fan Control..."
    /root/fan-control/fan-control.py & echo $! > $PIDFILE
}

rc_stop() {
    echo "Stopping Fan Control..."
    /usr/bin/pkill -F $PIDFILE
    /bin/sleep 5
}

case $1 in
    start)
        rc_start
	;;
    stop)
        rc_stop
	;;
    restart)
        rc_stop
        rc_start
        ;;
esac
