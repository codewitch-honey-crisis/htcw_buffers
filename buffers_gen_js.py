#!/usr/bin/env python3
"""
buffers_gen_js.py - Parse wire structs from a C header and generate
                    JavaScript (ES module) read/write functions for each struct.

Usage: python buffers_gen_js.py [--fixed] [--big-endian] [--lengths] [--buffers] [--out <dir>] <header.h>

Options:
  --fixed           Use fixed-size serialization for strings
                    (transmit entire declared size). Without this flag,
                    strings are length-prefixed on the wire.
  --big-endian      Generate read/write functions using big-endian
                    serialization. Without this flag, little-endian is used.
  --lengths         Treat any size_t field that immediately precedes a fixed
                    array as the runtime element count for that array. The
                    count is serialized first (as uint32 on the wire), then
                    only that many array elements follow. The count field is
                    HIDDEN from the JS API: on write the count is taken from
                    the array property's .length; on read it is consumed but
                    discarded (the array's length carries it). Strings
                    (char[] / wchar_t[]) are unaffected. Mutually exclusive
                    with --fixed.
  --buffers         Also emit buffers.js (shared support module).
  --out <dir>       Directory for generated files (default: input directory).

Outputs:
  <stem>_buffers.js  - ES module of read/write/size free functions + enums
  buffers.js         - shared support module (string codecs, status)

Wire format is byte-for-byte identical to buffers_gen_c.py and
buffers_gen_cs.py for the same flags.

API (JS-idiomatic, plain objects - no classes):
  <name>Read(u8, offset = 0, outBytesRead = null) -> object | null
      Decodes a struct from a Uint8Array. Returns the decoded plain object,
      or null on failure (buffer too small, count exceeds capacity).
      If outBytesRead is an array, outBytesRead[0] receives the bytes read.
  <name>Write(obj, u8, offset = 0) -> number
      Encodes a struct into a Uint8Array. Returns the number of bytes
      written, or -1 on failure.
  <name>Size(obj) -> number            (variable mode only)
      Returns the actual wire byte size of a populated object.

  <NAME>_SIZE   - per-struct max wire size constant
  <STEM>_MAX_SIZE - largest struct wire size in the module

Naming (JS conventions, NOT .NET):
  - snake_case / SCREAM_CASE / camelCase -> camelCase for fields & functions
    * first word lowercased; subsequent words simple-capitalized
    * no special handling of short words (device_id -> deviceId, not deviceID)
  - enum objects are PascalCase value-namespaces with PascalCase members
    (example_input_type_t -> ExampleInputType.Touch)
  - _t suffix stripped from typedef names
  - 64-bit integer fields (uint64_t/int64_t) are BigInt; all smaller
    integers are plain numbers.
"""

"""
MIT License

Copyright (c) 2026 honey the codewitch

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Type mapping  (identical to the C source of truth)
# ---------------------------------------------------------------------------

SCALAR_TYPE_MAP = {
    'uint8_t':            'uint8_t',
    'uint16_t':           'uint16_t',
    'uint32_t':           'uint32_t',
    'uint64_t':           'uint64_t',
    'int8_t':             'int8_t',
    'int16_t':            'int16_t',
    'int32_t':            'int32_t',
    'int64_t':            'int64_t',
    'bool':               'uint8_t',
    'char':               'int8_t',
    'unsigned char':      'uint8_t',
    'short':              'int16_t',
    'unsigned short':     'uint16_t',
    'int':                'int32_t',
    'unsigned int':       'uint32_t',
    'long':               'int32_t',
    'unsigned long':      'uint32_t',
    'long long':          'int64_t',
    'unsigned long long': 'uint64_t',
    'float':              'float',
    'double':             'double',
    'wchar_t':            'int16_t',
    'size_t':             'uint32_t',
}

WIRE_TYPE_SIZES = {
    'uint8_t':  1, 'uint16_t': 2, 'uint32_t': 4, 'uint64_t': 8,
    'int8_t':   1, 'int16_t':  2, 'int32_t':  4, 'int64_t':  8,
    'float':    4, 'double':   8,
}

WIRE_SCALAR_TYPES = set(WIRE_TYPE_SIZES.keys())

# Wire types represented as BigInt in JS (DataView getBig*64).
BIGINT_WIRE_TYPES = {'uint64_t', 'int64_t'}

# DataView method fragment for each multi-byte wire type.
# Single-byte types are handled directly via u8[] indexing.
DV_METHOD = {
    'uint16_t': 'Uint16', 'int16_t': 'Int16',
    'uint32_t': 'Uint32', 'int32_t': 'Int32',
    'uint64_t': 'BigUint64', 'int64_t': 'BigInt64',
    'float': 'Float32', 'double': 'Float64',
}


def enum_wire_type(min_val: int, max_val: int) -> str:
    if min_val >= 0:
        if max_val <= 0xFF:           return 'uint8_t'
        elif max_val <= 0xFFFF:       return 'uint16_t'
        elif max_val <= 0xFFFFFFFF:   return 'uint32_t'
        else:                         return 'uint64_t'
    else:
        if   min_val >= -128         and max_val <= 127:         return 'int8_t'
        elif min_val >= -32768       and max_val <= 32767:       return 'int16_t'
        elif min_val >= -2147483648  and max_val <= 2147483647:  return 'int32_t'
        else:                                                    return 'int64_t'


def length_prefix_type(array_len: int) -> str:
    if array_len < 256:
        return 'uint8_t'
    elif array_len < 65536:
        return 'uint16_t'
    elif array_len <= 0xFFFFFFFF:
        return 'uint32_t'
    else:
        error(f"Array length {array_len} exceeds UINT32_MAX")


def length_prefix_size(array_len: int) -> int:
    return WIRE_TYPE_SIZES[length_prefix_type(array_len)]


# ---------------------------------------------------------------------------
# JS naming helpers
# ---------------------------------------------------------------------------

def split_words(name: str) -> list:
    """Split a C identifier into a list of lowercase word strings.
    Identical word-splitting to the C# generator (handles snake_case,
    SCREAM_CASE, camelCase, PascalCase)."""
    name = name.strip('_')
    name = re.sub(r'_+', '_', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    parts = [p for p in name.split('_') if p]
    return [p.lower() for p in parts]


def _cap(word: str) -> str:
    """Simple capitalization: first letter up, rest down. No acronym rule."""
    if not word:
        return word
    return word[0].upper() + word[1:]


def to_camel(c_name: str) -> str:
    """Convert a C identifier to JS camelCase (lowercase-leading).
    First word lowercased; subsequent words simple-capitalized.
    e.g. device_id -> deviceId, ip_address -> ipAddress, id -> id."""
    if c_name.endswith('_t'):
        c_name = c_name[:-2]
    words = split_words(c_name)
    if not words:
        return c_name
    return words[0] + ''.join(_cap(w) for w in words[1:])


def to_pascal(c_name: str) -> str:
    """Convert a C identifier to JS PascalCase (used for enum value-namespaces
    and their members). e.g. example_input_type_t -> ExampleInputType,
    INPUT_TOUCH -> Touch."""
    if c_name.endswith('_t'):
        c_name = c_name[:-2]
    words = split_words(c_name)
    if not words:
        return c_name
    return ''.join(_cap(w) for w in words)


def define_name(struct_name: str) -> str:
    """SCREAMING_SNAKE constant name for a struct's wire size define."""
    name = struct_name
    if name.endswith('_t'):
        name = name[:-2]
    name = re.sub(r'[^A-Za-z0-9]', '_', name).upper()
    return f"{name}_SIZE"


