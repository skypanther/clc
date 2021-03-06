"""
PiLit Player - the player for PiLit light show sequences

(c) 2019 Tim Poulsen
MIT License

Usage:

    python3 pilit_player.py <show_file_name.json>

"""

import json
import os
import paho.mqtt.publish as publish
import sys
from datetime import datetime
from time import sleep

mqtt_server = "northpole.local"  # my server is named northpole, change this
show_loop_interval = 0.5  # seconds
logging_enabled = True
times_shutoff_cmd_sent = 0

def main():
    args = sys.argv[1:]
    if (len(args) == 0):
        # prompt for show name
        show_name = input('Enter the show name: ')
    else:
        show_name = args[0]
    show_path = os.path.realpath(show_name)
    load_file(show_path)

def load_file(show_path):
    if not os.path.isfile(show_path):
        print('No show file by that name')
        exit()
    show_file = ""
    with open(show_path) as sp:
        show_file = json.load(sp)
    validate_file(show_file)

def validate_file(show_file):
    if show_file and\
       show_file != "" and\
       show_file["showName"] != "" and\
       show_file["startTime"] != "" and\
       show_file["stopTime"] != "" and\
       show_file["channels"]:
        # show is valid
        preprocess_file(show_file)
        return
    print("Show file is not a valid PiLit file.")
    exit()

def preprocess_file(show_file):
    channels = []
    start_time, end_time = get_show_times(show_file)
    for channel in show_file["channels"]:
        sum_of_durations = 0
        channel_commands = []
        for animation in channel["animations"]:
            sum_of_durations = sum_of_durations + int(animation["duration"])
            animation_command = make_animation_command(channel["type"], animation)
            channel_commands.append( (channel["mqttName"], animation_command, sum_of_durations) )
        channels.append(channel_commands)
    show = {
        "start_time": start_time,
        "end_time": end_time,
        "channels": channels
    }
    run_show(show)

def make_animation_command(type, animation):
    # types: PixelNode, OnOffNode, MegaTree
    if type == "PixelNode" or type == "PixelTree":
        anim = animation['animation'] if animation['animation'] != "" else "off"
        color = animation['color'] if animation['color'] != "" else "black"
        loopDelay = animation['loopDelay'] if animation['loopDelay'] != "" else "10"
        holdTime = animation['holdTime'] if animation['holdTime'] != "" else "50"
        repeatable = animation['repeatable'] if animation['repeatable'] else True
        return f"{color}:{anim}:{loopDelay}:{holdTime}:{repeatable}"
    if type == "OnOffNode":
        anim = animation['animation'] if animation['animation'] != "" else "off"
        return f"{anim}"
    if type == "MultiRelayNode":
        anim = animation['animation'] if animation['animation'] != "" else "off"
        loopDelay = animation['loopDelay'] if animation['loopDelay'] != "" else "10"
        return f"{anim}:{loopDelay}"
    return "off"

def get_show_times(show_file):
    start_time = show_file["startTime"].split(':')
    stop_time = show_file["stopTime"].split(':')
    return ( (int(start_time[0]), int(start_time[1])), (int(stop_time[0]), int(stop_time[1])) )

def get_show_times_for_today(start_time, stop_time):
    st = datetime.today().replace(hour=start_time[0], minute=start_time[1], second=0, microsecond=0)
    if stop_time[0] <= 12:
        # we're stopping after midnight
        tomorrow = datetime.today() + datetime.timedelta(days=1)
        et = tomorrow.replace(hour=stop_time[0], minute=stop_time[1], second=59, microsecond=999999)
    else:
        et = datetime.today().replace(hour=stop_time[0], minute=stop_time[1], second=59, microsecond=999999)
    return st, et

def log(msg):
    if logging_enabled:
        print(msg)

def send_command(topic, payload, sum_of_durations):
    # paho mqtt send command here
    log(f"{topic} ({sum_of_durations} secs) --> {payload}")
    publish.single(topic, payload=payload, hostname=mqtt_server)

def lengths(x):
    # https://stackoverflow.com/a/30902673/292947
    # Find the longest list in a list of lists (recursive)
    # Usage: max(lengths(list_of_lists))
    if isinstance(x,list):
        yield len(x)
        for y in x:
            yield from lengths(y)

def get_longest_animation_sequence(channels_list):
    longest = (0, 0)
    for index, channel in enumerate(channels_list):
        num_anims = len(channel)
        if num_anims > longest[0]:
            longest = (num_anims, index)
    return longest

def run_show(show):
    most_animations_count, most_animations_index = get_longest_animation_sequence(show["channels"])
    last_animation_in_longest_sequence = show["channels"][most_animations_index][most_animations_count - 1]
    longest_animation_duration = last_animation_in_longest_sequence[2]
    mqtt_names = [channel[0][0] for channel in show["channels"]]
    animation_indexes = [0] * len(show["channels"])
    duration_counter = 0
    global times_shutoff_cmd_sent
    while True:
        current_time = datetime.now()
        show_start_time, show_stop_time = get_show_times_for_today(show["start_time"], show["end_time"])
        if current_time > show_start_time and current_time < show_stop_time:
            times_shutoff_cmd_sent = 0
            duration_counter += show_loop_interval  # 0.5 seconds
            if duration_counter == show_loop_interval:
                # This is the first time through, so run the first animation in all channels
                log("***** Starting Show *****")
                for index, channel in enumerate(show["channels"]):
                    current_animation_index = animation_indexes[index]
                    mqtt_name, anim, sum_of_durations = channel[current_animation_index]
                    send_command(mqtt_name, anim, sum_of_durations)
                    current_animation_index += 1
                    if current_animation_index >= len(channel):
                        current_animation_index = 0
                    animation_indexes[index] = current_animation_index
                continue
            for index, channel in enumerate(show["channels"]):
                current_animation_index = animation_indexes[index]
                mqtt_name, anim, sum_of_durations = channel[current_animation_index]
                # print(mqtt_name, sum_of_durations, duration_counter, current_animation_index, len(channel))
                if duration_counter >= sum_of_durations:
                    send_command(mqtt_name, anim, sum_of_durations)
                    current_animation_index += 1
                    if current_animation_index >= len(channel):
                        current_animation_index = 0
                    animation_indexes[index] = current_animation_index
            if duration_counter >= longest_animation_duration:
                duration_counter = 0
        else:
            animation_indexes = [0] * len(show["channels"])
            duration_counter = 0
            if times_shutoff_cmd_sent < 5:
                times_shutoff_cmd_sent += 1
                for mqtt_name in mqtt_names:
                    send_command(mqtt_name, "off", 0)
            sleep(show_loop_interval * 10)
        sleep(show_loop_interval)


if __name__ == '__main__':
    main()