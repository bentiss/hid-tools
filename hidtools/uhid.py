#!/bin/env python3
# -*- coding: utf-8 -*-
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

import hidtools.hid
from hidtools.util import BusType
import os
import select
import struct
import time
import uuid

from hidtools.hut import U8, U32
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pathlib import Path

from pyroute2 import UeventSocket

import logging

logger = logging.getLogger("hidtools.hid.uhid")


class UHIDIncompleteException(Exception):
    """
    An exception raised when a UHIDDevice does not have sufficient
    information to create a kernel device.
    """

    pass


class UHIDDevice(object):
    """
    A uhid device. uhid is a kernel interface to create virtual HID devices
    based on a report descriptor.

    This class also acts as context manager for any :class:`UHIDDevice`
    objects. See :meth:`dispatch` for details.

    .. attribute:: uniq

        A uniq string assigned to this device. This string is autogenerated
        and can be used to reliably identify the device.

    """

    __UHID_LEGACY_CREATE: Final = 0
    _UHID_DESTROY: Final = 1
    _UHID_START: Final = 2
    _UHID_STOP: Final = 3
    _UHID_OPEN: Final = 4
    _UHID_CLOSE: Final = 5
    _UHID_OUTPUT: Final = 6
    __UHID_LEGACY_OUTPUT_EV: Final = 7
    __UHID_LEGACY_INPUT: Final = 8
    _UHID_GET_REPORT: Final = 9
    _UHID_GET_REPORT_REPLY: Final = 10
    _UHID_CREATE2: Final = 11
    _UHID_INPUT2: Final = 12
    _UHID_SET_REPORT: Final = 13
    _UHID_SET_REPORT_REPLY: Final = 14

    UHID_FEATURE_REPORT: Final = 0
    UHID_OUTPUT_REPORT: Final = 1
    UHID_INPUT_REPORT: Final = 2

    _polling_functions: Dict[int, Callable[[], None]] = {}
    _poll = select.poll()
    _devices: List["UHIDDevice"] = []

    @classmethod
    def dispatch(cls: Type["UHIDDevice"], timeout: Optional[float] = None) -> bool:
        """
        Process any events available on any internally registered file
        descriptor and deal with the events.

        The caller must call this function regularly to make sure things
        like udev events are processed correctly. There's no indicator of
        when to call :meth:`dispatch` yet, call it whenever you're idle.

        :returns: True if data was processed, False otherwise
        """
        had_data = False
        devices = cls._poll.poll(timeout)
        while devices:
            for fd, mask in devices:
                if mask & select.POLLIN:
                    fun = cls._polling_functions[fd]
                    fun()
            devices = cls._poll.poll(timeout)
            had_data = True
        return had_data

    @classmethod
    def _append_fd_to_poll(
        cls: Type["UHIDDevice"],
        fd: int,
        read_function: Callable[[], None],
        mask=select.POLLIN,
    ) -> None:
        cls._poll.register(fd, mask)
        cls._polling_functions[fd] = read_function

    @classmethod
    def _remove_fd_from_poll(cls: Type["UHIDDevice"], fd: int) -> None:
        cls._poll.unregister(fd)

    def __init__(self: "UHIDDevice") -> None:
        self._name: Optional[str] = None
        self._phys: Optional[str] = ""
        self._rdesc: Optional[List[int]] = None
        self.parsed_rdesc: Optional[hidtools.hid.ReportDescriptor] = None
        self._info: Optional[Tuple[int, int, int]] = None
        self._bustype: Optional[BusType] = None
        self._fd: int = os.open("/dev/uhid", os.O_RDWR)
        self._start = self.start
        self._stop = self.stop
        self._open = self.open
        self._close = self.close
        self._output_report = self.output_report
        self._ready: bool = False
        self._is_destroyed: bool = False
        self._sys_path: Optional[Path] = None
        self.uniq = f"uhid_{str(uuid.uuid4())}"
        self.hid_id: int = 0
        self._append_fd_to_poll(self._fd, self._process_one_event)
        UHIDDevice._devices.append(self)

    def __enter__(self: "UHIDDevice") -> "UHIDDevice":
        return self

    def __exit__(self: "UHIDDevice", *exc_details) -> None:
        if not self._is_destroyed:
            self.destroy()

    @property
    def fd(self: "UHIDDevice") -> int:
        """
        The fd to the ``/dev/uhid`` device node
        """
        return self._fd

    @property
    def rdesc(self: "UHIDDevice") -> Optional[List[int]]:
        """
        The device's report descriptor
        """
        return self._rdesc

    @rdesc.setter
    def rdesc(
        self: "UHIDDevice", rdesc: Union[hidtools.hid.ReportDescriptor, str, bytes]
    ):
        if isinstance(rdesc, hidtools.hid.ReportDescriptor):
            self.parsed_rdesc = rdesc
        else:
            if isinstance(rdesc, str):
                rdesc = f"XXX {rdesc}"
                self.parsed_rdesc = hidtools.hid.ReportDescriptor.from_string(rdesc)
            else:
                self.parsed_rdesc = hidtools.hid.ReportDescriptor.from_bytes(rdesc)
        if self.parsed_rdesc is not None:  # should always be true
            self._rdesc = self.parsed_rdesc.bytes

    @property
    def phys(self: "UHIDDevice") -> Optional[str]:
        """
        The device's phys string
        """
        return self._phys

    @phys.setter
    def phys(self: "UHIDDevice", phys: str) -> None:
        self._phys = phys

    @property
    def name(self: "UHIDDevice") -> Optional[str]:
        """
        The devices HID name
        """
        return self._name

    @name.setter
    def name(self: "UHIDDevice", name: str) -> None:
        self._name = name

    @property
    def info(self: "UHIDDevice") -> Optional[Tuple[int, int, int]]:
        """
        The devices's bus, vendor ID and product ID as tuple
        """
        return self._info

    @info.setter
    def info(self: "UHIDDevice", info: Tuple[int, int, int]) -> None:
        self._info = info
        # In case bus type is passed as 'int', wrap it in BusType.
        self._bustype = info[0] if isinstance(info[0], BusType) else BusType(info[0])

    @property
    def bus(self: "UHIDDevice") -> Optional[BusType]:
        """
        The device's bus type :class:`hidtools.util.BusType`
        """
        return self._bustype

    @property
    def vid(self: "UHIDDevice") -> Optional[int]:
        """
        The device's 16-bit vendor ID
        """
        if self._info is None:
            return None
        return self._info[1]

    @property
    def pid(self: "UHIDDevice") -> Optional[int]:
        """
        The device's 16-bit product ID
        """
        if self._info is None:
            return None
        return self._info[2]

    def _call_set_report(self: "UHIDDevice", req: int, err: int) -> None:
        buf = struct.pack("< L L H", UHIDDevice._UHID_SET_REPORT_REPLY, req, err)
        os.write(self._fd, buf)

    def _call_get_report(self: "UHIDDevice", req: U8, data: List[U8], err: int) -> None:
        bdata = bytes(data)
        buf = struct.pack(
            "< L L H H 4096s",
            UHIDDevice._UHID_GET_REPORT_REPLY,
            req,
            err,
            len(bdata),
            bdata,
        )
        os.write(self._fd, buf)

    def call_input_event(self: "UHIDDevice", _data: Iterable[int]) -> None:
        """
        Send an input event from this device.

        :param list data: a list of 8-bit integers representing the HID
            report for this input event
        """
        data: bytes = bytes(_data)
        buf = struct.pack("< L H 4096s", UHIDDevice._UHID_INPUT2, len(data), data)
        logger.debug(f"inject {buf[:len(data)]!r}")
        os.write(self._fd, buf)

    @property
    def sys_path(self: "UHIDDevice") -> Optional[Path]:
        """
        The device's /sys path
        """
        return self._sys_path

    def walk_sysfs(
        self: "UHIDDevice", kind: str, glob: Optional[str] = None
    ) -> Tuple[Path, ...]:
        kinds: Final = {
            "evdev": "input/input*/event*",
            "hidraw": "hidraw/hidraw*",
        }
        if glob is None and kind in kinds:
            glob = kinds[kind]
        if self._sys_path is None or glob is None:
            return tuple()

        return tuple(self._sys_path.glob(glob))

    @property
    def device_nodes(self) -> List[str]:
        """
        A list of evdev nodes associated with this HID device. Populating
        this list requires the kernel to process the uhid device, and sometimes
        the kernel needs to talk to the uhid process.
        Ensure that :meth:`dispatch` is called and that you wait for some
        reasonable time after creating the device.
        """
        return [f"/dev/input/{e.name}" for e in self.walk_sysfs("evdev")]

    @property
    def hidraw_nodes(self) -> List[str]:
        """
        A list of hidraw nodes associated with this HID device. Populating
        this list requires the kernel to process the uhid device, and sometimes
        the kernel needs to talk to the uhid process.
        Ensure that :meth:`dispatch` is called and that you wait for some
        reasonable time after creating the device.
        """
        return [f"/dev/{h.name}" for h in self.walk_sysfs("hidraw")]

    def create_kernel_device(self: "UHIDDevice") -> None:
        """
        Create a kernel device from this device. Note that the device is not
        immediately ready to go after creation, you must wait for
        :meth:`start` and ideally for :meth:`open` to be called.

        :raises: :class:`UHIDIncompleteException` if the device does not
            have a name, report descriptor or the info bits set.
        """
        if (
            self._name is None
            or self._rdesc is None
            or self._info is None
            or self._phys is None
        ):
            raise UHIDIncompleteException("missing uhid initialization")

        kus = UeventSocket()
        kus.bind()

        buf = struct.pack(
            "< L 128s 64s 64s H H L L L L 4096s",
            UHIDDevice._UHID_CREATE2,
            bytes(self._name, "utf-8"),  # name
            bytes(self._phys, "utf-8"),  # phys
            bytes(self.uniq, "utf-8"),  # uniq
            len(self._rdesc),  # rd_size
            self.bus,  # bus
            self.vid,  # vendor
            self.pid,  # product
            0,  # version
            0,  # country
            bytes(self._rdesc),
        )  # rd_data[HID_MAX_DESCRIPTOR_SIZE]

        logger.debug("creating kernel device")
        n = os.write(self._fd, buf)
        assert n == len(buf)

        # the kernel creates the device in a worker struct
        # when we are here, we might still not have the device created
        # and thus need to wait for incoming events. In practice, this
        # works at the first attempt
        found: Optional[Path] = None
        for _ in range(10):
            for uevent in kus.get():
                if uevent.get("HID_UNIQ", "") == self.uniq:
                    found = uevent
                    break
            if found is not None:
                break
            time.sleep(0.001)
        if found is not None:
            self._sys_path = Path("/sys") / uevent["DEVPATH"].lstrip("/")
            assert (
                self._sys_path is not None
            )  # shut up the linter for .name not found in None
            self.hid_id = int(self._sys_path.name[15:], 16)
            self._ready = True

    def destroy(self: "UHIDDevice") -> None:
        """
        Destroy the device. The kernel will trigger the appropriate
        messages in response before removing the device.

        This function is called automatically on __exit__()
        """

        if self._ready:
            buf = struct.pack("< L", UHIDDevice._UHID_DESTROY)
            os.write(self._fd, buf)
            self._ready = False
            # equivalent to dispatch() but just for our device.
            # this ensures that the callbacks are called correctly
            poll = select.poll()
            poll.register(self._fd, select.POLLIN)
            while poll.poll(1):
                fun = self._polling_functions[self._fd]
                fun()

        UHIDDevice._devices.remove(self)
        self._remove_fd_from_poll(self._fd)
        os.close(self._fd)
        self._is_destroyed = True

    def start(self: "UHIDDevice", flags: int) -> None:
        """
        Called when the uhid device is ready to accept IO.

        This message is sent by the kernel, to receive this message you must
        call :meth:`dispatch`
        """
        logger.debug("start")

    def stop(self: "UHIDDevice") -> None:
        """
        Called when the uhid device no longer accepts IO.

        This message is sent by the kernel, to receive this message you must
        call :meth:`dispatch`
        """
        logger.debug("stop")

    def open(self: "UHIDDevice") -> None:
        """
        Called when a userspace client opens the created kernel device.

        This message is sent by the kernel, to receive this message you must
        call :meth:`dispatch`
        """
        logger.debug("open {}".format(self.sys_path))

    def close(self: "UHIDDevice") -> None:
        """
        Called when a userspace client closes the created kernel device.

        Sending events on a closed device will not result in anyone reading
        it.

        This message is sent by the kernel, to receive this message you must
        call :meth:`dispatch`
        """
        logger.debug("close")

    def set_report(
        self: "UHIDDevice", req: int, rnum: int, rtype: int, data: List[int]
    ) -> int:
        """
        Callback invoked when a process calls SetReport on this UHID device.

        Return ``0`` on success or an errno on failure.

        The default method always returns ``EIO`` for a failure. Override
        this in your device if you want SetReport to succeed.

        :param req: the request identifier
        :param rnum: ???
        :param rtype: one of :attr:`UHID_FEATURE_REPORT`, :attr:`UHID_INPUT_REPORT`, or :attr:`UHID_OUTPUT_REPORT`
        :param list data: a byte string with the data
        """
        return 5  # EIO

    def _set_report(
        self: "UHIDDevice", req: int, rnum: int, rtype: int, size: int, data: List[int]
    ) -> None:
        logger.debug(
            "set report {} {} {} {} {} ".format(
                req, rnum, rtype, size, [f"{d:02x}" for d in data[:size]]
            )
        )
        error = self.set_report(req, rnum, rtype, [int(x) for x in data[:size]])
        if self._ready:
            self._call_set_report(req, error)

    def get_report(
        self: "UHIDDevice", req: int, rnum: int, rtype: int
    ) -> Tuple[int, List[U8]]:
        """
        Callback invoked when a process calls SetReport on this UHID device.

        Return ``(0, [data bytes])`` on success or ``(errno, [])`` on
        failure.

        The default method always returns ``(EIO, [])`` for a failure.
        Override this in your device if you want GetReport to succeed.

        :param req: the request identifier
        :param rnum: ???
        :param rtype: one of :attr:`UHID_FEATURE_REPORT`, :attr:`UHID_INPUT_REPORT`, or :attr:`UHID_OUTPUT_REPORT`
        """
        return (5, [])  # EIO

    def _get_report(self: "UHIDDevice", req: int, rnum: int, rtype: int) -> None:
        logger.debug("get report {} {} {}".format(req, rnum, rtype))
        error, data = self.get_report(req, rnum, rtype)
        if self._ready:
            self._call_get_report(req, data, error)

    def output_report(
        self: "UHIDDevice", data: List[int], size: int, rtype: int
    ) -> None:
        """
        Callback invoked when a process sends raw data to the device.

        :param data: the data sent by the kernel
        :param size: size of the data
        :param rtype: one of :attr:`UHID_FEATURE_REPORT`, :attr:`UHID_INPUT_REPORT`, or :attr:`UHID_OUTPUT_REPORT`
        """
        logger.debug(
            "output {} {} {}".format(rtype, size, [f"{d:02x}" for d in data[:size]])
        )

    def _process_one_event(self: "UHIDDevice") -> None:
        buf = os.read(self._fd, 4380)
        assert (len(buf) == 4380) or (len(buf) == 4376)
        evtype = struct.unpack_from("< L", buf)[0]
        if evtype == UHIDDevice._UHID_START:
            ev, flags = struct.unpack_from("< L Q", buf)
            self.start(flags)
        elif evtype == UHIDDevice._UHID_OPEN:
            self._open()
        elif evtype == UHIDDevice._UHID_STOP:
            self._stop()
        elif evtype == UHIDDevice._UHID_CLOSE:
            self._close()
        elif evtype == UHIDDevice._UHID_SET_REPORT:
            ev, req, rnum, rtype, size, data = struct.unpack_from(
                "< L L B B H 4096s", buf
            )
            self._set_report(req, rnum, rtype, size, data)
        elif evtype == UHIDDevice._UHID_GET_REPORT:
            ev, req, rnum, rtype = struct.unpack_from("< L L B B", buf)
            self._get_report(req, rnum, rtype)
        elif evtype == UHIDDevice._UHID_OUTPUT:
            ev, data, size, rtype = struct.unpack_from("< L 4096s H B", buf)
            self._output_report(data, size, rtype)

    def create_report(
        self: "UHIDDevice",
        data: Any,
        global_data=None,
        reportID: Optional[int] = None,
        application: Optional[Union[str, U32]] = None,
    ) -> List[U8]:
        """
        Convert the data object to an array of ints representing the report.
        Each property of the given data object is matched against the field
        usage name (think ``hasattr``) and filled in accordingly.::

            mouse = MouseData()
            mouse.b1 = int(l)
            mouse.b2 = int(r)
            mouse.b3 = int(m)
            mouse.x = x
            mouse.y = y

            data_bytes = uhid_device.create_report(mouse)

        The :class:`UHIDDevice` will create the report according to the
        device's report descriptor.
        """
        if self.parsed_rdesc is None:
            return []
        return self.parsed_rdesc.create_report(data, global_data, reportID, application)
