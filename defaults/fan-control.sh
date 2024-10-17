#!/bin/sh

PIDFILE="/root/fan-control/fan-control.pid"

# This file provides start, stop, and restart options for fan-control.py

name=fan-control

rc_start() {

  if ! output=$(pgrep -F $PIDFILE 2>/dev/null)
  then
    echo "Starting Fan Control..."
    /root/fan-control/fan-control.py & echo $! > $PIDFILE
  else
    echo "Fan control already running"
  fi

}

rc_stop() {
    echo "Stopping Fan Control..."
    /usr/bin/pkill -F $PIDFILE
    /bin/sleep 5
    rm $PIDFILE
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
