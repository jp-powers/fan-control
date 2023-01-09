# Some Guidance on the Configuration Options

In the gen-config.py script that is generated during installation, there are a number of settings for you to change. Below is some guidance on what exactly each means and some suggestions to help you choose appropriately.

## system_info section

In this section you will be choosing some specifics about your system. This includes the operating system, IPMI type, singular or multiple fan zone selector, temperature focus, and a list of disks.

### Operating System - system_os

Currently the script supports Proxmox, TrueNAS CORE, and pfSense. Select the appropriate OS for your system.

NOTE: It's possible TrueNAS SCALE may work by selecting Proxmox as they are both Debian based but this is untested and may require some changes to work appropriately.

### IPMI - ipmi_type

Currently the script supports Dell iDRAC Gen 8 and SuperMicro X10 IPMI fan control. Use `"iDRAC_Gen08"` or `"SM_X10"` as needed.

NOTE: Both of these are generational, and it's very possible that if you have a Dell iDRAC Gen 7 or Gen 9 you can use Gen 8 (and similar for SuperMicro). However, this is untested right now. Generally speaking most manufacturers don't drastically change their IPMI raw commands significantly between generations, hence why I think it may work, but changes do happen and there's no guarantee it'll work.

### Fan Zones - single_zone

The script supports acting as a single fan zone or multiple zones. This variable is boolean, so set it to `True` or `False`. This is mostly a conceit for SuperMicro systems so users on Dell platforms will want to set this to True. Many SuperMicro motherboards work with numbered fan's (FAN1, FAN2, etc.) and lettered fans (FANA, FANB, etc.). These act as separate zones. The idea is numbered fans generally are the "system" (aka CPU and motherboard cooling) and lettered fans are peripherals (aka hard drives or GPUs). If you'd like to use the zones you can do by setting this variable to False.

### Temperature Focus - temp_focus

This setting allows you to tell the script to only care about the CPU temperature if you'd prefer. The available options are `"CPU"` or `"Both"`.

Depending on your system you may not care what your storage temperatures are. For example, on my pfSense server, the SSD mirror runs so cool there's no point in checking them. Some users may have storage that is (at least currently) undetectable by the script and may want to not check it at all.

I considered adding HDD as an option but decided against it as it seems like a bad idea to ignore the CPU temperatures entirely. For example, on my TrueNAS server the HDD's are almost always dictating the fan speed, but when performing certain regular maintenance tasks the CPU will run hotter and I'd rather the fans act accordingly. Even in a system without active CPU cooling it's likely the fans cooling the storage will have an impact on the CPU and you want to allow that cooling to happen when needed.

### Disk selector - disks

This is a python list of the disks you want the script to be working against. As the script utilizes smartctl to find disk temperatures it utilizes the system name for the disk. On Linux this will typically be sda, sdb, etc. On FreeBSD this will be da0, da1, etc. or ada0, ada1, etc.

I recommend using your OS's web interfaces to identify the disk names. As on both OS's these are found in /dev that is hard coded in the script so you only need to include the name. Beyond this, when making the list the only real "rules" are ensuring that each has quotes and there are commas between each except the last which should have no trailing comma.

Right now the script only supports drives that should show a temperature via the SMART value 194. If your disks don't have a temperature listed for value 194 don't list them here.

## Fan Curves

This section of the configuration is where you'll be setting the fan curve.

There are two separate fan curves, one for the CPU and one for storage. When looking at gen-config.py, you'll see a python list of lists. It's formatted to be as user readable as possible, but to help explain it a bit better outside of code try the following.

The way the script works is it will read what the current average temperature is, and then find the appropriate target fan speed based on these fan curves. Now, the current average temperature likely won't match the exact temperatures listed, so it performs some math to figure out what the target fan speed should be by looking at the fan curve, finding the temperature values above and below the current temperature, then doing some math to figure out what the target fan speed to should be based on that. So, for instance, if the following is your target fan curve:

| Current Temperature | Target Fan Speed |
|---------------------|------------------|
| 0                   | 0                |
| 25                  | 20               |
| 35                  | 20               |
| 40                  | 20               |
| 45                  | 30               |
| 50                  | 40               |
| 60                  | 50               |

The script will find your current average temperature, lets say it's 42C. 42 isn't in the list, so it takes 40 and 45 as those are there, sees the target fan speeds are 20 on one and 30 on the other, and does some math to find the right speed for the fans accordingly. If the current average is on the list, the math results in the target listed.

