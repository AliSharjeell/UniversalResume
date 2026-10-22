"""A tiny protobuf wire-format codec.

Only what Antigravity's trajectory steps need: read a message into its fields, change a
few, and write it back. Fields keep their original order and wire type, so a message that
came out of Antigravity goes back in looking the same.
"""


def read_varint(buf, i):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, i
        shift += 7


def write_varint(val):
    out = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode(buf):
    """A message as a list of (field number, wire type, value) in the order they appeared."""
    out = []
    i, n = 0, len(buf)
    while i < n:
        key, i = read_varint(buf, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = read_varint(buf, i)
        elif wire == 1:
            value = buf[i:i + 8]
            i += 8
        elif wire == 2:
            ln, i = read_varint(buf, i)
            value = buf[i:i + ln]
            i += ln
        elif wire == 5:
            value = buf[i:i + 4]
            i += 4
        else:
            raise ValueError(f'unsupported protobuf wire type {wire}')
        out.append([field, wire, value])
    return out


def encode(fields):
    out = bytearray()
    for field, wire, value in fields:
        out += write_varint((field << 3) | wire)
        if wire == 0:
            out += write_varint(value)
        elif wire == 1:
            out += value
        elif wire == 2:
            out += write_varint(len(value))
            out += value
        elif wire == 5:
            out += value
    return bytes(out)


def get(fields, number):
    """Every value carried for a field number."""
    return [value for field, _, value in fields if field == number]


def first(fields, number, default=None):
    vals = get(fields, number)
    return vals[0] if vals else default


def set_field(fields, number, value, wire=2):
    """Replace a field's value in place, or append it."""
    for item in fields:
        if item[0] == number:
            item[1], item[2] = wire, value
            return fields
    fields.append([number, wire, value])
    return fields


def drop_field(fields, number):
    return [item for item in fields if item[0] != number]


def sub(fields, number):
    """A nested message for a field, decoded."""
    raw = first(fields, number)
    return decode(raw) if isinstance(raw, (bytes, bytearray)) else []


def strings(buf):
    """Every printable string in a message, with the field path it came from."""
    out = []

    def walk(fields, path):
        for field, _, value in fields:
            if not isinstance(value, (bytes, bytearray)):
                continue
            try:
                text = bytes(value).decode('utf-8')
            except UnicodeDecodeError:
                text = None
            if text and all(ch in '\n\t' or 32 <= ord(ch) < 127 for ch in text):
                out.append((f'{path}.{field}', text))
                continue
            try:
                walk(decode(value), f'{path}.{field}')
            except Exception:
                pass

    walk(decode(buf), '')
    return out
