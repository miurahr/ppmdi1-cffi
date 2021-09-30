#
# Copyright (c) 2019,2020 Hiroshi Miura <miurahr@linux.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import argparse
import os
import pathlib
import struct
import sys
import time
from datetime import datetime, timezone
from typing import Any, BinaryIO, Optional

__copyright__ = 'Copyright (C) 2021 Hiroshi Miura'

from _ppmd import ffi, lib  # type: ignore  # noqa

READ_BLOCKSIZE = 16384

def dostime_to_dt(dosdate, dostime):
    """Convert a DOS time to a Python time tuple."""
    day = dosdate & 0x1f
    month = (dosdate >> 5) & 0xf
    year = 1980 + (dosdate >> 9)
    second = 2 * (dostime & 0x1f)
    minute = (dostime >> 5) & 0x3f
    hour = dostime >> 11
    return datetime(year, month, day, hour=hour, minute=minute, second=second, tzinfo=timezone.utc)


def dt_to_dostime(dt):
    dosdate = (dt.year - 1980) << 9
    dosdate |= dt.month << 5
    dosdate |= dt.day
    dostime = dt.second // 2
    dostime |= dt.minute << 5
    dostime |= dt.hour << 11
    return (dosdate, dostime)


def datetime_to_timestamp(dt):
    return time.mktime(dt.timetuple()) + dt.microsecond / 1e6


@ffi.def_extern()
def dst_write(b: bytes, size: int, userdata: object) -> None:
    encoder = ffi.from_handle(userdata)
    buf = ffi.buffer(b, size)
    encoder.destination.write(buf)


@ffi.def_extern()
def src_readinto(b: bytes, size: int, userdata: object) -> int:
    decoder = ffi.from_handle(userdata)
    buf = ffi.buffer(b, size)
    result = decoder.source.readinto(buf)
    return result


_allocated = []


@ffi.def_extern()
def raw_alloc(size: int) -> object:
    if size == 0:
        return ffi.NULL
    block = ffi.new("char[]", size)
    _allocated.append(block)
    return block


@ffi.def_extern()
def raw_free(o: object) -> None:
    if o in _allocated:
        _allocated.remove(o)


class PpmdI1Decoder:

    def __init__(self, source: BinaryIO, max_order: int, mem_size: int, restore: int):
        self.closed = False
        self.source = source
        self.model = ffi.new('PPMdModelVariantI *')
        self.reader = ffi.new('RawReader *')
        self._userdata = ffi.new_handle(self)
        self.max_order = max_order  # type: int
        self.mem_size = mem_size  # type: int
        self.restore = restore  # type: int

    def decode(self, length):
        outbuf = bytearray()
        for _ in range(length):
            sym = lib.NEXTPPMdVariantIByte(self.model)
            if sym < 0:
                break
            outbuf += sym.to_bytes(1, 'little')
        return bytes(outbuf)

    def close(self):
        if not self.closed:
            ffi.release(self.reader)
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
