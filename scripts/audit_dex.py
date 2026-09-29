#!/usr/bin/env python3
"""Check DEX invoke word counts at instruction boundaries parsed by dexdump.

This targeted structural audit supplements, but does not replace, ART testing.
"""
import hashlib
import re
import struct
import zlib

SETTINGS = "Lcom/armsx2/config/Settings;"


def argument_words(descriptor):
    words = 0
    i = 0
    while i < len(descriptor):
        array = descriptor[i] == "["
        while descriptor[i] == "[":
            i += 1
        c = descriptor[i]
        if c == "L":
            i = descriptor.index(";", i)
        words += 1 if array or c not in "JD" else 2
        i += 1
    return words


def audit(data, disassembly):
    if data[:4] != b"dex\n" or data[7] != 0:
        raise ValueError("Not a standard DEX file")
    if struct.unpack_from("<I", data, 8)[0] != zlib.adler32(data[12:]):
        raise ValueError("DEX checksum mismatch")
    if data[12:32] != hashlib.sha1(data[32:]).digest():
        raise ValueError("DEX signature mismatch")
    u4 = lambda p: struct.unpack_from("<I", data, p)[0]
    u2 = lambda p: struct.unpack_from("<H", data, p)[0]
    if u4(32) != len(data) or u4(40) != 0x12345678:
        raise ValueError("DEX size/endian mismatch")

    def string_at(offset):
        # Skip ULEB128 UTF-16 length; relevant descriptors/names are ASCII.
        while data[offset] & 128:
            offset += 1
        offset += 1
        return data[offset:data.index(0, offset)].decode("utf-8", errors="replace")

    strings = [string_at(u4(u4(60) + 4*i)) for i in range(u4(56))]
    types = [strings[u4(u4(68) + 4*i)] for i in range(u4(64))]
    prototypes = []
    for i in range(u4(72)):
        off = u4(u4(76) + 12*i + 8)
        prototypes.append("" if not off else "".join(types[u2(off+4+2*j)] for j in range(u4(off))))
    methods = []
    settings_constructor = 0
    for i in range(u4(88)):
        off = u4(92) + 8*i
        owner, proto, name = types[u2(off)], prototypes[u2(off+2)], strings[u4(off+4)]
        methods.append((owner, name, proto))
        if owner == SETTINGS:
            if name == "copy$default" or (name == "<init>" and (not proto or "DefaultConstructorMarker" in proto)):
                raise ValueError(f"Unsafe Settings method retained: {name}({proto})")
            if name == "<init>":
                settings_constructor += 1
                if argument_words(proto) != 246:
                    raise ValueError("Unexpected Settings constructor word count")

    count = 0
    for line in disassembly.splitlines():
        match = re.match(r"\s*([0-9a-fA-F]+):.*\|[0-9a-fA-F]+:\s+invoke-(?:virtual|super|direct|static|interface)(?:/range)?\s", line)
        if not match:
            continue
        off = int(match[1], 16)
        opcode, high = data[off], data[off+1]
        if opcode not in (*range(0x6e, 0x73), *range(0x74, 0x79)):
            raise ValueError(f"Unexpected invoke opcode at {off:x}")
        owner, name, proto = methods[u2(off+2)]
        actual = high if opcode >= 0x74 else high >> 4
        expected = argument_words(proto) + (opcode not in (0x71, 0x77))
        if actual != expected:
            raise ValueError(f"invoke at {off:x}: {owner}.{name} expected {expected} words, encoded {actual}")
        if opcode < 0x74 and actual > 5:
            raise ValueError("Non-range invoke exceeds five words")
        count += 1
    if not count:
        raise ValueError("No supported invokes inspected; dexdump format may have changed")
    return {"invokes_checked": count, "settings_constructors": settings_constructor}