def header_stem_to_define_prefix(header_path: str) -> str:
    stem = os.path.splitext(os.path.basename(header_path))[0]
    ident = re.sub(r'[^A-Za-z0-9]', '_', stem).upper()
    if ident and ident[0].isdigit():
        ident = '_' + ident
    return ident


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def strip_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    return text


def strip_preprocessor(text: str) -> str:
    text = re.sub(r'^\s*#[^\n]*(?:\\\n[^\n]*)*', '', text, flags=re.MULTILINE)
    return text


# ---------------------------------------------------------------------------
# Enum parsing  (mirrors C# generator: keeps member names + values)
# ---------------------------------------------------------------------------

ENUM_TYPEDEF_RE = re.compile(
    r'\btypedef\s+enum\s*(?:[A-Za-z_][A-Za-z0-9_]*)?\s*'
    r'\{(?P<body>[^{}]*)\}\s*(?P<n>[A-Za-z_][A-Za-z0-9_]*)\s*;',
    re.DOTALL,
)
ENUM_RE = re.compile(
    r'\benum\s+(?P<n>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<body>[^{}]*)\}\s*;',
    re.DOTALL,
)
_INT_LITERAL_RE = re.compile(r'^-?\s*(?:0[xX][0-9A-Fa-f]+|0[0-7]*|[1-9][0-9]*|0)$')


def parse_enums(text: str) -> dict:
    """Returns dict: c_name -> {wire_type, members: [(js_member_name, int_value)]}"""
    enums = {}
    found = []
    for m in ENUM_TYPEDEF_RE.finditer(text):
        found.append((m.group('n'), m.group('body')))
    typedef_names = {n for n, _ in found}
    for m in ENUM_RE.finditer(text):
        if m.group('n') not in typedef_names:
            found.append((m.group('n'), m.group('body')))
    for c_name, body in found:
        if c_name in enums:
            error(f"Duplicate enum name: '{c_name}'")
        members = []
        current = 0
        for entry in body.split(','):
            entry = entry.strip()
            if not entry:
                continue
            if '=' in entry:
                lhs, rhs = entry.split('=', 1)
                lhs = lhs.strip()
                rhs = rhs.strip()
                if not _INT_LITERAL_RE.fullmatch(rhs):
                    error(f"Enum '{c_name}': non-literal value '{rhs}' not supported")
                current = int(rhs, 0)
                member_c_name = lhs
            else:
                member_c_name = entry.strip()
            members.append((to_pascal(member_c_name), current))
            current += 1
        values = [v for _, v in members]
        if values:
            wire_type = enum_wire_type(min(values), max(values))
            enums[c_name] = {'wire_type': wire_type, 'members': members}
    return enums


# ---------------------------------------------------------------------------
# Field parsing
# ---------------------------------------------------------------------------

FIELD_RE = re.compile(
    r'^\s*'
    r'(?P<type>[A-Za-z_][A-Za-z0-9_ ]*?)'
    r'\s+'
    r'(?P<n>[A-Za-z_][A-Za-z0-9_]*)'
    r'(?:\s*\[\s*(?P<len>[^\]]+)\s*\])?'
    r'\s*;',
    re.MULTILINE,
)


def resolve_type(type_str, struct_name, field_name, all_struct_names, known_enums):
    key = ' '.join(type_str.lower().split())
    if key in SCALAR_TYPE_MAP:
        return SCALAR_TYPE_MAP[key]
    if type_str in known_enums:
        return known_enums[type_str]['wire_type']
    if type_str in all_struct_names:
        return type_str
    error(f"Struct '{struct_name}', field '{field_name}': unsupported or unknown type '{type_str}'")


