# fan-control

The intent of this script package to provide a (relatively) simple means of controlling fan speed via a fan curve. It is one monolithic script to manage TrueNAS Core, pfSense, and Proxmox.
It includes a means of running as a service, including reading the configuration regularly for changes so you can make adjustments without needing to reboot/start the script in odd ways on different platforms.

# Some explanation is required

There are a number of specific tools like this for each of the platforms, but I've been unsatisfied with most and the one I do like was in Ruby, which isn't quite as cross-platform as I'd like. I recreated the script in Python, added a means of checking HDD temps, and then made necessary changes depending on platform for checking things like CPU temps and whatnot.

There are a number of areas that, in my incredibly amateur opinion, are incredibly amateur. My goal for sharing it is to hopefully get it out there so those with a better understanding of these platforms and Python can take it and make it better. If not, hey, I know it works (or at least it seems to work) for me.

# TrueNAS Core Caveat

Due to how TrueNAS works, setting the script to start on boot needs to be performed by the user. If you'd set that up and would then like to disable the script from auto-starting, you also need to do that on your own.

It might be possible to do this via the install/uninstall shell scripts but I didn't do much research into it as from what I can tell the other IPMI fan control scripts don't do anything like this either, so I kind of assume it's not a thing.

# Tested Against

My personal machines are as follows:
1. pfSense - Supermicro X11SSH-LN4F in a Supermicro CSE-512F-350B chassis
1. TrueNAS Core - Supermicro X10DRH-C in a Supermicro 36 3.5" + 2 2.5" chassis (not sure of exact model)
1. Proxmox - Dell Poweredge R730xd

Depending on your setup editing the config file appropriately should just work, but it was written to work against these systems and thus I can't guarantee it'll work against anything different.

# Install / Uninstall

Unzip everything into /root/fan-control
execute the install.sh script, follow the instructions. It will copy the appropriate files for your OS, mark as executable, do what it can so things auto start on boot, open the config generator for you, execute it, and start the script.

When the config generator runs, take a look at all the options. The defaults are what I use on my respective systems, but you may desire different settings, specifically the fan curves.

To uninstall, there is a matching uninstall.sh script. However, I do not script the removal of /root/fan-control, I only do what I can to stop the script and either remove the auto-start components or instruct you how to.

# Long term use

## Changing the configuration

Whenever you want to change something like adding/removing a drive to monitor, changing the fan curve, etc., you can directly edit config.ini and the changes will be recognized by the script and implemented on the next loop. I recommend "testing" changes by changing config.ini, and when you're happy you can edit gen-config.py. Doing it this way ensures that if you make a mistake in the config.ini you can execute your gen-config.py with it's "known good" settings and it will regenerate config.ini for you.

## Start/stop/restart

I've implemented some changes so the log should now capture more traceback errors and other critical exceptions. If you ever feel like you need to restart the script, you can do the following:

### Proxmox

Executing the following command will start the service. This may be necessary if you were experimenting with changes and needed to stop things.

    systemctl start fan-control.service

Executing the following command will stop the service. This may be necessary if you notice the fan-control.log being flooded with traceback reports.

    systemctl stop fan-control.service

Executing the following command will restart the service. This may be necessary if you notice the script just seems to have stalled out. Hopefully the new logging method will allow better tracing of why.

    systemctl restart fan-control.service


### TrueNAS Core / pfSense

As both TrueNAS Core and pfSense are based on FreeBSD, instead of using the systemd service we use rc.d. PfSense allows us to directly attach our fan-control.sh script to the system, but TrueNAS uses a static filesystem so instead we just leave the script alone.

Similar to the Proxmox, fan-control.sh supports start, stop, and restart. It records the PID of the python script when it is used to start it. Generally, just starting on boot as following the install.sh instructions should allow things to just work most of the time. However, if you do things without rebooting, you can use nohup as root to send the script to the background and out of session. We do it this way as otherwise the script can close when closing a session, such as exiting your SSH session.

Executing the following command will start the service. This may be necessary if you were experimenting with changes and needed to stop things.

    # nohup /root/fan-control/fan-control.sh start &

Executing the following command will stop the service. This may be necessary if you notice the fan-control.log being flooded with traceback reports.

    # nohup /root/fan-control/fan-control.sh stop &

Executing the following command will restart the service. This may be necessary if you notice the script just seems to have stalled out. Hopefully the new logging method will allow better tracing of why.

    # nohup /root/fan-control/fan-control.sh restart &

# TODO

In practice I've found that my TrueNAS CORE/pfSense rc.d services are not working fully as intended. I need to do some more investigation into how to do so properly. That said, the above commands for start/stop/restart do work independently from what I can tell.

I'd like to add a method for separating HDD and SSD temperatures and comparing appropariately. Mostly, I find that my current SK Hynix SSDs have a tendency to shoot up in temp briefly which causes annoying jumps in fan speed in bursts during things like monthly SMART Extended tests.

I'm hoping to find some time to rework the timing mechanics. Right now the script is essentially working as an "iterate/sleep timer" and while it works well enough for my needs it'll get riskier if the CPU timer is changes significantly. I have a rough idea of how to convert from the current mechanism to a "compare against the system clock" method but haven't had a chance to sit down and explore it further.

I ran into this issue briefly: When swapping drives (during a drive failure requiring a replacement swap for instance), the script crashed because a device it searched for was no longer there. With the changes to provide Python error logs to the fan-control.log the problem goes away mostly (the infinite loop is far more infinite), it also bloats the log wildly. I have an idea for doing an automated check for drives periodically, possibly triggered by such an error, so such issues are unlikely to occur.

The log as is mostly exists to help you understand what is causing bursts of higher speed. I'd like to spend some time at some point expanding on the logging. Specifically, in my experience, there are specific drives that will trigger the max temp, and writing out which drive it is would be helpful. Possibly also at a user specified frequency writing out a chart of drive temps would be helpful.

I'd like to reach a point where this is less monolithic and more modular. I'd like a means of detecting OS, potentially detecting the IPMI platform, and having individual modular components for each so it can grow/add platforms and OSs more easily. Some of this I know I could do now, but as is for just 2 IPMI platforms and 3 OS's (two of which are almost identical) I know how I'm doing things now works well enough.

I'd also like to rework the install/uninstall scripts to be a bit more user friendly. I'm fairly happy with out I setup gen-config.py but it might be interesting to build a means of having the install script "dump" a gen-config.py that is generated by the user during the install process.