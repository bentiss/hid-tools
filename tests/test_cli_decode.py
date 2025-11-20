#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Red Hat, Inc.
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

from dataclasses import dataclass
from tests_kernel.base import UHIDTestDevice
from hidtools.cli.decode import main as decode
from click.testing import CliRunner
from pathlib import Path
import logging
import pytest
import re

from typing import Iterator, Optional, Union

logger = logging.getLogger("hidtools.test.cli.decode")


RDESC_NORMAL = """
R: 67 05 01 09 02 a1 01 09 01 a1 00 05 09 19 01 29 10 15 00 25 01 95 10 75 01 81 02 05 01 16 01 80 26 ff 7f 75 10 95 02 09 30 09 31 81 06 15 81 25 7f 75 08 95 01 09 38 81 06 05 0c 0a 38 02 95 01 81 06 c0 c0
N: Logitech G500s Laser Gaming Mouse
I: 3 046d c24e
"""

RDESC_BINARY = b"\x05\x01\t\x06\xa1\x01\x85\x01\x05\x07\x19\xe0)\xe7\x15\x00%\x01u\x01\x95\x08\x81\x02\x95\x05u\x08\x15\x00&\xa4\x00\x05\x07\x19\x00*\xa4\x00\x81\x00\xc0\x05\x0c\t\x01\xa1\x01\x85\x03u\x10\x95\x02\x15\x01&\x8c\x02\x19\x01*\x8c\x02\x81\x00\xc0\x06\x00\xff\t\x01\xa1\x01\x85\x10u\x08\x95\x06\x15\x00&\xff\x00\t\x01\x81\x00\t\x01\x91\x00\xc0\x06\x00\xff\t\x02\xa1\x01\x85\x11u\x08\x95\x13\x15\x00&\xff\x00\t\x02\x81\x00\t\x02\x91\x00\xc0"

RDESC_MULTIREPORT = """
R: 945 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0
R: 945 05 0d 09 04 a1 01 85 01 09 22 a1 02 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 22 a1 02 05 0d 09 42 15 00 25 01 75 01 95 01 81 02 75 01 81 03 75 06 09 51 25 3f 81 02 26 ff 00 75 08 09 48 81 02 09 49 81 02 95 01 05 01 a4 26 80 0f 75 10 55 0f 65 11 09 30 35 00 46 35 01 95 02 81 02 26 c0 08 46 ae 00 09 31 81 02 b4 c0 05 0d 09 56 55 00 65 00 27 ff ff ff 7f 95 01 75 20 81 02 09 54 25 7f 95 01 75 08 81 02 85 0a 09 55 25 0a b1 02 85 44 06 00 ff 09 c5 15 00 26 ff 00 75 08 96 00 01 b1 02 c0 06 ff 01 09 01 a1 01 85 02 15 00 26 ff 00 75 08 95 40 09 00 81 02 c0 06 00 ff 09 01 a1 01 85 03 75 08 95 1f 09 01 91 02 c0 06 01 ff 09 01 a1 01 85 04 15 00 26 ff 00 75 08 95 13 09 00 81 02 c0
"""

RDESC_COMMENTS = """
# Logitech G500s Laser Gaming Mouse
# 0x05, 0x01,                    // Usage Page (Generic Desktop)        0
# 0x09, 0x02,                    // Usage (Mouse)                       2
# 0xa1, 0x01,                    // Collection (Application)            4
# 0x09, 0x01,                    //  Usage (Pointer)                    6
# 0xa1, 0x00,                    //  Collection (Physical)              8
# 0x05, 0x09,                    //   Usage Page (Button)               10
# 0x19, 0x01,                    //   Usage Minimum (1)                 12
# 0x29, 0x10,                    //   Usage Maximum (16)                14
# 0x15, 0x00,                    //   Logical Minimum (0)               16
# 0x25, 0x01,                    //   Logical Maximum (1)               18
# 0x95, 0x10,                    //   Report Count (16)                 20
# 0x75, 0x01,                    //   Report Size (1)                   22
# 0x81, 0x02,                    //   Input (Data,Var,Abs)              24
# 0x05, 0x01,                    //   Usage Page (Generic Desktop)      26
# 0x16, 0x01, 0x80,              //   Logical Minimum (-32767)          28
# 0x26, 0xff, 0x7f,              //   Logical Maximum (32767)           31
# 0x75, 0x10,                    //   Report Size (16)                  34
# 0x95, 0x02,                    //   Report Count (2)                  36
# 0x09, 0x30,                    //   Usage (X)                         38
# 0x09, 0x31,                    //   Usage (Y)                         40
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              42
# 0x15, 0x81,                    //   Logical Minimum (-127)            44
# 0x25, 0x7f,                    //   Logical Maximum (127)             46
# 0x75, 0x08,                    //   Report Size (8)                   48
# 0x95, 0x01,                    //   Report Count (1)                  50
# 0x09, 0x38,                    //   Usage (Wheel)                     52
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              54
# 0x05, 0x0c,                    //   Usage Page (Consumer Devices)     56
# 0x0a, 0x38, 0x02,              //   Usage (AC Pan)                    58
# 0x95, 0x01,                    //   Report Count (1)                  61
# 0x81, 0x06,                    //   Input (Data,Var,Rel)              63
# 0xc0,                          //  End Collection                     65
# 0xc0,                          // End Collection                      66
#
R: 67 05 01 09 02 a1 01 09 01 a1 00 05 09 19 01 29 10 15 00 25 01 95 10 75 01 81 02 05 01 16 01 80 26 ff 7f 75 10 95 02 09 30 09 31 81 06 15 81 25 7f 75 08 95 01 09 38 81 06 05 0c 0a 38 02 95 01 81 06 c0 c0
N: Logitech G500s Laser Gaming Mouse
I: 3 046d c24e
"""