def parse_field(raw, struct_name, all_struct_names, known_enums):
    raw = raw.strip()
    if not raw:
        return None
    if '*' in raw:
        error(f"Struct '{struct_name}': pointer field not allowed: '{raw}'")
    m = FIELD_RE.match(raw + (';' if not raw.endswith(';') else ''))
    if not m:
        error(f"Struct '{struct_name}': cannot parse field: '{raw}'")
    type_str = ' '.join(m.group('type').split())
    name = m.group('n')
    len_str = m.group('len')
    array_len = None
    if len_str is not None:
        len_str = len_str.strip()
        if not re.fullmatch(r'\d+', len_str):
            error(f"Struct '{struct_name}', field '{name}': array length must be a literal integer, got '{len_str}'")
        array_len = int(len_str)
    wire_type = resolve_type(type_str, struct_name, name, all_struct_names, known_enums)
    is_enum = type_str in known_enums
    enum_c_name = type_str if is_enum else None
    return {
        "c_name": name,
        "js_name": to_camel(name),
        "type": type_str,
        "wire_type": wire_type,
        "array_len": array_len,
        "is_enum": is_enum,
        "enum_c_name": enum_c_name,
    }


def parse_struct_body(body, struct_name, all_struct_names, known_enums):
    fields = []
    for raw in body.split(';'):
        raw = raw.strip()
        if not raw:
            continue
        if re.search(r'\b(struct|union)\b', raw):
            error(f"Struct '{struct_name}': nested struct/union not allowed: '{raw}'")
        field = parse_field(raw + ';', struct_name, all_struct_names, known_enums)
        if field:
            fields.append(field)
    return fields


def apply_lengths_pairing(structs: dict, struct_name: str) -> None:
    """Pair `size_t name; T arr[N];` so the count drives the runtime element
    count. The count field is hidden from the JS API; on write the count is
    taken from the array property's .length, on read it is consumed but
    discarded. Strings keep their own length-prefix behavior. The size_t must
    immediately precede the array."""
    fields = structs[struct_name]['fields']
    for i in range(len(fields) - 1):
        cur = fields[i]
        nxt = fields[i + 1]
        if cur['array_len'] is not None:
            continue
        if cur['is_enum']:
            continue
        if cur['type'] != 'size_t':
            continue
        if nxt['array_len'] is None:
            continue
        if nxt['type'] in ('char', 'wchar_t'):
            continue
        nxt['length_field'] = cur['c_name']
        cur['is_length_for'] = nxt['c_name']


# ---------------------------------------------------------------------------
# Top-level struct extraction
# ---------------------------------------------------------------------------

STRUCT_RE = re.compile(
    r'\bstruct\s+(?P<n>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<body>[^{}]*)\}\s*;',
    re.DOTALL,
)
TYPEDEF_RE = re.compile(
    r'\btypedef\s+struct\s*(?:[A-Za-z_][A-Za-z0-9_]*)?\s*\{(?P<body>[^{}]*)\}\s*(?P<n>[A-Za-z_][A-Za-z0-9_]*)\s*;',
    re.DOTALL,
)


def parse_header(text: str, lengths_mode: bool = False) -> tuple:
    text = strip_comments(text)
    text = strip_preprocessor(text)

    known_enums = parse_enums(text)

    found = []
    for m in TYPEDEF_RE.finditer(text):
        found.append((m.start(), m.group('n'), m.group('body')))
    typedef_spans = [(m.start(), m.end()) for m in TYPEDEF_RE.finditer(text)]
    for m in STRUCT_RE.finditer(text):
        if not any(ts <= m.start() and m.end() <= te for ts, te in typedef_spans):
            found.append((m.start(), m.group('n'), m.group('body')))
    found.sort(key=lambda x: x[0])

    all_struct_names = {name for _, name, _ in found}
    structs = {}
    for _, name, body in found:
        if name in structs:
            error(f"Duplicate struct name: '{name}'")
        fields = parse_struct_body(body, name, all_struct_names, known_enums)
        seen = set()
        for f in fields:
            if f['c_name'] in seen:
                error(f"Struct '{name}': duplicate field name '{f['c_name']}'")
            seen.add(f['c_name'])
        structs[name] = {"fields": fields, "js_name": to_camel(name)}

    if lengths_mode:
        for name in structs:
            apply_lengths_pairing(structs, name)

    return structs, known_enums


# ---------------------------------------------------------------------------
# Wire size computation  (identical semantics to C / C#)
# ---------------------------------------------------------------------------

def _field_is_string(f: dict) -> bool:
    return f['array_len'] is not None and f['type'] in ('char', 'wchar_t')


def wire_size_of(wire_type, array_len, structs, _visiting=frozenset(),
                 fixed_mode=True, is_string=False) -> int:
    if wire_type in WIRE_TYPE_SIZES:
        element_size = WIRE_TYPE_SIZES[wire_type]
    elif wire_type in structs:
        if wire_type in _visiting:
            error(f"Circular struct reference detected involving '{wire_type}'")
        element_size = struct_wire_size(wire_type, structs, _visiting | {wire_type}, fixed_mode=fixed_mode)
    else:
        error(f"Cannot determine wire size for type '{wire_type}'")
    count = array_len if array_len is not None else 1
    size = element_size * count
    if not fixed_mode and array_len is not None and is_string:
        size += length_prefix_size(array_len)
    return size


def struct_wire_size(struct_name, structs, _visiting=frozenset(), fixed_mode=True) -> int:
    return sum(
        wire_size_of(f['wire_type'], f['array_len'], structs, _visiting,
                     fixed_mode=fixed_mode, is_string=_field_is_string(f))
        for f in structs[struct_name]['fields']
    )


