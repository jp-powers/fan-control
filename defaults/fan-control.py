#!/usr/bin/python3
##
## ipmi-fan-control.py
##

# import needed components
import time # used for sleep
import subprocess # used to execute external commands
import logging # lets make some nice logs
import json # we'll use json to handle reading the data from sensors a bit more cleanly/easily in Proxmox
import os # used to check if config.ini has changed
from configparser import ConfigParser # using ConfigParser for separate config file
import ast # used when importing config.ini to make it cleaner to work with

## need to load some config info at the top
# Read config.ini file
config_object = ConfigParser()
config_object.read("config.ini")
# logging
log_file_name = config_object["log_config"]["file_name"]
log_format = config_object["log_config"]["format"]
log_date_format = config_object["log_config"]["date_format"]
log_frequency = config_object["log_config"]["frequency"]
# ipmi type
hardware_platform = config_object["system_info"]["ipmi_type"]
# HDD temp cycle
detect_hdd_temp_every = int(config_object["detect_timers"]["hdd_timer"])

## define log basics
logging.basicConfig(format=log_format, datefmt=log_date_format, filename=log_file_name, level=logging.DEBUG)

## lets make some logic

def logger_start(): # show when logging of fan-control sessions starts
    logging.info("=============================")
    logging.info("||                         ||")
    logging.info("||  FAN CONTROL HAS BEGUN  ||")
    logging.info("||                         ||")
    logging.info("|| assuming direct control ||") # couldn't stop myself from a Mass Effect 2 joke for some reason
    logging.info("||                         ||")
    logging.info("=============================")

def has_config_changed(): # used to check if the config file has changed so values can be updated
    stat = os.stat("config.ini")
    return stat.st_mtime

def get_cpu_temp(op_sys):
    if op_sys == "Proxmox":
        sensors_data_json = json.loads(subprocess.check_output('sensors -j', shell=True)) # gets json formatted temperatures from sensors command, loads them into a variable as a dictionary
        temps_list = [] # define list for temperatures to be added to with following iterations
        for sensors_data_name, sensors_data_value in sensors_data_json.items(): # iterate thru every data set dict in json output
            if "coretemp" in sensors_data_name: # find dicts with coretemp data
                for coretemp_data_name, coretemp_data_value in sensors_data_value.items(): # iterate thru core temp data sets
                    if "Core " in coretemp_data_name: # find dicts with actual core data
                        for temps_data_name, temps_data_value in coretemp_data_value.items(): #iterate thru core data set
                            if "input" in temps_data_name: # find data with actual temperature value
                                temps_list.append(temps_data_value) # add that data to the full list
        cpu_avg_temp = sum(temps_list) / len(temps_list) # run a quick average of the data
        return round(cpu_avg_temp,2)
    if op_sys == "TrueNAS" or "pfSense":
        cpu_temps_cmd = "sysctl -a dev.cpu |  grep temperature | awk '{print $2}' | sed 's/.$//'" # define command to find the CPU temps by core
        cpu_temps = subprocess.check_output(cpu_temps_cmd, shell=True) # get the CPU temps into variable cpu_temps
        cpu_temps_list = list(map(float, cpu_temps.splitlines())) # take cpu_temps and create list for iterating on
        cpu_avg_temp = sum(cpu_temps_list) / len(cpu_temps_list) # run a quick average of the data
        return round(cpu_avg_temp,2)