@dataclass
class HidDecodeOutput:
    """
    The stdout from hid-decode in various converted formats
    """

    lines: list[str]

    @property
    def as_str(self) -> str:
        return "\n".join(self.lines)

    @property
    def initial_rdesc_dump(self) -> list[str]:
        """
        Returns the initial dump of the human-readable report descriptor
        with the comment prefixes removed
        """
        output = [o.lstrip("# ") for o in self.lines if o.startswith("# ")]
        return [o for o in output if o.strip() and "device " not in o]

    @property
    def as_int_list(self) -> list[int]:
        """Convert the hid-decode output into a list of bytes"""
        items = ", ".join(self.initial_rdesc_dump).split(", ")
        return [int(b, 16) for b in items if b.startswith("0x")]

    @property
    def as_bytes(self) -> bytes:
        return bytes(self.as_int_list)

    @classmethod
    def from_file(cls, path: Path) -> "HidDecodeOutput":
        return cls(lines=path.read_text().split("\n"))


def run_hid_decode(
    args: list[str],
    data: Optional[Union[str, bytes]],
    source_file: Optional[Path] = None,
) -> HidDecodeOutput:
    runner = CliRunner()
    with runner.isolated_filesystem():
        if source_file:
            assert data is None
            runner.invoke(decode, args + ["--output", "output.txt", str(source_file)])
        else:
            assert data is not None
            with open("report-descriptor.hid", "wb") as sourcefile:
                if isinstance(data, str):
                    data = bytes(data, encoding="utf-8")
                elif isinstance(data, list):
                    data = bytes(data)
                sourcefile.write(data)

            runner.invoke(decode, args + ["--output", "output.txt", sourcefile.name])
        return HidDecodeOutput.from_file(Path("output.txt"))


@pytest.fixture(
    params=[RDESC_NORMAL, RDESC_BINARY, RDESC_MULTIREPORT, RDESC_COMMENTS],
    ids=["normal", "binary", "multireport", "comments"],
)
def rdesc(request) -> Iterator[Union[str, bytes]]:
    yield request.param


@pytest.mark.parametrize("args", [[], ["--verbose"]], ids=["none", "verbose"])
class TestHidRecorder:
    def test_read(self, args, rdesc):
        output = run_hid_decode(args, rdesc)
        assert output.initial_rdesc_dump is not None

    def test_basic_elements(self, args, rdesc):
        output = run_hid_decode(args, rdesc)
        output_str = output.as_str
        assert "Usage (" in output_str
        assert "Usage Page (" in output_str
        assert "Collection (Application)" in output_str
        assert "End Collection" in output_str

    def test_format(self, args, rdesc):
        output = run_hid_decode(args, rdesc)
        for line in output.initial_rdesc_dump:
            if "End Collection" in line:
                assert re.search("0xc0, *// +End Collection *[0-9]+", line), line
            elif "Push" in line:
                assert re.search("0xa4, *// +Push *[0-9]+", line), line
            elif "Pop" in line:
                assert re.search("0xb4, *// +Pop *[0-9]+", line), line
            elif line == "**** win 8 certified ****":
                pass
            else:
                assert re.search(
                    "0x[0-9a-f][0-9a-f], 0x[0-9a-f][0-9a-f], *// .*", line
                ), line

    @pytest.mark.parametrize(
        "rdescriptor,usage_id, usage",
        [
            (RDESC_NORMAL, 0x2, "Mouse"),
        ],
        ids=["normal"],
    )
    def test_dump(self, args, rdescriptor, usage_id, usage):
        output = run_hid_decode(args, rdescriptor)
        initial_dump = output.initial_rdesc_dump
        assert re.match(
            r"0x05, 0x01, +// +Usage Page \(Generic Desktop\) +0", initial_dump[0]
        )
        assert re.match(
            rf"0x09, 0x{usage_id:02x}, +// +Usage \({usage}\) +2", initial_dump[1]
        )
        assert "End Collection" in initial_dump[-1]
        assert "End Collection" in initial_dump[-2]

        bytelist = output.as_int_list
        strbytes = " ".join(f"{x:02x}" for x in bytelist)
        expected = f"R: {len(bytelist)} {strbytes}"
        assert rdescriptor.split("\n")[1] == expected