def compute_max_wire_size(structs, fixed_mode=True) -> int:
    if not structs:
        return 0
    return max(struct_wire_size(name, structs, fixed_mode=fixed_mode) for name in structs)


# ---------------------------------------------------------------------------
# Function-name helpers
# ---------------------------------------------------------------------------

def read_fn_name(struct_name):
    return f"{to_camel(struct_name)}Read"


def write_fn_name(struct_name):
    return f"{to_camel(struct_name)}Write"


def size_fn_name(struct_name):
    return f"{to_camel(struct_name)}Size"


# ---------------------------------------------------------------------------
# DataView read/write expression helpers
# ---------------------------------------------------------------------------

def dv_read(wire_type: str, off_expr: str, big_endian: bool) -> str:
    """Return a JS expression that reads one scalar of wire_type at off_expr
    from the local DataView `dv`."""
    if wire_type == 'uint8_t':
        return f"u8[{off_expr}]"
    if wire_type == 'int8_t':
        # sign-extend a byte
        return f"(u8[{off_expr}] << 24 >> 24)"
    meth = DV_METHOD[wire_type]
    le = 'true' if not big_endian else 'false'
    return f"dv.get{meth}({off_expr}, {le})"


def dv_write(wire_type: str, off_expr: str, val_expr: str, big_endian: bool) -> str:
    if wire_type == 'uint8_t':
        return f"u8[{off_expr}] = {val_expr} & 0xFF;"
    if wire_type == 'int8_t':
        return f"u8[{off_expr}] = {val_expr} & 0xFF;"
    meth = DV_METHOD[wire_type]
    le = 'true' if not big_endian else 'false'
    return f"dv.set{meth}({off_expr}, {val_expr}, {le});"


def js_zero_literal(wire_type: str) -> str:
    return "0n" if wire_type in BIGINT_WIRE_TYPES else "0"


# ---------------------------------------------------------------------------
# Read-function body generation
# ---------------------------------------------------------------------------

def gen_read_body(struct_name, info, structs, enums, big_endian, fixed_mode):
    js_name = info['js_name']
    fields = info['fields']
    all_struct_names = set(structs.keys())
    L = []
    ind = "  "

    if not fields:
        L.append(f"{ind}const result = {{}};")
        L.append(f"{ind}if (outBytesRead) outBytesRead[0] = 0;")
        L.append(f"{ind}return result;")
        return L

    L.append(f"{ind}const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);")
    L.append(f"{ind}const result = {{}};")
    L.append(f"{ind}let off = offset;")

    for f in fields:
        js = f['js_name']
        wt = f['wire_type']
        sz = WIRE_TYPE_SIZES.get(wt, 0)
        arr = f['array_len']
        is_struct = wt in all_struct_names

        # Hidden count field: consumed by its paired array's block.
        if f.get('is_length_for') is not None:
            continue

        # --- length-paired array (--lengths) ---
        if arr is not None and f.get('length_field') is not None:
            L.append(f"{ind}{{ // length-paired array: {js}")
            L.append(f"{ind}  if (off + 4 > u8.byteLength) return null;")
            L.append(f"{ind}  const n = {dv_read('uint32_t', 'off', big_endian)};")
            L.append(f"{ind}  off += 4;")
            L.append(f"{ind}  if (n < 0 || n > {arr}) return null;")
            if is_struct:
                nested_read = read_fn_name(wt)
                L.append(f"{ind}  const list = new Array(n);")
                L.append(f"{ind}  const nb = [0];")
                L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
                L.append(f"{ind}    const item = {nested_read}(u8, off, nb);")
                L.append(f"{ind}    if (item === null) return null;")
                L.append(f"{ind}    list[i] = item;")
                L.append(f"{ind}    off += nb[0];")
                L.append(f"{ind}  }}")
                L.append(f"{ind}  result.{js} = list;")
            else:
                arr_ctor = "[]"
                L.append(f"{ind}  const a = new Array(n);")
                L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
                L.append(f"{ind}    if (off + {sz} > u8.byteLength) return null;")
                read_expr = dv_read(wt, 'off', big_endian)
                if f['type'] == 'bool':
                    L.append(f"{ind}    a[i] = ({read_expr}) !== 0;")
                else:
                    L.append(f"{ind}    a[i] = {read_expr};")
                L.append(f"{ind}    off += {sz};")
                L.append(f"{ind}  }}")
                L.append(f"{ind}  result.{js} = a;")
            L.append(f"{ind}}}")
            continue

        # --- char[] string (UTF-8) ---
        if arr is not None and f['type'] == 'char':
            if fixed_mode:
                L.append(f"{ind}if (off + {arr} > u8.byteLength) return null;")
                L.append(f"{ind}result.{js} = decodeUtf8(u8, off, {arr});")
                L.append(f"{ind}off += {arr};")
            else:
                lp_wt = length_prefix_type(arr)
                lp_sz = WIRE_TYPE_SIZES[lp_wt]
                L.append(f"{ind}{{ // string {js}")
                L.append(f"{ind}  if (off + {lp_sz} > u8.byteLength) return null;")
                L.append(f"{ind}  const len = {dv_read(lp_wt, 'off', big_endian)};")
                L.append(f"{ind}  off += {lp_sz};")
                L.append(f"{ind}  if (len > {arr} || off + len > u8.byteLength) return null;")
                L.append(f"{ind}  result.{js} = decodeUtf8(u8, off, len);")
                L.append(f"{ind}  off += len;")
                L.append(f"{ind}}}")
            continue

        # --- wchar_t[] string (UTF-16) ---
        if arr is not None and f['type'] == 'wchar_t':
            be = 'true' if big_endian else 'false'
            if fixed_mode:
                byte_count = arr * 2
                L.append(f"{ind}if (off + {byte_count} > u8.byteLength) return null;")
                L.append(f"{ind}result.{js} = decodeUtf16(u8, off, {byte_count}, {be});")
                L.append(f"{ind}off += {byte_count};")
            else:
                lp_wt = length_prefix_type(arr)
                lp_sz = WIRE_TYPE_SIZES[lp_wt]
                L.append(f"{ind}{{ // wstring {js}")
                L.append(f"{ind}  if (off + {lp_sz} > u8.byteLength) return null;")
                L.append(f"{ind}  const len = {dv_read(lp_wt, 'off', big_endian)};")
                L.append(f"{ind}  off += {lp_sz};")
                L.append(f"{ind}  const byteLen = len * 2;")
                L.append(f"{ind}  if (len > {arr} || off + byteLen > u8.byteLength) return null;")
                L.append(f"{ind}  result.{js} = decodeUtf16(u8, off, byteLen, {be});")
                L.append(f"{ind}  off += byteLen;")
                L.append(f"{ind}}}")
            continue

        # --- struct array (full declared length, no prefix) ---
        if arr is not None and is_struct:
            nested_read = read_fn_name(wt)
            L.append(f"{ind}{{ // struct array {js}")
            L.append(f"{ind}  const list = new Array({arr});")
            L.append(f"{ind}  const nb = [0];")
            L.append(f"{ind}  for (let i = 0; i < {arr}; i++) {{")
            L.append(f"{ind}    const item = {nested_read}(u8, off, nb);")
            L.append(f"{ind}    if (item === null) return null;")
            L.append(f"{ind}    list[i] = item;")
            L.append(f"{ind}    off += nb[0];")
            L.append(f"{ind}  }}")
            L.append(f"{ind}  result.{js} = list;")
            L.append(f"{ind}}}")
            continue

        # --- scalar/enum array (full declared length, no prefix) ---
        if arr is not None:
            L.append(f"{ind}{{ // array {js}")
            L.append(f"{ind}  const a = new Array({arr});")
            L.append(f"{ind}  for (let i = 0; i < {arr}; i++) {{")
            L.append(f"{ind}    if (off + {sz} > u8.byteLength) return null;")
            read_expr = dv_read(wt, 'off', big_endian)
            if f['type'] == 'bool':
                L.append(f"{ind}    a[i] = ({read_expr}) !== 0;")
            else:
                L.append(f"{ind}    a[i] = {read_expr};")
            L.append(f"{ind}    off += {sz};")
            L.append(f"{ind}  }}")
            L.append(f"{ind}  result.{js} = a;")
            L.append(f"{ind}}}")
            continue

        # --- single nested struct ---
        if is_struct:
            nested_read = read_fn_name(wt)
            L.append(f"{ind}{{ // nested {js}")
            L.append(f"{ind}  const nb = [0];")
            L.append(f"{ind}  const item = {nested_read}(u8, off, nb);")
            L.append(f"{ind}  if (item === null) return null;")
            L.append(f"{ind}  result.{js} = item;")
            L.append(f"{ind}  off += nb[0];")
            L.append(f"{ind}}}")
            continue

        # --- single scalar / enum / bool ---
        L.append(f"{ind}if (off + {sz} > u8.byteLength) return null;")
        read_expr = dv_read(wt, 'off', big_endian)
        if f['type'] == 'bool':
            L.append(f"{ind}result.{js} = ({read_expr}) !== 0;")
        else:
            L.append(f"{ind}result.{js} = {read_expr};")
        L.append(f"{ind}off += {sz};")

    L.append(f"{ind}if (outBytesRead) outBytesRead[0] = off - offset;")
    L.append(f"{ind}return result;")
    return L