Now, some suggestions for how to use the fan curves for your system:

You'll have your own temperature ranges and target fan speeds that will be different from my own. To some degree, you'll need to figure that out on your own by using the script and deciding "No, that's too loud" or "wow that's running cooler than I thought" and changing things accordingly. It's very dependent on your own environment and that's a decision you need to make yourself. That said, in many systems there is a "floor" on fan speed. You'll notice in the example above there is a 0C 0 Fan speed listing, but from 25C to 40C the fan speed is 20. This is an example from a system I use that I found if I allow the fans to spin below 20% they "wobble" and it's incredibly noticeable to me as the server rack is ~10 feet behind my desk. Similarly, on my TrueNAS server, I set a "floor" fan speed a bit higher than necessary so the drives are a bit cooler than my ideal target to provide some "padding" in the event of spikes so they don't spin up as frequently due to bursts in activity.

Due to how the script reads the fan curve, you can add or remove as many entries from it as you want. Just make sure you match the surrounding formatting and ensure you go from lowest to highest.

Ultimately, this is very user/environment dependent area of the configuration. The best suggestion is ball park what you think you want, then keep adjusting it until you're happy.

## Maximum Temperatures - hdd_panic

This section of the configuration allows you set a maximum drive temperature to react to. In a large pool of disks, it's common for one or more disks to run at higher temperatures than others. Setting the `max_temp` sets a target temperature you want the drives to stay below, and the `panic_addition` is a "bonus" fan speed. If any one drive breeches the `max_temp` the script will figure out the appropriate speed from the curve then add the `panic_addition` to it. This allows the script to provide more cooling to help get the drive temperatures down further.

The `max_temp` value is somewhat more objective than other values you can set in this script, however it will be dependent on your drives. For all of my systems, I'm using drives where 50C is well within the safe operating temperatures, although it is somewhat high. Historically I know the general suggestion is 40C for spinning disks, but in the last decade there's been a lot of development in the hardware and while not ideal to run up to 50C many drives can handle it without significant issue. Similar can be said for SSDs. For my setup I use 50C as a `max_temp` because my hardware allows for it, and since my server rack is so close to my desk and I hear it all the time it's just uncomfortable to have a max temp much lower due to how frequently panic triggers. You can change it to reflect your own environment/comfort level.

It's also worth noting, you can easily adjust your fan curve to account for the panic_addition and set that value to 0. Also, as an example, if you're running many old disks or just want to be extra careful/really stretch their life, you may want to increase the `panic_addition` to help cool the drives that much faster.

## Temperature Detection Frequency - detect_timers

This section of the configuration allows you to set how frequently the script should check the CPU and the storage temperatures. Generally speaking I suggest leaving these as is. CPU temperatures can fluctuate greatly and rapidly so setting the CPU timer higher than 5 is ill advised, and I think many users would prefer leaving it at 1 for quick fan speed adjustments when the system is under load. For storage, specifically with spinning disks, just due to the mass of metal they tend to take on heat slower than CPUs and also cooler slower.

In the context of this script, these "timers" don't really work against actual time. Instead they work via python's `sleep` function and iterating a counter to check if they need to run again. I plan on reworking this so it works against actual time at some point.

## Logging configuration - log_config

This section allows you to change where the log is stored (`file_name`), the formatting of the log (`format`), what the time stamps in the log will look (`date_format`), and lastly how frequently the script will add to the log (`frequency`).

### file_name

Likely best to leave this alone, although you can change it as you see fit.

## format

Likely best to leave this alone, although you can change it as you see fit. That said, if you change it, note the comment on this line: When entering percent signs (%) you need to double them due to how the configuration tools the script uses functions.

## date_format

I've been told my time stamps are a bit strange by others but I find them helpful when searching for what happened at a specific moment. If you'd like to make adjustments you can refer to the python docs for assistance: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior I will note the month/day is in the American format, so flipping them may be worth it for non-Americans to be more easily understood without needing to adjust. Like above: if you change it, note the comment on this line: When entering percent signs (%) you need to double them due to how the configuration tools the script uses functions.

## frequency

This setting allows you to change how often the script writes to the log. This was mostly added to avoid spamming writes to the disk for CPU temperature changes. Early on while testing/setting up the fan curves it'd probably be a good idea to set it to `Every`, but once you're comfortable with it you can change it to `On_Change` or `On_Panic`.