class TestHidRecorderOnUHIDDevice:
    @pytest.fixture
    def uhid_rdesc(self) -> list[int]:
        # fmt: off
        return [
            0x05, 0x01,  # .Usage Page (Generic Desktop)        0
            0x09, 0x02,  # .Usage (Mouse)                       2
            0xA1, 0x01,  # .Collection (Application)            4
            0x09, 0x02,  # ..Usage (Mouse)                      6
            0xA1, 0x02,  # ..Collection (Logical)               8
            0x09, 0x01,  # ...Usage (Pointer)                   10
            0xA1, 0x00,  # ...Collection (Physical)             12
            0x05, 0x09,  # ....Usage Page (Button)              14
            0x19, 0x01,  # ....Usage Minimum (1)                16
            0x29, 0x03,  # ....Usage Maximum (3)                18
            0x15, 0x00,  # ....Logical Minimum (0)              20
            0x25, 0x01,  # ....Logical Maximum (1)              22
            0x75, 0x01,  # ....Report Size (1)                  24
            0x95, 0x03,  # ....Report Count (3)                 26
            0x81, 0x02,  # ....Input (Data,Var,Abs)             28
            0x75, 0x05,  # ....Report Size (5)                  30
            0x95, 0x01,  # ....Report Count (1)                 32
            0x81, 0x03,  # ....Input (Cnst,Var,Abs)             34
            0x05, 0x01,  # ....Usage Page (Generic Desktop)     36
            0x09, 0x30,  # ....Usage (X)                        38
            0x09, 0x31,  # ....Usage (Y)                        40
            0x15, 0x81,  # ....Logical Minimum (-127)           42
            0x25, 0x7F,  # ....Logical Maximum (127)            44
            0x75, 0x08,  # ....Report Size (8)                  46
            0x95, 0x02,  # ....Report Count (2)                 48
            0x81, 0x06,  # ....Input (Data,Var,Rel)             50
            0xC0,        # ...End Collection                    52
            0xC0,        # ..End Collection                     53
            0xC0,        # .End Collection                      54
        ]
        # fmt: on

    @pytest.fixture
    def uhid_device(self, uhid_rdesc) -> Iterator[UHIDTestDevice]:
        try:
            uhid_device = UHIDTestDevice("hidraw test", "Mouse", rdesc=uhid_rdesc)
        except PermissionError:
            pytest.skip("Insufficient permissions, run me as root")
        uhid_device.create_kernel_device()
        while not uhid_device.device_nodes or not uhid_device.hidraw_nodes:
            uhid_device.dispatch(10)

        yield uhid_device

        uhid_device.destroy()
        uhid_device.dispatch(10)

    def test_sysfs_rdesc_match(self, uhid_rdesc, uhid_device):
        """
        After creating our uhid device, make sure that the report descriptor
        bytes in sysfs match the ones we've created the device with.
        """
        node = uhid_device.device_nodes[0]
        assert node.startswith("/dev/input/")
        node = node[len("/dev/input/") :]
        sysfs = f"/sys/class/input/{node}/device/device/report_descriptor"
        data = open(sysfs, "rb").read()
        output = run_hid_decode([], data=uhid_rdesc)
        assert data == output.as_bytes

    def test_rdesc_match(self, uhid_rdesc):
        """
        Check that the rdesc printed matches the one we
        get back from hid-decode.
        """
        output = run_hid_decode(args=[], data=uhid_rdesc)
        assert uhid_rdesc == output.as_int_list

    @pytest.mark.parametrize("node", ["hidraw", "evdev"])
    def test_pass_event_node(self, uhid_rdesc, uhid_device, node):
        # same as above, but passes the event node into hid-decode
        if node == "hidraw":
            source = uhid_device.hidraw_nodes[0]
        else:
            source = uhid_device.device_nodes[0]
        output = run_hid_decode(args=[], data=None, source_file=source)
        assert uhid_rdesc == output.as_int_list