# ---------------------------------------------------------------------------
# Write-function body generation
# ---------------------------------------------------------------------------

def gen_write_body(struct_name, info, structs, enums, big_endian, fixed_mode):
    js_name = info['js_name']
    fields = info['fields']
    all_struct_names = set(structs.keys())
    L = []
    ind = "  "

    if not fields:
        L.append(f"{ind}return 0;")
        return L

    L.append(f"{ind}const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);")
    L.append(f"{ind}let off = offset;")

    for f in fields:
        js = f['js_name']
        wt = f['wire_type']
        sz = WIRE_TYPE_SIZES.get(wt, 0)
        arr = f['array_len']
        is_struct = wt in all_struct_names

        if f.get('is_length_for') is not None:
            continue

        # --- length-paired array (--lengths): count from array .length ---
        if arr is not None and f.get('length_field') is not None:
            L.append(f"{ind}{{ // length-paired array: {js}")
            L.append(f"{ind}  const a = obj.{js};")
            L.append(f"{ind}  const n = (a == null) ? 0 : a.length;")
            L.append(f"{ind}  if (n > {arr}) return -1;")
            L.append(f"{ind}  if (off + 4 > u8.byteLength) return -1;")
            L.append(f"{ind}  {dv_write('uint32_t', 'off', 'n', big_endian)}")
            L.append(f"{ind}  off += 4;")
            if is_struct:
                nested_write = write_fn_name(wt)
                L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
                L.append(f"{ind}    if (a[i] == null) return -1;")
                L.append(f"{ind}    const w = {nested_write}(a[i], u8, off);")
                L.append(f"{ind}    if (w < 0) return -1;")
                L.append(f"{ind}    off += w;")
                L.append(f"{ind}  }}")
            else:
                L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
                L.append(f"{ind}    if (off + {sz} > u8.byteLength) return -1;")
                val = _write_scalar_value(f, "a[i]")
                L.append(f"{ind}    {dv_write(wt, 'off', val, big_endian)}")
                L.append(f"{ind}    off += {sz};")
                L.append(f"{ind}  }}")
            L.append(f"{ind}}}")
            continue

        # --- char[] string (UTF-8) ---
        if arr is not None and f['type'] == 'char':
            if fixed_mode:
                L.append(f"{ind}if (off + {arr} > u8.byteLength) return -1;")
                L.append(f"{ind}encodeUtf8Fixed(obj.{js}, u8, off, {arr});")
                L.append(f"{ind}off += {arr};")
            else:
                lp_wt = length_prefix_type(arr)
                lp_sz = WIRE_TYPE_SIZES[lp_wt]
                L.append(f"{ind}{{ // string {js}")
                L.append(f"{ind}  const enc = encodeUtf8Bounded(obj.{js}, {arr});")
                L.append(f"{ind}  if (off + {lp_sz} + enc.length > u8.byteLength) return -1;")
                L.append(f"{ind}  {dv_write(lp_wt, 'off', 'enc.length', big_endian)}")
                L.append(f"{ind}  off += {lp_sz};")
                L.append(f"{ind}  u8.set(enc, off);")
                L.append(f"{ind}  off += enc.length;")
                L.append(f"{ind}}}")
            continue

        # --- wchar_t[] string (UTF-16) ---
        if arr is not None and f['type'] == 'wchar_t':
            be = 'true' if big_endian else 'false'
            if fixed_mode:
                byte_count = arr * 2
                L.append(f"{ind}if (off + {byte_count} > u8.byteLength) return -1;")
                L.append(f"{ind}encodeUtf16Fixed(obj.{js}, u8, off, {arr}, {be});")
                L.append(f"{ind}off += {byte_count};")
            else:
                lp_wt = length_prefix_type(arr)
                lp_sz = WIRE_TYPE_SIZES[lp_wt]
                L.append(f"{ind}{{ // wstring {js}")
                L.append(f"{ind}  const units = utf16Units(obj.{js}, {arr});")
                L.append(f"{ind}  const byteLen = units * 2;")
                L.append(f"{ind}  if (off + {lp_sz} + byteLen > u8.byteLength) return -1;")
                L.append(f"{ind}  {dv_write(lp_wt, 'off', 'units', big_endian)}")
                L.append(f"{ind}  off += {lp_sz};")
                L.append(f"{ind}  encodeUtf16Into(obj.{js}, units, u8, off, {be});")
                L.append(f"{ind}  off += byteLen;")
                L.append(f"{ind}}}")
            continue

        # --- struct array (full declared length, zero-fill missing) ---
        if arr is not None and is_struct:
            nested_write = write_fn_name(wt)
            nested_sz = struct_wire_size(wt, structs, fixed_mode=fixed_mode)
            L.append(f"{ind}{{ // struct array {js}")
            L.append(f"{ind}  const a = obj.{js};")
            L.append(f"{ind}  const n = (a == null) ? 0 : Math.min(a.length, {arr});")
            L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
            L.append(f"{ind}    if (a[i] == null) return -1;")
            L.append(f"{ind}    const w = {nested_write}(a[i], u8, off);")
            L.append(f"{ind}    if (w < 0) return -1;")
            L.append(f"{ind}    off += w;")
            L.append(f"{ind}  }}")
            # zero-fill remaining declared slots
            L.append(f"{ind}  for (let i = n; i < {arr}; i++) {{")
            L.append(f"{ind}    if (off + {nested_sz} > u8.byteLength) return -1;")
            L.append(f"{ind}    u8.fill(0, off, off + {nested_sz});")
            L.append(f"{ind}    off += {nested_sz};")
            L.append(f"{ind}  }}")
            L.append(f"{ind}}}")
            continue

        # --- scalar/enum array (full declared length, zero-fill missing) ---
        if arr is not None:
            L.append(f"{ind}{{ // array {js}")
            L.append(f"{ind}  const a = obj.{js};")
            L.append(f"{ind}  const n = (a == null) ? 0 : Math.min(a.length, {arr});")
            L.append(f"{ind}  for (let i = 0; i < n; i++) {{")
            L.append(f"{ind}    if (off + {sz} > u8.byteLength) return -1;")
            val = _write_scalar_value(f, "a[i]")
            L.append(f"{ind}    {dv_write(wt, 'off', val, big_endian)}")
            L.append(f"{ind}    off += {sz};")
            L.append(f"{ind}  }}")
            L.append(f"{ind}  for (let i = n; i < {arr}; i++) {{")
            L.append(f"{ind}    if (off + {sz} > u8.byteLength) return -1;")
            L.append(f"{ind}    {dv_write(wt, 'off', js_zero_literal(wt), big_endian)}")
            L.append(f"{ind}    off += {sz};")
            L.append(f"{ind}  }}")
            L.append(f"{ind}}}")
            continue

        # --- single nested struct ---
        if is_struct:
            nested_write = write_fn_name(wt)
            L.append(f"{ind}{{ // nested {js}")
            L.append(f"{ind}  if (obj.{js} == null) return -1;")
            L.append(f"{ind}  const w = {nested_write}(obj.{js}, u8, off);")
            L.append(f"{ind}  if (w < 0) return -1;")
            L.append(f"{ind}  off += w;")
            L.append(f"{ind}}}")
            continue

        # --- single scalar / enum / bool ---
        L.append(f"{ind}if (off + {sz} > u8.byteLength) return -1;")
        val = _write_scalar_value(f, f"obj.{js}")
        L.append(f"{ind}{dv_write(wt, 'off', val, big_endian)}")
        L.append(f"{ind}off += {sz};")

    L.append(f"{ind}return off - offset;")
    return L


