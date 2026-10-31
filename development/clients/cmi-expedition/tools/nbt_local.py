"""Minimal NBT I/O for disposable local world metadata, without external packages."""
import gzip
import io
import struct
from dataclasses import dataclass


@dataclass
class Tag:
    kind: int
    value: object


FORMATS = {1: 'b', 2: 'h', 3: 'i', 4: 'q', 5: 'f', 6: 'd'}


def read_string(stream):
    size = struct.unpack('>H', stream.read(2))[0]
    return stream.read(size).decode('utf-8', 'surrogatepass')


def write_string(stream, value):
    data = value.encode('utf-8', 'surrogatepass')
    stream.write(struct.pack('>H', len(data)))
    stream.write(data)


def read_payload(stream, kind):
    if kind in FORMATS:
        fmt = '>' + FORMATS[kind]
        return Tag(kind, struct.unpack(fmt, stream.read(struct.calcsize(fmt)))[0])
    if kind == 8:
        return Tag(kind, read_string(stream))
    if kind in (7, 11, 12):
        size = struct.unpack('>i', stream.read(4))[0]
        unit = {7: 1, 11: 4, 12: 8}[kind]
        return Tag(kind, (size, stream.read(size * unit)))
    if kind == 9:
        child = stream.read(1)[0]
        size = struct.unpack('>i', stream.read(4))[0]
        return Tag(kind, (child, [read_payload(stream, child) for _ in range(size)]))
    if kind == 10:
        values = {}
        while True:
            child = stream.read(1)[0]
            if child == 0:
                break
            name = read_string(stream)
            values[name] = read_payload(stream, child)
        return Tag(kind, values)
    raise ValueError('Unsupported NBT tag ' + str(kind))


def write_payload(stream, tag):
    kind, value = tag.kind, tag.value
    if kind in FORMATS:
        stream.write(struct.pack('>' + FORMATS[kind], value))
    elif kind == 8:
        write_string(stream, value)
    elif kind in (7, 11, 12):
        stream.write(struct.pack('>i', value[0]))
        stream.write(value[1])
    elif kind == 9:
        child, values = value
        stream.write(bytes([child]) + struct.pack('>i', len(values)))
        for item in values:
            assert item.kind == child
            write_payload(stream, item)
    elif kind == 10:
        for name, item in value.items():
            stream.write(bytes([item.kind]))
            write_string(stream, name)
            write_payload(stream, item)
        stream.write(b'\0')
    else:
        raise ValueError('Unsupported NBT tag ' + str(kind))


def loads(data):
    stream = io.BytesIO(data)
    kind = stream.read(1)[0]
    name = read_string(stream)
    return name, read_payload(stream, kind)


def dumps(named_tag):
    name, tag = named_tag
    stream = io.BytesIO()
    stream.write(bytes([tag.kind]))
    write_string(stream, name)
    write_payload(stream, tag)
    return stream.getvalue()


def load(path):
    raw = gzip.decompress(path.read_bytes())
    result = loads(raw)
    assert dumps(result) == raw, 'NBT round-trip changed untouched metadata'
    return result


def save(path, named_tag):
    raw = dumps(named_tag)
    assert dumps(loads(raw)) == raw
    path.write_bytes(gzip.compress(raw, mtime=0))


def wrap(value):
    if isinstance(value, str): return Tag(8, value)
    if isinstance(value, dict): return Tag(10, {k: wrap(v) for k, v in value.items()})
    if isinstance(value, bool): return Tag(1, int(value))
    if isinstance(value, int): return Tag(3, value)
    if isinstance(value, float): return Tag(6, value)
    if isinstance(value, list):
        if value and all(isinstance(v, (int,float)) for v in value) and any(isinstance(v,float) for v in value):
            value = [float(v) for v in value]
        values = [wrap(v) for v in value]
        kind = values[0].kind if values else 0
        assert all(v.kind == kind for v in values), 'NBT lists must have one element type'
        return Tag(9, (kind, values))
    raise ValueError(type(value))
