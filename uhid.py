#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Hid tools / uhid.py
#
# Copyright (c) 2017 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2017 Red Hat, Inc.
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

import hid
import os
import pyudev
import select
import struct
import uuid


class UHIDUncompleteException(Exception):
    pass


class UHIDDevice(object):
    __UHID_LEGACY_CREATE = 0
    UHID_DESTROY = 1
    UHID_START = 2
    UHID_STOP = 3
    UHID_OPEN = 4
    UHID_CLOSE = 5
    UHID_OUTPUT = 6
    __UHID_LEGACY_OUTPUT_EV = 7
    __UHID_LEGACY_INPUT = 8
    UHID_GET_REPORT = 9
    UHID_GET_REPORT_REPLY = 10
    UHID_CREATE2 = 11
    UHID_INPUT2 = 12
    UHID_SET_REPORT = 13
    UHID_SET_REPORT_REPLY = 14

    polling_functions = {}
    poll = select.poll()
    devices = []

    pyudev_context = None
    pyudev_monitor = None

    @classmethod
    def process_one_event(cls, timeout=None):
        devices = cls.poll.poll(timeout)
        for fd, mask in devices:
            if mask & select.POLLIN:
                fun = cls.polling_functions[fd]
                fun()
        return len(devices)

    @classmethod
    def append_fd_to_poll(cls, fd, read_function):
        cls.poll.register(fd)
        cls.polling_functions[fd] = read_function

    @classmethod
    def remove_fd_from_poll(cls, fd):
        cls.poll.unregister(fd)

    @classmethod
    def init_pyudev(cls):
        if cls.pyudev_context is None:
            cls.pyudev_context = pyudev.Context()
            cls.pyudev_monitor = pyudev.Monitor.from_netlink(cls.pyudev_context)
            cls.pyudev_monitor.filter_by('input')
            cls.pyudev_monitor.start()

            cls.append_fd_to_poll(cls.pyudev_monitor.fileno(), cls.cls_udev_event)

    @classmethod
    def cls_udev_event(cls):
        event = cls.pyudev_monitor.poll()

        if event is None:
            return

        for d in cls.devices:
            if d.udev is not None and d.udev.sys_path in event.sys_path:
                d.udev_event(event)

    def __init__(self):
        self._name = None
        self._phys = ''
        self._rdesc = None
        self.parsed_rdesc = None
        self._info = None
        self._fd = os.open('/dev/uhid', os.O_RDWR)
        self._start = self.start
        self._stop = self.stop
        self._open = self.open
        self._close = self.close
        self._set_report = self.set_report
        self._get_report = self.get_report
        self._output_report = self.output_report
        self._udev = None
        self.uniq = f'uhid_{str(uuid.uuid4())}'
        self.append_fd_to_poll(self._fd, self._process_one_event)
        self.init_pyudev()
        UHIDDevice.devices.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        UHIDDevice.devices.remove(self)
        self.remove_fd_from_poll(self._fd)
        os.close(self._fd)

    def udev_event(self, event):
        pass

    @property
    def fd(self):
        return self._fd

    @property
    def rdesc(self):
        return self._rdesc

    @rdesc.setter
    def rdesc(self, rdesc):
        parsed_rdesc = rdesc
        if not isinstance(rdesc, hid.ReportDescriptor):
            parsed_rdesc = hid.ReportDescriptor.parse_rdesc(rdesc)
        self.parsed_rdesc = parsed_rdesc
        self._rdesc = parsed_rdesc.data()

    @property
    def phys(self):
        return self._phys

    @phys.setter
    def phys(self, phys):
        self._phys = phys

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, info):
        self._info = info

    @property
    def bus(self):
        return self._info[0]

    @property
    def vid(self):
        return self._info[1]

    @property
    def pid(self):
        return self._info[2]

    def call_set_report(self, req, err):
        buf = struct.pack('< L L H',
                          UHIDDevice.UHID_SET_REPORT_REPLY,
                          req,
                          err)
        os.write(self._fd, buf)

    def call_get_report(self, req, data, err):
        data = bytes(data)
        buf = struct.pack('< L L H H 4096s',
                          UHIDDevice.UHID_GET_REPORT_REPLY,
                          req,
                          err,
                          len(data),
                          data)
        os.write(self._fd, buf)

    def call_input_event(self, data):
        data = bytes(data)
        buf = struct.pack('< L H 4096s',
                          UHIDDevice.UHID_INPUT2,
                          len(data),
                          data)
        os.write(self._fd, buf)

    @property
    def udev(self):
        if self._udev is None:
            for device in self.pyudev_context.list_devices(subsystem='hid'):
                if self.uniq == device.properties['HID_UNIQ']:
                    self._udev = device
        return self._udev

    @property
    def sys_path(self):
        return self.udev.sys_path

    def create_kernel_device(self):
        if (self._name is None or
           self._rdesc is None or
           self._info is None):
            raise UHIDUncompleteException("missing uhid initialization")

        buf = struct.pack('< L 128s 64s 64s H H L L L L 4096s',
                          UHIDDevice.UHID_CREATE2,
                          bytes(self._name, 'utf-8'),  # name
                          bytes(self._phys, 'utf-8'),  # phys
                          bytes(self.uniq, 'utf-8'),  # uniq
                          len(self._rdesc),  # rd_size
                          self.bus,  # bus
                          self.vid,  # vendor
                          self.pid,  # product
                          0,  # version
                          0,  # country
                          bytes(self._rdesc))  # rd_data[HID_MAX_DESCRIPTOR_SIZE]

        n = os.write(self._fd, buf)
        assert n == len(buf)

    def destroy(self):
        buf = struct.pack('< L',
                          UHIDDevice.UHID_DESTROY)
        os.write(self._fd, buf)

    def start(self, flags):
        print('start')

    def stop(self):
        print('stop')

    def open(self):
        print('open', self.sys_path)

    def close(self):
        print('close')

    def set_report(self, req, rnum, rtype, size, data):
        print('set report', req, rtype, size, [f'{d:02x}' for d in data[:size]])
        self.call_set_report(req, 1)

    def get_report(self, req, rnum, rtype):
        print('get report', req, rnum, rtype)
        self.call_get_report(req, [], 1)

    def output_report(self, data, size, rtype):
        print('output', rtype, size, [f'{d:02x}' for d in data[:size]])

    def _process_one_event(self):
        buf = os.read(self._fd, 4380)
        assert len(buf) == 4380
        evtype = struct.unpack_from('< L', buf)[0]
        if evtype == UHIDDevice.UHID_START:
            ev, flags = struct.unpack_from('< L Q', buf)
            self.start(flags)
        elif evtype == UHIDDevice.UHID_OPEN:
            self._open()
        elif evtype == UHIDDevice.UHID_STOP:
            self._stop()
        elif evtype == UHIDDevice.UHID_CLOSE:
            self._close()
        elif evtype == UHIDDevice.UHID_SET_REPORT:
            ev, req, rnum, rtype, size, data = struct.unpack_from('< L L B B H 4096s', buf)
            self._set_report(req, rnum, rtype, size, data)
        elif evtype == UHIDDevice.UHID_GET_REPORT:
            ev, req, rnum, rtype = struct.unpack_from('< L L B B', buf)
            self._get_report(req, rnum, rtype)
        elif evtype == UHIDDevice.UHID_OUTPUT:
            ev, data, size, rtype = struct.unpack_from('< L 4096s H B', buf)
            self._output_report(data, size, rtype)

    def format_report(self, data, global_data=None, reportID=None, application=None):
        return self.parsed_rdesc.format_report(data, global_data, reportID, application)
