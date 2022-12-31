#!/bin/sh

# Script should be run as sudo as we're writing to /root
if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        exit
fi

# set some variables for the python shebangs to each OS
TRUENASSHEBANG="#!/usr/local/bin/python3"
PROXMOXSHEBANG="#!/usr/bin/python3"
PFSENSESHEBANG="#!/usr/local/bin/python3.8"

function check_script_exec () {
    if [ $(stat -c "%a" /root/fan-control/gen-config.py) = "755" ]; then
        echo "gen-config.py has proper permissions"
    else
        echo "gen-config.py did not get proper permissions, please manually run the following!"
        echo "chmod 755 /root/fan-control/gen-config.py"
    fi
    if [ $(stat -c "%a" /root/fan-control/fan-control.py) = "755" ]; then
        echo "fan-control.py has proper permissions"
    else
        echo "fan-control.py did not get proper permissions, please manually run the following!"
        echo "chmod 755 /root/fan-control/fan-control.py"
    fi
}

echo "What OS are you installing on?"
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
    echo "creating fan-control.py"
    echo $TRUENASSHEBANG > /root/fan-control/fan-control.py
    cat /root/fan-control/defaults/fan-control.py | tail -n+2>> /root/fan-control/fan-control.py
    echo "creating gen-config.py"
    echo $TRUENASSHEBANG > /root/fan-control/gen-config.py
    cat /root/fan-control/defaults/gen-config.py.truenas | tail -n+2>> /root/fan-control/gen-config.py
    echo "copying fan-control.sh to /root/fan-control/"
    echo "This is used to start/stop/restart the script. Alongside nohup it will survive thru shell session closure."
    cp /root/fan-control/defaults/fan-control.sh /root/fan-control/fan-control.sh
    echo "making appropriate files executable"
    chmod 755 /root/fan-control/gen-config.py /root/fan-control/fan-control.py /root/fan-control/fan-control.sh
    check_script_exec
    echo "Starting nano to edit the config file generator that now. Ctrl+X when complete to save and exit."
    echo "(sleeping for 10 seconds to cancel if wanted)"
    sleep 10
    nano /root/fan-control/gen-config.py
    echo "Executing gen-config.py to generate the config file"
    /root/fan-control/gen-config.py
    echo "************************"
    echo "* USER ACTION REQUIRED *"
    echo "************************"
    echo "Go to the TrueNAS Core WebUI, log in, go to following menus:"
    echo "Tasks -> Init/Shutdown Scripts"
    echo "Add a task (top right)"
    echo "Description: fan-control"
    echo "Set Type as Command"
    echo "Set Command as: /root/fan-control/fan-control.sh start"
    echo "Set When to Post Init, and enable it then save." 
    echo "fan-control.py is setup. Starting the script now."
    nohup /root/fan-control/fan-control.sh start & # starting this way so it won't stop when exiting the shell
fi

if [ "$USER_OS" = "2" ]; then
    echo "installing requirements via apt. If already installed apt will skip on it's own."
    apt install ipmitool lm-sensors
    echo "creating fan-control.py"
    echo $PROXMOXSHEBANG > /root/fan-control/fan-control.py
    cat /root/fan-control/defaults/fan-control.py | tail -n+2>> /root/fan-control/fan-control.py
    echo "creating gen-config.py"
    echo $PROXMOXSHEBANG > /root/fan-control/gen-config.py
    cat /root/fan-control/defaults/gen-config.py.proxmox | tail -n+2>> /root/fan-control/gen-config.py
    echo "copying service file to /root/fan-control/"
    echo "If you'd like to make changes to it/how it runs you can do that here"
    cp /root/fan-control/defaults/fan-control.service /root/fan-control/fan-control.service
    echo "making appropriate files executable"
    chmod 755 /root/fan-control/gen-config.py /root/fan-control/fan-control.py
    check_script_exec
    echo "Starting nano to edit the config file generator that now. Ctrl+X when complete to save and exit."
    echo "(sleeping for 10 seconds to cancel if wanted)"
    sleep 10
    nano /root/fan-control/gen-config.py
    echo "Executing gen-config.py to generate the config file"
    /root/fan-control/gen-config.py
    echo "Creating link to service file"
    ln -s /root/fan-control/fan-control.service /etc/systemd/system/fan-control.service
    echo "reloading daemons"
    systemctl daemon-reload
    echo "enabling fan-control.service"
    systemctl enable fan-control.service
    echo "starting fan-control"
    systemctl restart fan-control.service
    sleep 2
    systemctl status fan-control.service
fi

if [ "$USER_OS" = "3" ]; then
    echo "creating fan-control.py"
    echo $PFSENSESHEBANG > /root/fan-control/fan-control.py
    cat /root/fan-control/defaults/fan-control.py | tail -n+2>> /root/fan-control/fan-control.py
    echo "creating gen-config.py"
    echo $PFSENSESHEBANG > /root/fan-control/gen-config.py
    cat /root/fan-control/defaults/gen-config.py.pfsense | tail -n+2>> /root/fan-control/gen-config.py
    echo "copying fan-control.sh to /root/fan-control/"
    echo "This is used to start/stop/restart the script. Alongside nohup it will survive thru shell session closure."
    cp /root/fan-control/defaults/fan-control.sh /root/fan-control/fan-control.sh
    echo "making appropriate files executable"
    chmod 755 /root/fan-control/gen-config.py /root/fan-control/fan-control.py /root/fan-control/fan-control.sh
    check_script_exec
    echo "Starting nano to edit the config file generator that now. Ctrl+X when complete to save and exit."
    echo "(sleeping for 10 seconds to cancel if wanted)"
    sleep 10
    nano /root/fan-control/gen-config.py
    echo "Executing gen-config.py to generate the config file"
    /root/fan-control/gen-config.py
    echo "Copying fan-control.sh to /usr/local/etc/rc.d/ so it can auto start on reboots"
    cp fan-control.sh /usr/local/etc/rc.d/
    echo "fan-control.py is setup. Starting the script now."
    nohup /root/fan-control/fan-control.sh start & # starting this way so it won't stop when exiting the shell
fi