def _write_scalar_value(f: dict, expr: str) -> str:
    """Coerce a JS field value expression to the wire scalar before writing."""
    if f['type'] == 'bool':
        return f"({expr} ? 1 : 0)"
    if f['wire_type'] in BIGINT_WIRE_TYPES:
        # accept number or bigint, normalize to BigInt for DataView setBig*
        return f"BigInt({expr})"
    return expr


# ---------------------------------------------------------------------------
# Size-function body generation (variable mode only)
# ---------------------------------------------------------------------------

def gen_size_body(struct_name, info, structs, enums):
    fields = info['fields']
    all_struct_names = set(structs.keys())
    L = []
    ind = "  "
    if not fields:
        L.append(f"{ind}return 0;")
        return L
    L.append(f"{ind}let size = 0;")
    for f in fields:
        js = f['js_name']
        wt = f['wire_type']
        sz = WIRE_TYPE_SIZES.get(wt, 0)
        arr = f['array_len']
        is_struct = wt in all_struct_names

        if f.get('is_length_for') is not None:
            continue

        if arr is not None and f.get('length_field') is not None:
            if is_struct:
                nested_size = size_fn_name(wt)
                L.append(f"{ind}{{ const a = obj.{js}; size += 4;")
                L.append(f"{ind}  if (a) for (let i = 0; i < Math.min(a.length, {arr}); i++) size += {nested_size}(a[i]); }}")
            else:
                L.append(f"{ind}size += 4 + (obj.{js} ? Math.min(obj.{js}.length, {arr}) : 0) * {sz};")
            continue

        if arr is not None and f['type'] == 'char':
            lp_sz = length_prefix_size(arr)
            L.append(f"{ind}size += {lp_sz} + utf8Bounded(obj.{js}, {arr});")
            continue

        if arr is not None and f['type'] == 'wchar_t':
            lp_sz = length_prefix_size(arr)
            L.append(f"{ind}size += {lp_sz} + utf16Units(obj.{js}, {arr}) * 2;")
            continue

        if arr is not None and is_struct:
            nested_size = size_fn_name(wt)
            L.append(f"{ind}{{ const a = obj.{js};")
            L.append(f"{ind}  for (let i = 0; i < {arr}; i++) size += {nested_size}(a ? a[i] : undefined); }}")
            continue

        if arr is not None:
            L.append(f"{ind}size += {arr} * {sz};")
            continue

        if is_struct:
            nested_size = size_fn_name(wt)
            L.append(f"{ind}size += {nested_size}(obj.{js});")
            continue

        L.append(f"{ind}size += {sz};")
    L.append(f"{ind}return size;")
    return L


