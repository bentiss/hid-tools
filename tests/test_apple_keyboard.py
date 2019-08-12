#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2019 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import base
import libevdev
import sys
import hidtools.hid
from base import main, setUpModule, tearDownModule  # noqa
from test_keyboard import ArrayKeyboard, TestArrayKeyboard

import logging
logger = logging.getLogger('hidtools.test.apple-keyboard')

class AppleKeyboard(ArrayKeyboard):
    report_descriptor = [
        0x05, 0x01,         #  Usage Page (Generic Desktop)
        0x09, 0x06,         #  Usage (Keyboard)
        0xa1, 0x01,         #  Collection (Application)
        0x85, 0x01,         #   Report ID (1)
        0x05, 0x07,         #   Usage Page (Keyboard)
        0x19, 0xe0,         #   Usage Minimum (224)
        0x29, 0xe7,         #   Usage Maximum (231)
        0x15, 0x00,         #   Logical Minimum (0)
        0x25, 0x01,         #   Logical Maximum (1)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x08,         #   Report Count (8)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x75, 0x08,         #   Report Size (8)
        0x95, 0x01,         #   Report Count (1)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x05,         #   Report Count (5)
        0x05, 0x08,         #   Usage Page (LEDs)
        0x19, 0x01,         #   Usage Minimum (1)
        0x29, 0x05,         #   Usage Maximum (5)
        0x91, 0x02,         #   Output (Data,Var,Abs)
        0x75, 0x03,         #   Report Size (3)
        0x95, 0x01,         #   Report Count (1)
        0x91, 0x01,         #   Output (Cnst,Arr,Abs)
        0x75, 0x08,         #   Report Size (8)
        0x95, 0x06,         #   Report Count (6)
        0x15, 0x00,         #   Logical Minimum (0)
        0x26, 0xff, 0x00,   #   Logical Maximum (255)
        0x05, 0x07,         #   Usage Page (Keyboard)
        0x19, 0x00,         #   Usage Minimum (0)
        0x2a, 0xff, 0x00,   #   Usage Maximum (255)
        0x81, 0x00,         #   Input (Data,Arr,Abs)
        0xc0,               #  End Collection
        0x05, 0x0c,         #  Usage Page (Consumer Devices)
        0x09, 0x01,         #  Usage (Consumer Control)
        0xa1, 0x01,         #  Collection (Application)
        0x85, 0x47,         #   Report ID (71)
        0x05, 0x01,         #   Usage Page (Generic Desktop)
        0x09, 0x06,         #   Usage (Keyboard)
        0xa1, 0x02,         #   Collection (Logical)
        0x05, 0x06,         #    Usage Page (Generic Device Controls)
        0x09, 0x20,         #    Usage (Battery Strength)
        0x15, 0x00,         #    Logical Minimum (0)
        0x26, 0xff, 0x00,   #    Logical Maximum (255)
        0x75, 0x08,         #    Report Size (8)
        0x95, 0x01,         #    Report Count (1)
        0x81, 0x02,         #    Input (Data,Var,Abs)
        0xc0,               #   End Collection
        0xc0,               #  End Collection
        0x05, 0x0c,         #  Usage Page (Consumer Devices)
        0x09, 0x01,         #  Usage (Consumer Control)
        0xa1, 0x01,         #  Collection (Application)
        0x85, 0x11,         #   Report ID (17)
        0x15, 0x00,         #   Logical Minimum (0)
        0x25, 0x01,         #   Logical Maximum (1)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x03,         #   Report Count (3)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x01,         #   Report Count (1)
        0x05, 0x0c,         #   Usage Page (Consumer Devices)
        0x09, 0xb8,         #   Usage (Eject)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x06, 0xff, 0x00,   #   Usage Page (Vendor Usage Page 0xff)
        0x09, 0x03,         #   Usage (Vendor Usage 0x03)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x03,         #   Report Count (3)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x05, 0x0c,         #   Usage Page (Consumer Devices)
        0x85, 0x12,         #   Report ID (18)
        0x15, 0x00,         #   Logical Minimum (0)
        0x25, 0x01,         #   Logical Maximum (1)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x01,         #   Report Count (1)
        0x09, 0xcd,         #   Usage (Play/Pause)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x09, 0xb3,         #   Usage (Fast Forward)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x09, 0xb4,         #   Usage (Rewind)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x09, 0xb5,         #   Usage (Scan Next Track)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x09, 0xb6,         #   Usage (Scan Previous Track)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x85, 0x13,         #   Report ID (19)
        0x15, 0x00,         #   Logical Minimum (0)
        0x25, 0x01,         #   Logical Maximum (1)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x01,         #   Report Count (1)
        0x06, 0x01, 0xff,   #   Usage Page (Vendor Usage Page 0xff01)
        0x09, 0x0a,         #   Usage (Vendor Usage 0x0a)
        0x81, 0x02,         #   Input (Data,Var,Abs)
        0x06, 0x01, 0xff,   #   Usage Page (Vendor Usage Page 0xff01)
        0x09, 0x0c,         #   Usage (Vendor Usage 0x0c)
        0x81, 0x22,         #   Input (Data,Var,Abs,NoPref)
        0x75, 0x01,         #   Report Size (1)
        0x95, 0x06,         #   Report Count (6)
        0x81, 0x01,         #   Input (Cnst,Arr,Abs)
        0x85, 0x09,         #   Report ID (9)
        0x09, 0x0b,         #   Usage (Vendor Usage 0x0b)
        0x75, 0x08,         #   Report Size (8)
        0x95, 0x01,         #   Report Count (1)
        0xb1, 0x02,         #   Feature (Data,Var,Abs)
        0x75, 0x08,         #   Report Size (8)
        0x95, 0x02,         #   Report Count (2)
        0xb1, 0x01,         #   Feature (Cnst,Arr,Abs)
        0xc0,               #  End Collection
    ]

    def __init__(self,
                 rdesc=report_descriptor,
                 name='Apple Wireless Keyboard',
                 info=(0x5, 0x05ac, 0x0256)):
        super().__init__(rdesc, name, info)
        self.default_reportID = 1


class TestAppleKeyboard(TestArrayKeyboard):
    def create_device(self):
        return AppleKeyboard()

    def test_single_function_key(self):
        """check for function key reliability."""
        uhdev = self.uhdev
        syn_event = self.syn_event

        r = uhdev.event(['F4'])
        expected = [syn_event]
        expected.append(libevdev.InputEvent(libevdev.EV_KEY.KEY_DASHBOARD, 1))
        events = uhdev.next_sync_events()
        self.debug_reports(r, uhdev, events)
        self.assertInputEventsIn(expected, events)
        self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.KEY_DASHBOARD], 1)

        r = uhdev.event([])
        expected = [syn_event]
        expected.append(libevdev.InputEvent(libevdev.EV_KEY.KEY_DASHBOARD, 0))
        events = uhdev.next_sync_events()
        self.debug_reports(r, uhdev, events)
        self.assertInputEventsIn(expected, events)
        self.assertEqual(uhdev.evdev.value[libevdev.EV_KEY.KEY_DASHBOARD], 0)
