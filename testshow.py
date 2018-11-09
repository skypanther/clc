"""
Show Runner script for CLC, the Christmas lights controller
Author: Tim Poulsen, @skypanther
License: MIT

This script runs on your Raspberry Pi, reads in a show.json
file, and turns on/off the relays to perform your show.

Setup:

1. Make sure you have gpiozero installed on your Pi with:

> sudo apt-get update
> sudo apt-get install python3-gpiozero python-gpiozero

2. Update the board_pins list below with the pin numbers you're
using on your Pi. If you're using less than 16 pins, simply
delete any extra numbers from the sample line below

3. Run it (manually or from cron) with a command in the form:

> py runshow.py show.json HH:MM

  where show.json is the name of your show file (in same
  directory as this file) and HH:MM is the hours and minutes
  of when to end the show.

For example:

> py runshow.py show.json 22:30

Runs the show.json show till 11:30 PM tonight.

"""

import sys
from datetime import datetime
from time import sleep
import json
import os.path

# CONFIGURE THESE VARIABLES TO SUIT YOUR ACTUAL SETUP
# don't use pin 8 on a Pi B+ as it's the "hard drive light" pin
board_pins = [3, 5, 7, 26, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24]

# DON'T CHANGE THESE VARIABLES
midnight = datetime.today().replace(
    hour=23, minute=59, second=59, microsecond=999999)
args = sys.argv[1:]
pins = []

on = u'\u2593 '
off = u'\u2591 '
states = [off, on]


def main():
    if (len(args) == 0):
        # prompt for show name, duration
        show_name = input('Enter the show name: ')
        the_time = input('When should the show end? (time as HH:MM):')
        if "." not in show_name:
            show_name += ".json"
        if the_time == '':
            end_time = midnight
        else:
            end_time = format_end_time(the_time)
    elif (len(args) == 1 and args[0] == 'off'):
        # turn all lights off then exit
        all_off()
        exit()
    elif (len(args) == 1 and args[0] == 'on'):
        # turn all lights on then exit
        all_on()
        exit()
    elif (len(args) == 1):
        show_name = args[0]
        end_time = midnight
        if "." not in show_name:
            show_name += ".json"
    else:
        show_name = args[0]
        end_time = format_end_time(args[1])
        if "." not in show_name:
            show_name += ".json"
    if not os.path.isfile(show_name):
        print('No show file by that name')
        exit()
    run_show(show_name, end_time)


def run_show(show_name, end_time):
    # Runs the actual show
    with open(show_name) as json_file:
        show_file = json.load(json_file)
    if 'show' not in show_file:
        print('Bad show file')
        exit()
    show = show_file['show']
    delay = show_file['interval'] if 'interval' in show_file else 500
    delay = delay / 1000.0
    now = datetime.now()
    while now < end_time:
        for row in show:
            print_line(row)
            sleep(delay)
        now = datetime.now()


def format_end_time(the_time):
    # Formats an HH:MM time string into an actual datetime
    input_time = the_time.split(':')
    end_time = datetime.today().replace(
        hour=int(input_time[0]), minute=int(input_time[1]))
    return end_time


def all_on():
    print_line('1' * len(board_pins))


def all_off():
    print_line('0' * len(board_pins))


def print_line(line):
    print('\r', end="")
    for led in line:
        print(states[led], end="")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