# ---------------------------------------------------------------------------
# Module assembly
# ---------------------------------------------------------------------------

def gen_enum_js(c_name, info):
    pascal = to_pascal(c_name)
    members = info['members']
    parts = ", ".join(f"{name}: {val}" for name, val in members)
    return f"export const {pascal} = Object.freeze({{ {parts} }});"


def generate_js_module(header_path, structs, enums, fixed_mode, big_endian):
    stem = os.path.splitext(os.path.basename(header_path))[0]
    define_prefix = header_stem_to_define_prefix(header_path)
    max_size = compute_max_wire_size(structs, fixed_mode=fixed_mode)

    L = []
    L.append("// Auto-generated by buffers_gen_js.py - do not edit manually.")
    L.append(f"// Wire format: {'big' if big_endian else 'little'}-endian, "
             f"{'fixed' if fixed_mode else 'variable'}-length strings.")

    # imports from the shared runtime
    imports = ["decodeUtf8", "decodeUtf16", "encodeUtf8Fixed", "encodeUtf16Fixed"]
    if not fixed_mode:
        imports += ["encodeUtf8Bounded", "utf8Bounded", "utf16Units", "encodeUtf16Into"]
    L.append(f"import {{ {', '.join(imports)} }} from './buffers.js';")
    L.append("")

    # size constants
    L.append(f"export const {define_prefix}_MAX_SIZE = {max_size};")
    for struct_name in structs:
        size = struct_wire_size(struct_name, structs, fixed_mode=fixed_mode)
        L.append(f"export const {define_name(struct_name)} = {size};")
    L.append("")

    # enums
    for c_name, info in enums.items():
        L.append(gen_enum_js(c_name, info))
    if enums:
        L.append("")

    # read/write/size functions
    for struct_name, info in structs.items():
        rfn = read_fn_name(struct_name)
        wfn = write_fn_name(struct_name)
        L.append(f"export function {rfn}(u8, offset = 0, outBytesRead = null) {{")
        L.extend(gen_read_body(struct_name, info, structs, enums, big_endian, fixed_mode))
        L.append("}")
        L.append("")
        L.append(f"export function {wfn}(obj, u8, offset = 0) {{")
        L.extend(gen_write_body(struct_name, info, structs, enums, big_endian, fixed_mode))
        L.append("}")
        L.append("")
        if not fixed_mode:
            sfn = size_fn_name(struct_name)
            L.append(f"export function {sfn}(obj) {{")
            L.extend(gen_size_body(struct_name, info, structs, enums))
            L.append("}")
            L.append("")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# Shared runtime module (buffers.js)
# ---------------------------------------------------------------------------