def get_hdd_temp(disk_list): # this feels like a silly way to do it but it works I guess
    # create output list for smartctl run(s) and hdd_temps list, then get the HDD temps into list
    smartctl_output = []
    hdd_temps = []
    hdd_temps_list = []

    for disk_dev in disk_list: # iterate thru the list of drives to monitor
        hdd_temps_cmd = "smartctl -A /dev/" + disk_dev + " | grep Temperature_Celsius" # define command to find the HDD temps by device
        smartctl_output.append(str(subprocess.check_output(hdd_temps_cmd, shell=True))) # run the command, dump to raw output list
    for disk in smartctl_output: # convert output to just temps
        # almost certainly a smarter way to do this...
        hdd_temps.append(disk[40:42]) # takes each entry of smartctl_output, grabs the text of the output for the temp, appends it to hdd_temps
    for disk in hdd_temps: # take hdd_temps and create list for iterating on
        hdd_temps_list.append(int(disk))

    hdd_avg_temp = sum(hdd_temps_list) / len(hdd_temps_list) # run a quick average of the data
    hdd_max_temp = max(hdd_temps_list) # find the highest temp disk
    return [round(hdd_avg_temp,2), hdd_max_temp]

def get_cpu_zone_speed(temp,cpu_fan_curve): # based on the fan curve, decide what the appropriate fan power level (fan speed) should be, return it as an integer.
    i = 0 # create an iterator
    while i < (len(cpu_fan_curve) - 1): # while iterator is 1 less than total length of fan curve...
        a = cpu_fan_curve[i] # set 'a' to curve temp value of iterator
        b = cpu_fan_curve[i + 1] # set 'b' to next curve temp value of iterator

        if temp >= a[0] and temp <= b[0]: # if current average temperature is greater or equal to 'a' and less or equal to 'b' ...
            power = a[1] + (temp - a[0]) * (b[1] - a[1]) / (b[0] - a[0]) # do some math to figure out what to set fan power to
            break
        i += 1 # bump the iterator
    return int(power)

def get_hdd_zone_speed(temps,max_temp,speed_addition,hdd_fan_curve): # based on the fan curve, decide what the appropriate fan power level (fan speed) should be, return it as an integer.
    i = 0 # create an iterator
    if temps[1] >= max_temp: # if current max temp is greater than config's max temp bump the returned power by our max addition
        a = hdd_fan_curve[i] # set 'a' to curve temp value of iterator
        b = hdd_fan_curve[i + 1] # set 'b' to next curve temp value of iterator

        power = a[1] + (max_temp - a[0]) * (b[1] - a[1]) / (b[0] - a[0]) # do some math to figure out what to set fan power to
        return int(power) + speed_addition
    else: # if not, return base power we just figured out
        while i < (len(hdd_fan_curve) - 1): # while iterator is 1 less than total length of fan curve...
            a = hdd_fan_curve[i] # set 'a' to curve temp value of iterator
            b = hdd_fan_curve[i + 1] # set 'b' to next curve temp value of iterator

            if temps[0] >= a[0] and temps[0] <= b[0]: # if current average temperature is greater or equal to 'a' and less or equal to 'b' ...
                power = a[1] + (temps[0] - a[0]) * (b[1] - a[1]) / (b[0] - a[0]) # do some math to figure out what to set fan power to
                break
            i += 1 # bump the iterator
        return int(power)

def set_cpu_zone_fan_speed(zone_0_speed): # simple method to set the Zone 0 fan speed
    cmd = 'ipmitool raw 0x30 0x70 0x66 0x01 0x00 {speed}'.format(speed=zone_0_speed)
    subprocess.check_output(cmd, shell=True)

def set_hdd_zone_fan_speed(zone_1_speed): # simple method to set the Zone 1 fan speed
    cmd = 'ipmitool raw 0x30 0x70 0x66 0x01 0x01 {speed}'.format(speed=zone_1_speed)
    subprocess.check_output(cmd, shell=True)

def set_linked_zone_fan_speed(platform,speed): # simple method to set fan speed for both zones
    if platform == "SM_X10":
        cmd = 'ipmitool raw 0x30 0x70 0x66 0x01 0x00 {speed}'.format(speed=speed)
        subprocess.check_output(cmd, shell=True)
        cmd = 'ipmitool raw 0x30 0x70 0x66 0x01 0x01 {speed}'.format(speed=speed)
        subprocess.check_output(cmd, shell=True)
    if platform == "iDRAC_Gen08":
        hex_power = hex(speed) # convert incoming variable to hex
        cmd = 'ipmitool raw 0x30 0x30 0x02 0xff {hex_power}'.format(hex_power=hex_power)
        subprocess.check_output(cmd, shell=True)


