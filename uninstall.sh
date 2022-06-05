#!/bin/sh

# So all loops can run with sudo the script itself should be run as sudo.
# If not, potentially long write times could leave disks at idle for long stretches while waiting for sudo password.
if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        exit
fi

echo "What OS are you running on?"
echo "1 = TrueNAS CORE"
echo "2 = Proxmox"
echo "3 = pfSense"
read -p "My OS: " USER_OS
case $USER_OS in
    1) echo "You selected TrueNAS CORE" ;;
    2) echo "You selected Proxmox" ;;
    3) echo "You Selected pfSense" ;;
    *) echo "You didn't enter a proper selection, try again please." ;;
esac

echo "If you selected incorrectly, Ctrl+C now in next 5 seconds!"
sleep 5

if [ "$USER_OS" = "1" ]; then
    echo "Stopping the script now."
    /root/fan-control/fan-control.sh stop
    echo "************************"
    echo "* USER ACTION REQUIRED *"
    echo "************************"
    echo "Go to the TrueNAS Core WebUI, log in, go to following menus:"
    echo "Tasks -> Init/Shutdown Scripts"
    echo "Remove the task you created to start script on boot."
    echo "You are now stopped and it won't auto start on boot. If you'd like, run the following command to remove:"
    echo "rm -r /root/fan-control/"
fi

if [ "$USER_OS" = "2" ]; then
    echo "stopping fan-control"
    systemctl stop fan-control.service
    sleep 2
    systemctl status fan-control.service
    echo "disabling fan-control.service"
    systemctl disable fan-control.service
    echo "reloading daemons"
    systemctl daemon-reload
    echo "removing service file"
    rm /etc/systemd/system/fan-control.service
    echo "You are now stopped and it won't auto start on boot. If you'd like, run the following command to remove:"
    echo "rm -r /root/fan-control/"    
fi

if [ "$USER_OS" = "3" ]; then
    echo "Stopping the script now."
    /root/fan-control/fan-control.sh stop
    echo "Removing rc.d file"
    rm /usr/local/etc/rc.d/fan-control.sh
    echo "You are now stopped and it won't auto start on boot. If you'd like, run the following command to remove:"
    echo "rm -r /root/fan-control/"
fi