BUFFERS_JS_CONTENT = r"""// Auto-generated by buffers_gen_js.py - do not edit manually.
// Shared support module for wire buffer reading/writing.

export const BUFFERS_SUCCESS = 0;
export const BUFFERS_EOF = -1;
export const BUFFERS_ERROR_EOF = -2;

const _utf8Decoder = new TextDecoder('utf-8');
const _utf8Encoder = new TextEncoder();

// --- UTF-8 (char[]) ---------------------------------------------------------

// Decode up to `max` bytes from u8 at off, stopping at the first NUL byte.
export function decodeUtf8(u8, off, max) {
  let end = off + max;
  for (let i = off; i < off + max; i++) {
    if (u8[i] === 0) { end = i; break; }
  }
  return _utf8Decoder.decode(u8.subarray(off, end));
}

// Encode a string as UTF-8, truncated to at most `cap` bytes on a valid
// code-point boundary (never splits a multibyte sequence). Returns a Uint8Array.
export function encodeUtf8Bounded(value, cap) {
  if (value == null || value.length === 0) return new Uint8Array(0);
  const full = _utf8Encoder.encode(value);
  if (full.length <= cap) return full;
  // Truncate without splitting: back up off any UTF-8 continuation bytes.
  let n = cap;
  while (n > 0 && (full[n] & 0xC0) === 0x80) n--;
  return full.subarray(0, n);
}

// Byte length of encodeUtf8Bounded(value, cap) without allocating the slice.
export function utf8Bounded(value, cap) {
  return encodeUtf8Bounded(value, cap).length;
}

// Encode a string as UTF-8 into a fixed `cap`-byte field at off, zero-padded.
// Truncates on a valid code-point boundary if necessary.
export function encodeUtf8Fixed(value, u8, off, cap) {
  u8.fill(0, off, off + cap);
  if (value == null || value.length === 0) return;
  const enc = encodeUtf8Bounded(value, cap);
  u8.set(enc, off);
}

// --- UTF-16 (wchar_t[]) -----------------------------------------------------

// Number of UTF-16 code units to emit for `value`, capped at `cap`, never
// splitting a surrogate pair at the boundary.
export function utf16Units(value, cap) {
  if (value == null || value.length === 0) return 0;
  let n = Math.min(value.length, cap);
  // If we'd cut between a high and low surrogate, drop the lone high surrogate.
  if (n > 0 && n < value.length) {
    const c = value.charCodeAt(n - 1);
    if (c >= 0xD800 && c <= 0xDBFF) n--;
  }
  return n;
}

// Decode `byteLen` bytes of UTF-16 (LE unless be) at off, stopping at the
// first NUL code unit (0x0000).
export function decodeUtf16(u8, off, byteLen, be) {
  const units = byteLen >> 1;
  let count = units;
  for (let i = 0; i < units; i++) {
    const lo = u8[off + i * 2];
    const hi = u8[off + i * 2 + 1];
    const cu = be ? ((lo << 8) | hi) : ((hi << 8) | lo);
    if (cu === 0) { count = i; break; }
  }
  let s = '';
  for (let i = 0; i < count; i++) {
    const lo = u8[off + i * 2];
    const hi = u8[off + i * 2 + 1];
    const cu = be ? ((lo << 8) | hi) : ((hi << 8) | lo);
    s += String.fromCharCode(cu);
  }
  return s;
}

// Write `units` UTF-16 code units of `value` into u8 at off (LE unless be).
export function encodeUtf16Into(value, units, u8, off, be) {
  for (let i = 0; i < units; i++) {
    const cu = value.charCodeAt(i);
    const hi = (cu >> 8) & 0xFF;
    const lo = cu & 0xFF;
    if (be) { u8[off + i * 2] = hi; u8[off + i * 2 + 1] = lo; }
    else    { u8[off + i * 2] = lo; u8[off + i * 2 + 1] = hi; }
  }
}

// Encode a string as UTF-16 into a fixed `cap`-unit field at off (cap*2 bytes),
// zero-padded, never splitting a surrogate pair.
export function encodeUtf16Fixed(value, u8, off, cap, be) {
  const byteCap = cap * 2;
  u8.fill(0, off, off + byteCap);
  if (value == null || value.length === 0) return;
  const units = utf16Units(value, cap);
  encodeUtf16Into(value, units, u8, off, be);
}
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    gen_buffers = False
    out_dir = ""
    fixed_mode = False
    big_endian = False
    lengths_mode = False
    while args and args[0].startswith('--'):
        opt = args.pop(0)
        if opt == '--buffers':
            gen_buffers = True
        elif opt == '--out':
            if not args:
                error("--out requires an argument")
            out_dir = args.pop(0)
        elif opt == '--fixed':
            fixed_mode = True
        elif opt == '--big-endian':
            big_endian = True
        elif opt == '--lengths':
            lengths_mode = True
        else:
            error(f"Unknown option: {opt}")

    if len(args) != 1:
        print(f"Usage: {sys.argv[0]} [--fixed] [--big-endian] [--lengths] [--buffers] [--out <dir>] <header.h>",
              file=sys.stderr)
        sys.exit(1)

    if lengths_mode and fixed_mode:
        error("--lengths and --fixed are mutually exclusive")

    path = args[0]
    try:
        with open(path, 'r') as f:
            text = f.read()
    except OSError as e:
        error(f"Cannot open file: {e}")

    structs, enums = parse_header(text, lengths_mode=lengths_mode)
    if not structs:
        error("No structs found in header")

    stem = os.path.splitext(os.path.basename(path))[0]
    if len(out_dir) == 0:
        out_dir = os.path.dirname(path) or '.'

    js_path = os.path.join(out_dir, f"{stem}_buffers.js")
    with open(js_path, 'w') as f:
        f.write(generate_js_module(path, structs, enums, fixed_mode, big_endian))
    print(f"Written: {js_path}")

    if gen_buffers:
        buffers_path = os.path.join(out_dir, "buffers.js")
        with open(buffers_path, 'w') as f:
            f.write(BUFFERS_JS_CONTENT)
        print(f"Written: {buffers_path}")


if __name__ == '__main__':
    main()