##
## OK, lets do all the things.
##

logger_start()

config_loaded = False # assume config not loaded at first
config_last_changed = has_config_changed() # go ahead and get the current change time
hdd_itter = detect_hdd_temp_every # create an HDD iterator we'll use for a timer
# defaults fan speeds to 100%, and creates variables so things will hold during loop skips
current_cpu_fan_speed = 100
current_hdd_fan_speed = 100
hdd_suggested_fan_speed = 0
last_cpu_fan_speed = 0
last_hdd_fan_speed = 0

## if Supermicro, set fans to full so they don't "warble" and hold at our most recent request
if hardware_platform == "SM_X10":
    cmd = 'ipmitool raw 0x30 0x45 0x01 0x01'
    subprocess.check_output(cmd, shell=True)
    time.sleep(2)

## if Dell, set fans to allow full manual control to stop iDRAC from trying to manage it
if hardware_platform == "iDRAC_Gen08":
   cmd = 'ipmitool raw 0x30 0x30 0x01 0x00'
   subprocess.check_output(cmd, shell=True)
   time.sleep(2)

while True: # This is a service so it needs to run forever... so... lets make an infinite loop!
    try:
        if config_loaded is False or config_last_changed != has_config_changed(): # on every loop, check to see if the config file has changed, if so reload it
            ## Read config.ini file
            config_object = ConfigParser()
            config_object.read("config.ini")
            ## system info
            operating_system = config_object["system_info"]["system_os"]
            hardware_platform = config_object["system_info"]["ipmi_type"]
            fan_control_linked = config_object["system_info"].getboolean("single_zone")
            hdd_to_monitor = ast.literal_eval(config_object["system_info"]["disks"])
            ## fan curve
            cpu_fan_curve = ast.literal_eval(config_object["fan_curve"]["cpu"])
            hdd_fan_curve = ast.literal_eval(config_object["fan_curve"]["hdd"])
            ## temperature related data
            hdd_max_temp = int(config_object["hdd_panic"]["max_temp"])
            hdd_max_temp_addition = int(config_object["hdd_panic"]["panic_addition"])
            ## timers
            detect_cpu_temp_every = int(config_object["detect_timers"]["cpu_timer"])
            detect_hdd_temp_every = int(config_object["detect_timers"]["hdd_timer"])
            ## logging
            log_file_name = config_object["log_config"]["file_name"]
            log_format = config_object["log_config"]["format"]
            log_date_format = config_object["log_config"]["date_format"]
            log_frequency = config_object["log_config"]["frequency"]
            ## confirm complete
            config_loaded = True
            config_last_changed = has_config_changed()
            logging.info("""

            Config: Config loaded! Current config is:
            System OS: {os}
            Hardware Platform: {plat}
            Linked Fan Zones: {link}
            Drives to Monitor: {drives}
            CPU Fan Curve: {cpu_curve}
            HDD Fan Curve: {hdd_curve}
            HDD Panic Temp: {hmax}
            HDD Panic Addition: {addition}
            Log Frequency: {freq}

            """.format(os=operating_system,plat=hardware_platform,link=fan_control_linked,drives=hdd_to_monitor,cpu_curve=cpu_fan_curve,hdd_curve=hdd_fan_curve,hmax=hdd_max_temp,addition=hdd_max_temp_addition,freq=log_frequency))

        if operating_system == "pfSense": # pfSense routers shouldn't really care about the HDD temps, so skip all that stuff and just do CPU loops
            current_cpu_temp = get_cpu_temp(operating_system) #get current CPU average temp
            current_cpu_fan_speed = get_cpu_zone_speed(current_cpu_temp,cpu_fan_curve) # get what the fan speed should be based on above temp
            if log_frequency == "Every":
                logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed
            if log_frequency == "On_Change":
                if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                    last_cpu_fan_speed = current_cpu_fan_speed
                    logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                    set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed
            if log_frequency == "On_Panic":
                set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed
        if operating_system != "pfSense":
            if fan_control_linked is True:
                current_cpu_temp = get_cpu_temp(operating_system) #get current average temp
                current_cpu_fan_speed = get_cpu_zone_speed(current_cpu_temp,cpu_fan_curve) # get what the fan speed should be based on above temp
                hdd_itter += detect_cpu_temp_every # bump the hdd timer
                if hdd_itter >= detect_hdd_temp_every: # check if we need to run our HDD checks
                    current_hdd_temp = get_hdd_temp(hdd_to_monitor) # get current HDD average and max temps
                    current_hdd_fan_speed = get_hdd_zone_speed(current_hdd_temp,hdd_max_temp,hdd_max_temp_addition,hdd_fan_curve) # get what the fan speed should be based on above temp
                    if current_cpu_fan_speed > current_hdd_fan_speed:
                        if log_frequency == "Every":
                            logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed))
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_cpu_fan_speed))
                            set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
                        if log_frequency == "On_Change":
                            if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                                last_cpu_fan_speed = current_cpu_fan_speed
                                logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed))
                                logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_cpu_fan_speed))
                                set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
                        if log_frequency == "On_Panic":
                            if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                                last_cpu_fan_speed = current_cpu_fan_speed
                                set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
                    if current_hdd_fan_speed >= current_cpu_fan_speed:
                        if log_frequency == "Every":
                            logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed))
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            set_linked_zone_fan_speed(hardware_platform,current_hdd_fan_speed) # set the fan speed
                        if log_frequency == "On_Change":
                            if current_hdd_fan_speed > last_hdd_fan_speed or current_hdd_fan_speed < last_hdd_fan_speed:
                                last_hdd_fan_speed = current_hdd_fan_speed
                                logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed))
                                logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                                set_linked_zone_fan_speed(hardware_platform,current_hdd_fan_speed) # set the fan speed
                        if log_frequency == "On_Panic":
                            if current_hdd_fan_speed > last_hdd_fan_speed or current_hdd_fan_speed < last_hdd_fan_speed:
                                last_hdd_fan_speed = current_hdd_fan_speed
                                set_linked_zone_fan_speed(hardware_platform,current_hdd_fan_speed) # set the fan speed
                    if current_hdd_temp[1] >= hdd_max_temp:
                        if log_frequency == "Every" or log_frequency == "On_Change":
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            logging.warning("HDD Temp: Max HDD temperature met or exceeded! Holding fans for {time} seconds at {fan_speed}%".format(time=detect_hdd_temp_every*2,fan_speed=current_hdd_fan_speed)) # drop a warning to log if HDD temp hits max
                            time.sleep(detect_hdd_temp_every) # lets sleep for a bit to give the HDDs time to chill
                        if log_frequency == "On_Panic":
                            logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed))
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            logging.warning("HDD Temp: Max HDD temperature met or exceeded! Holding fans for {time} seconds at {fan_speed}%".format(time=detect_hdd_temp_every*2,fan_speed=current_hdd_fan_speed)) # drop a warning to log if HDD temp hits max
                            time.sleep(detect_hdd_temp_every) # lets sleep for a bit to give the HDDs time to chill
                    hdd_itter = 0 # reset our HDD timer
                    hdd_suggested_fan_speed = current_hdd_fan_speed # set a variable to hold the fan speed for future loops
                else: # now just checking CPU
                    if hdd_suggested_fan_speed >= current_cpu_fan_speed: # check if our last HDD temps were higher and act accordingly
                        if log_frequency == "Every":
                            logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=hdd_suggested_fan_speed)) # For each loop, write the temp then the proposed fan speed
                            set_linked_zone_fan_speed(hardware_platform,hdd_suggested_fan_speed) # set the fan speed
                    else: # adjusting based on CPU temps only now
                        if log_frequency == "Every":
                            logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                            set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
                        if log_frequency == "On_Change":
                            if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                                last_cpu_fan_speed = current_cpu_fan_speed
                                logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                                set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
                        if log_frequency == "On_Panic":
                            if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                                last_cpu_fan_speed = current_cpu_fan_speed
                                set_linked_zone_fan_speed(hardware_platform,current_cpu_fan_speed) # set the fan speed
            else: # if Fan Zones are not linked
                current_cpu_temp = get_cpu_temp(operating_system) #get current CPU average temp
                current_cpu_fan_speed = get_cpu_zone_speed(current_cpu_temp,cpu_fan_curve) # get what the fan speed should be based on above temp
                if log_frequency == "Every":
                    logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                    set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed
                if log_frequency == "On_Change":
                    if current_cpu_fan_speed > last_cpu_fan_speed or current_cpu_fan_speed < last_cpu_fan_speed:
                        last_cpu_fan_speed = current_cpu_fan_speed
                        logging.info("CPU Temp: {temp}C -> Fans: {fan_speed}".format(temp=current_cpu_temp,fan_speed=current_cpu_fan_speed)) # For each loop, write the temp then the proposed fan speed
                        set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed
                if log_frequency == "On_Panic":
                    set_cpu_zone_fan_speed(current_cpu_fan_speed) # set the fan speed

                hdd_itter += detect_cpu_temp_every # bump the hdd timer
                if hdd_itter >= detect_hdd_temp_every: # check if we need to run our HDD checks
                    current_hdd_temp = get_hdd_temp(hdd_to_monitor) #get current HDD average and max temps
                    current_hdd_fan_speed = get_hdd_zone_speed(current_hdd_temp,hdd_max_temp,hdd_max_temp_addition,hdd_fan_curve) # get what the fan speed should be based on above temp
                    if log_frequency == "Every":
                        logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                        set_hdd_zone_fan_speed(current_hdd_fan_speed) # set the fan speed
                    if log_frequency == "On_Change":
                        if current_hdd_fan_speed > last_hdd_fan_speed or current_hdd_fan_speed < last_hdd_fan_speed:
                            last_hdd_fan_speed = current_hdd_fan_speed
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            set_hdd_zone_fan_speed(current_hdd_fan_speed) # set the fan speed
                    if log_frequency == "On_Panic":
                        if current_hdd_fan_speed > last_hdd_fan_speed or current_hdd_fan_speed < last_hdd_fan_speed:
                            last_hdd_fan_speed = current_hdd_fan_speed
                            set_hdd_zone_fan_speed(current_hdd_fan_speed) # set the fan speed
                    if current_hdd_temp[1] >= hdd_max_temp:
                        if log_frequency == "Every" or log_frequency == "On_Change":
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            logging.warning("HDD Temp: Max HDD temperature met or exceeded! Holding fans for {time} seconds at {fan_speed}%".format(time=detect_hdd_temp_every*2,fan_speed=current_hdd_fan_speed)) # drop a warning to log if HDD temp hits max
                            time.sleep(detect_hdd_temp_every) # lets sleep for a bit to give the HDDs time to chill
                        if log_frequency == "On_Panic":
                            logging.info("HDD Temp: Average = {avg_temp}C, Max = {max_temp}C-> Fans: {fan_speed}".format(avg_temp=current_hdd_temp[0],max_temp=current_hdd_temp[1],fan_speed=current_hdd_fan_speed))
                            logging.warning("HDD Temp: Max HDD temperature met or exceeded! Holding fans for {time} seconds at {fan_speed}%".format(time=detect_hdd_temp_every*2,fan_speed=current_hdd_fan_speed)) # drop a warning to log if HDD temp hits max
                            time.sleep(detect_hdd_temp_every) # lets sleep for a bit to give the HDDs time to chill
                    hdd_itter = 0 # reset our HDD timer

        time.sleep(detect_cpu_temp_every) # wait to run again
    except Exception as exc: # in event of a script crash, dump more data to log
        logging.error("Critical error occurred!!", exc_info=True)
