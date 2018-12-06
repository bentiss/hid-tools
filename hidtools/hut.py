#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2017 Benjamin Tissoires <benjamin.tissoires@gmail.com>
# Copyright (c) 2012-2017 Red Hat, Inc.
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

import os
from parse import parse as _parse
from hidtools import HidUsagePage, HidUsageTable


DATA_DIRNAME = "data"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, DATA_DIRNAME)


def _parse_usages(f):
    """
    Parse a single HUT file. The file format is a set of lines in three
    formats: ::

        (01)<tab>Usage Page name
        A0<tab>Name
        F0-FF<tab>Reserved for somerange

    All numbers in hex.

    Only one Usage Page per file

    Usages are parsed into a dictionary[number] = name.

    The return value is a single HidUsagePage where page[idx] = idx-name.
    """
    usage_page = None
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Usage Page, e.g. '(01)	Generic Desktop'
        if line.startswith('('):
            assert usage_page is None

            r = _parse('({idx:x})\t{page_name}', line)
            assert(r is not None)
            usage_page = HidUsagePage()
            usage_page.page_id = r['idx']
            usage_page.page_name = r['page_name']
            continue

        assert usage_page is not None

        # Reserved ranges, e.g  '0B-1F	Reserved'
        r = _parse('{:x}-{:x}\t{name}', line)
        if r:
            if 'reserved' not in r['name'].lower():
                print(line)
            continue

        # Single usage, e.g. 36	Slider
        # we can not use {usage:x} or the value '0B' will be converted to 0
        # See https://github.com/r1chardj0n3s/parse/issues/65
        # fixed in parse 1.8.4 (May 2018)
        r = _parse('{usage}\t{name}', line)
        assert r is not None
        if 'reserved' in r['name'].lower():
            continue

        usage_page[int(r['usage'], 16)] = r['name']

    return usage_page


USAGES = None

def usages():
    """
    Return the HID Usage Tables as a dictionary where the keys are the
    numeric Usage Page and the values are the respective
    :class:`hidtools.HidUsagePage` object. ::

        > usages = hut.usages()
        > print(usages[0x01].page_name)
        Generic Desktop
        > print(usages.usage_pages[0x01].page_name)
        Generic Desktop
        > print(usages[0x01].page_id)
        1

    :return: a :class:`hidtools.HidUsageTable` object
    """
    global USAGES

    if USAGES is not None:
        return USAGES

    usages = HidUsageTable()
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.hut'):
            with open(os.path.join(DATA_DIR, filename), 'r') as f:
                try:
                    usage_page = _parse_usages(f)
                    usages[usage_page.page_id] = usage_page
                except:
                    print(filename)
                    raise

    USAGES = usages
    return usages