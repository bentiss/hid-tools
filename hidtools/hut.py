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
import parse


DATA_DIRNAME = "data"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, DATA_DIRNAME)

class HidUsagePage(dict):
    """
    A dictionary of HID Usages in the form ``{ usage: usage_name}``,
    representing all Usages in this Usage Page.

    A HID Usage is named semantical identifier that describe how a given
    field in a HID report is to be used. A Usage Page is a logical grouping
    of those identifiers, e.g. "Generic Desktop", "Telephony Devices", or
    "Digitizers".  ::

        > print(usage_page.page_name)
        Generic Desktop
        > print(usage_page.page_id)
        1
        > print(usage_page[0x02])
        Mouse
        > print(usage_page.from_name["Mouse"])
        2

    .. attribute:: page_id

        The Page ID for this Usage Page, e.g. ``01`` (Generic Desktop)

    .. attribute:: page_name

        The assigned name for this usage Page, e.g. "Generic Desktop"

    """
    @property
    def page_id(self):
        """
        The numerical page ID for this usage page
        """
        return self._page_id

    @page_id.setter
    def page_id(self, page_id):
        self._page_id = page_id

    @property
    def page_name(self):
        """
        The assigned name for this Usage Page
        """
        return self._name

    @page_name.setter
    def page_name(self, name):
        self._name = name

    @property
    def from_name(self):
        """
        A dictionary using ``{ name: usage }`` mapping, to look up the usage
        based on a name.
        """
        try:
            return self._inverted
        except AttributeError:
            self._inverted = {}
            for k, v in self.items():
                self._inverted[v] = k
            return self._inverted

    @property
    def from_usage(self):
        """
        A dictionary using ``{ usage: name }`` mapping, to look up the name
        based on a page ID . This is the same as using the object itself.
        """
        return self


class HidUsageTable(dict):
    """
    This is a dictionary wrapper that all HID Usages known to man. Or to
    this module at least.

    This dict is laid out as ``{page_id : usage_page_object}``
    (:class:`HidUsagePage`)

    This object is a dictionary, use like this: ::

        > print(usages[0x01].page_name)
        Generic Desktop
        > print(usages.usage_pages[0x01].page_name)
        Generic Desktop
        > print(usages[0x01].page_id)
        1
        > print(usages.usage_page_from_name('Generic Desktop').page_id)
        1
        > print(usages.usage_page_from_page_id(0x01).page_name)
        Generic Desktop
    """

    @property
    def usage_pages(self):
        """
        A dictionary mapping ``{page_id : object}``
        """
        return self

    def usage_page_from_name(self, page_name):
        """
        Look up the usage page based on the page name (e.g. "Generic
        Desktop").

        :return: the :meth:`HidUsagePage` or None
        """
        for k, v in self.items():
            if v.page_name == page_name:
                return v
        return None

    def usage_page_from_page_id(self, page_id):
        """
        Look up the usage page based on the page ID. This is identical to
        calling::

                self.usage_pages[page_id]

        except that this function returns None if the page ID is unknown.

        :return: the :meth:`HidUsagePage` or None
        """
        try:
            return self[page_id]
        except KeyError:
            return None

    @classmethod
    def _parse_usages(cls, f):
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

                r = parse.parse('({idx:x})\t{page_name}', line)
                assert(r is not None)
                usage_page = HidUsagePage()
                usage_page.page_id = r['idx']
                usage_page.page_name = r['page_name']
                continue

            assert usage_page is not None

            # Reserved ranges, e.g  '0B-1F	Reserved'
            r = parse.parse('{:x}-{:x}\t{name}', line)
            if r:
                if 'reserved' not in r['name'].lower():
                    print(line)
                continue

            # Single usage, e.g. 36	Slider
            # we can not use {usage:x} or the value '0B' will be converted to 0
            # See https://github.com/r1chardj0n3s/parse/issues/65
            # fixed in parse 1.8.4 (May 2018)
            r = parse.parse('{usage}\t{name}', line)
            assert r is not None
            if 'reserved' in r['name'].lower():
                continue

            usage_page[int(r['usage'], 16)] = r['name']

        return usage_page


    @classmethod
    def _from_hut_data(cls):
        """
        Return the HID Usage Tables as a dictionary where the keys are the
        numeric Usage Page and the values are the respective
        :class:`hidtools.HidUsagePage` object. ::

            > usages = hidtools.hut.HUT()
            > print(usages[0x01].page_name)
            Generic Desktop
            > print(usages.usage_pages[0x01].page_name)
            Generic Desktop
            > print(usages[0x01].page_id)
            1

        :return: a :class:`hidtools.HidUsageTable` object
        """
        hut = HidUsageTable()
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.hut'):
                with open(os.path.join(DATA_DIR, filename), 'r') as f:
                    try:
                        usage_page = cls._parse_usages(f)
                        hut[usage_page.page_id] = usage_page
                    except:
                        print(filename)
                        raise

        return hut

HUT = HidUsageTable._from_hut_data()
"""
The HID Usage Tables as a :class:`hidtools.HidUsageTable` object,
a dictionary where the keys are the numeric Usage Page and the values are
the respective :class:`hidtools.HidUsagePage` object. ::

    > usages = hidtools.hut.HUT()
    > print(usages[0x01].page_name)
    Generic Desktop
    > print(usages.usage_pages[0x01].page_name)
    Generic Desktop
    > print(usages[0x01].page_id)
    1
"""
