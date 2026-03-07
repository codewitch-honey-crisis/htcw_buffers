#!/usr/bin/env python3
"""
buffers_gen_c.py - Parse wire structs from a C header and generate
                   read/write functions for each struct.

Usage: python buffers_gen_c.py [--prefix <pfx>] [--buffers] [--out <dir>] <header.h>

Options:
  --prefix <pfx>   Prepend <pfx> to every generated function name and
                   per-struct #define (not to the MAX_SIZE define).
  --buffers        Also emit buffers.h / buffers.c support files.
  --out <dir>      Directory for generated files (default: same as input).

Outputs:
  <stem>_buffers.h   - declarations for all read/write functions
  <stem>_buffers.c   - implementations

Function naming:
  - Typedef names ending in _t have _t stripped
  - struct name precedes _read / _write
  - e.g. example_data_message_t -> [prefix]example_data_message_read / [prefix]example_data_message_write
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Type mapping
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

WIRE_SCALAR_TYPES = {
    'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
    'int8_t',  'int16_t',  'int32_t',  'int64_t',
    'float',   'double',
}

WIRE_TYPE_SIZES = {
    'uint8_t':  1,
    'uint16_t': 2,
    'uint32_t': 4,
    'uint64_t': 8,
    'int8_t':   1,
    'int16_t':  2,
    'int32_t':  4,
    'int64_t':  8,
    'float':    4,
    'double':   8,
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


def type_fn_suffix(type_name: str) -> str:
    """Strip trailing _t from typedef names for use in function names."""
    if type_name.endswith('_t'):
        return type_name[:-2]
    return type_name

def header_stem_to_define_prefix(header_path: str) -> str:
    """Convert header filename stem to a valid uppercase C identifier prefix."""
    stem = os.path.splitext(os.path.basename(header_path))[0]
    ident = re.sub(r'[^A-Za-z0-9]', '_', stem).upper()
    if ident and ident[0].isdigit():
        ident = '_' + ident
    return ident


def struct_size_define_name(struct_name: str, user_prefix: str = "") -> str:
    """Return the #define name for a struct's wire size.

    e.g. nop_message_t  -> NOP_MESSAGE_SIZE
         with user_prefix="EX_" -> EX_NOP_MESSAGE_SIZE
    """
    name = struct_name
    if name.endswith('_t'):
        name = name[:-2]
    name = re.sub(r'[^A-Za-z0-9]', '_', name).upper()
    up = user_prefix.upper()
    return f"{up}{name}_SIZE"

# ---------------------------------------------------------------------------
# Enum parsing
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
    enums = {}
    found = []
    for m in ENUM_TYPEDEF_RE.finditer(text):
        found.append((m.group('n'), m.group('body')))
    typedef_names = {n for n, _ in found}
    for m in ENUM_RE.finditer(text):
        if m.group('n') not in typedef_names:
            found.append((m.group('n'), m.group('body')))
    for name, body in found:
        if name in enums:
            error(f"Duplicate enum name: '{name}'")
        values = []
        current = 0
        for entry in body.split(','):
            entry = entry.strip()
            if not entry:
                continue
            if '=' in entry:
                lhs, rhs = entry.split('=', 1)
                rhs = rhs.strip()
                if not _INT_LITERAL_RE.fullmatch(rhs):
                    error(f"Enum '{name}': non-literal value '{rhs}' not supported")
                current = int(rhs, 0)
            values.append(current)
            current += 1
        if values:
            enums[name] = enum_wire_type(min(values), max(values))
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
        return known_enums[type_str]
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
    is_enum = False
    if type_str in known_enums:
        is_enum = True
    return {"name": name, "type": type_str, "wire_type": wire_type, "array_len": array_len, "is_enum": is_enum}


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


def parse_header(text: str) -> dict:
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
            if f['name'] in seen:
                error(f"Struct '{name}': duplicate field name '{f['name']}'")
            seen.add(f['name'])
        structs[name] = {"fields": fields}

    return structs

# ---------------------------------------------------------------------------
# Wire size computation
# ---------------------------------------------------------------------------

def wire_size_of(wire_type: str, array_len, structs: dict,
                 _visiting: frozenset = frozenset()) -> int:
    """Return the wire byte size of a single field, recursing into nested structs."""
    if wire_type in WIRE_TYPE_SIZES:
        element_size = WIRE_TYPE_SIZES[wire_type]
    elif wire_type in structs:
        if wire_type in _visiting:
            error(f"Circular struct reference detected involving '{wire_type}'")
        element_size = struct_wire_size(wire_type, structs, _visiting | {wire_type})
    else:
        error(f"Cannot determine wire size for type '{wire_type}'")

    count = array_len if array_len is not None else 1
    return element_size * count


def struct_wire_size(struct_name: str, structs: dict,
                     _visiting: frozenset = frozenset()) -> int:
    """Return the total wire byte size of a single instance of struct_name."""
    return sum(
        wire_size_of(f['wire_type'], f['array_len'], structs, _visiting)
        for f in structs[struct_name]['fields']
    )


def compute_max_wire_size(structs: dict) -> int:
    """Return the maximum wire size across all top-level structs."""
    if not structs:
        return 0
    return max(struct_wire_size(name, structs) for name in structs)

# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------


def read_fn_name(user_prefix, struct_name):
    return f"{user_prefix}{type_fn_suffix(struct_name)}_read"


def write_fn_name(user_prefix, struct_name):
    return f"{user_prefix}{type_fn_suffix(struct_name)}_write"


def gen_read_call(prefix, field, accessor, all_struct_names, indent="    "):
    wt = field['wire_type']
    if wt in all_struct_names:
        fn = read_fn_name(prefix, wt)
        return [f"{indent}res = {fn}(&{accessor}, on_read, on_read_state);",
                f"{indent}if(res < 0) {{ return res; }}"]
    elif field['is_enum']:
        wt = field['type']
        return [f"{indent}res = read_{wt}(&{accessor}, on_read, on_read_state);",
                f"{indent}if(res < 0) {{ return res; }}"]
    else:
        wt = field['type']
        return [f"{indent}res = buffers_read_{wt}(&{accessor}, on_read, on_read_state);",
                f"{indent}if(res < 0) {{ return res; }}"]


def gen_write_call(prefix, field, accessor, all_struct_names, indent="    "):
    wt = field['wire_type']
    if wt in all_struct_names:
        fn = write_fn_name(prefix, wt)
        return [f"{indent}res = {fn}(&{accessor}, on_write, on_write_state);",
                f"{indent}if(res < 0) {{ return res; }}"]
    elif field['is_enum']:
        wt = field['type']
        return [f"{indent}res = write_{wt}({accessor}, on_write, on_write_state);",
                f"{indent}if(res < 0) {{ return res; }}"]
    else:
        wt = field['type']
        return [f"{indent}res = buffers_write_{wt}({accessor}, on_write, on_write_state);",
                f"{indent}if(res < 0) {{ return res; }}"]

def gen_enum_write_fn(enum_name, wire_type):
    fn = f"write_{enum_name}"
    lines = [f"static int {fn}({enum_name} e, buffers_write_callback_t on_write, void* on_write_state) {{"]
    lines.append("    int res;")
    lines.append(f"    {wire_type} tmp = ({wire_type})e;")
    lines.append(f"    res = buffers_write_{wire_type}(tmp, on_write, on_write_state);")
    lines.append("    return res;")
    lines.append("}")
    return "\n".join(lines)

def gen_write_fn(prefix, struct_name, fields, all_struct_names):
    fn = write_fn_name(prefix, struct_name)
    lines = [f"int {fn}(const {struct_name}* s, buffers_write_callback_t on_write, void* on_write_state) {{"]
    if not fields:
        lines.append("    return 0;")
    else:
        lines.append("    int res;")
        for i, f in enumerate(fields):
            is_last = (i == len(fields) - 1)
            if f['array_len'] is not None:
                lines.append(f"    for(int i = 0; i < {f['array_len']}; ++i) {{")
                stmts = gen_write_call(prefix, f, f"s->{f['name']}[i]", all_struct_names, indent="        ")
                lines.extend(stmts)
                lines.append("    }")
            else:
                stmts = gen_write_call(prefix, f, f"s->{f['name']}", all_struct_names)
                lines.append(stmts[0])
                if not is_last:
                    lines.append(stmts[1])
        lines.append("    return res;")
    lines.append("}")
    return "\n".join(lines)

def gen_enum_read_fn(enum_name, wire_type):
    fn = f"read_{enum_name}"
    lines = [f"static int {fn}({enum_name}* e, buffers_read_callback_t on_read, void* on_read_state) {{"]
    lines.append("    int res;")
    lines.append(f"    {wire_type} tmp;")
    lines.append(f"    res = buffers_read_{wire_type}(&tmp, on_read, on_read_state);")
    lines.append("    if(res < 0) { return res; }")
    lines.append(f"    *e = ({enum_name})tmp;")
    lines.append("    return res;")
    lines.append("}")
    return "\n".join(lines)

def gen_read_fn(prefix, struct_name, fields, all_struct_names):
    fn = read_fn_name(prefix, struct_name)
    lines = [f"int {fn}({struct_name}* s, buffers_read_callback_t on_read, void* on_read_state) {{"]
    if not fields:
        lines.append("    return 0;")
    else:
        lines.append("    int res;")
        for i, f in enumerate(fields):
            is_last = (i == len(fields) - 1)
            if f['array_len'] is not None:
                lines.append(f"    for(int i = 0; i < {f['array_len']}; ++i) {{")
                stmts = gen_read_call(prefix, f, f"s->{f['name']}[i]", all_struct_names, indent="        ")
                lines.extend(stmts)
                lines.append("    }")
            else:
                stmts = gen_read_call(prefix, f, f"s->{f['name']}", all_struct_names)
                lines.append(stmts[0])
                if not is_last:
                    lines.append(stmts[1])
        lines.append("    return res;")
    lines.append("}")
    return "\n".join(lines)


def gen_write_fn(prefix, struct_name, fields, all_struct_names):
    fn = write_fn_name(prefix, struct_name)
    lines = [f"int {fn}(const {struct_name}* s, buffers_write_callback_t on_write, void* on_write_state) {{"]
    if not fields:
        lines.append("    return 0;")
    else:
        lines.append("    int res;")
        for i, f in enumerate(fields):
            is_last = (i == len(fields) - 1)
            if f['array_len'] is not None:
                lines.append(f"    for(int i = 0; i < {f['array_len']}; ++i) {{")
                stmts = gen_write_call(prefix, f, f"s->{f['name']}[i]", all_struct_names, indent="        ")
                lines.extend(stmts)
                lines.append("    }")
            else:
                stmts = gen_write_call(prefix, f, f"s->{f['name']}", all_struct_names)
                lines.append(stmts[0])
                if not is_last:
                    lines.append(stmts[1])
        lines.append("    return res;")
    lines.append("}")
    return "\n".join(lines)


def generate_h(header_path, user_prefix, structs):
    stem = os.path.splitext(os.path.basename(header_path))[0]
    guard = f"{stem.upper()}_BUFFERS_H"
    define_prefix = header_stem_to_define_prefix(header_path)
    max_size = compute_max_wire_size(structs)                 
    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        f'#include "{os.path.basename(header_path)}"',
        '#include "buffers.h"',
        "",
        f"#define {define_prefix}_MAX_SIZE ({max_size})",
    ]
    for struct_name in structs:
        size = struct_wire_size(struct_name, structs)
        define = struct_size_define_name(struct_name, user_prefix)
        lines.append(f"#define {define} ({size})")
    lines += [
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
    ]
    for struct_name in structs:
        lines.append(f"int {read_fn_name(user_prefix, struct_name)}({struct_name}* s, buffers_read_callback_t on_read, void* on_read_state);")
        lines.append(f"int {write_fn_name(user_prefix, struct_name)}(const {struct_name}* s, buffers_write_callback_t on_write, void* on_write_state);")
        lines.append("")
    lines += ["#ifdef __cplusplus", "}", "#endif", f"#endif /* {guard} */", ""]
    return "\n".join(lines)


def generate_c(header_path, user_prefix, structs):
    stem = os.path.splitext(os.path.basename(header_path))[0]
    all_struct_names = set(structs.keys())
    lines = [
        '#include "buffers.h"',
        f'#include "{stem}_buffers.h"',
        "",
    ]
    enum_types = dict()
    for struct_name, info in structs.items():
        for field in info['fields']:
            if field['is_enum']:
              enum_types[field['type']]=field['wire_type']

    for enum_name, wire_type in enum_types.items():
        lines.append(gen_enum_read_fn(enum_name, wire_type))
        lines.append("")
        lines.append(gen_enum_write_fn(enum_name, wire_type))
        lines.append("")

    for struct_name, info in structs.items():
        lines.append(gen_read_fn(user_prefix, struct_name, info['fields'], all_struct_names))
        lines.append("")
        lines.append(gen_write_fn(user_prefix, struct_name, info['fields'], all_struct_names))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

BUFFERS_H_CONTENT = r"""#ifndef HTCW_BUFFERS_H
#define HTCW_BUFFERS_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>  /* memcpy */
#ifdef __cplusplus
extern "C" {
#endif

enum {
    BUFFERS_ERROR_EOF = -2,
    BUFFERS_EOF       = -1,
    BUFFERS_SUCCESS   =  0
};

typedef int  (*buffers_read_callback_t )(void* state);
typedef int  (*buffers_write_callback_t)(uint8_t value, void* state);

/* -------------------------------------------------------------------------
 * Read functions — little-endian (native/default)
 * ------------------------------------------------------------------------- */
int buffers_read_uint8_t (uint8_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_uint16_t(uint16_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint32_t(uint32_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint64_t(uint64_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_int8_t  (int8_t*   result, buffers_read_callback_t cb, void* state);
int buffers_read_int16_t (int16_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int32_t (int32_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int64_t (int64_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_float   (float*    result, buffers_read_callback_t cb, void* state);
int buffers_read_double  (double*   result, buffers_read_callback_t cb, void* state);
/* aliases */
int buffers_read_char          (char*               result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_char (unsigned char*      result, buffers_read_callback_t cb, void* state);
int buffers_read_short         (short*              result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_short(unsigned short*     result, buffers_read_callback_t cb, void* state);
int buffers_read_int           (int*                result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_int  (unsigned int*       result, buffers_read_callback_t cb, void* state);
int buffers_read_long          (long*               result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_long (unsigned long*      result, buffers_read_callback_t cb, void* state);
int buffers_read_long_long         (long long*          result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_long_long(unsigned long long* result, buffers_read_callback_t cb, void* state);
int buffers_read_bool          (bool*               result, buffers_read_callback_t cb, void* state);
int buffers_read_wchar_t       (wchar_t*            result, buffers_read_callback_t cb, void* state);
int buffers_read_size_t        (size_t*             result, buffers_read_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Read functions — big-endian (_be variants)
 * ------------------------------------------------------------------------- */
int buffers_read_uint16_t_be(uint16_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint32_t_be(uint32_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint64_t_be(uint64_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_int16_t_be (int16_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int32_t_be (int32_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int64_t_be (int64_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_float_be   (float*    result, buffers_read_callback_t cb, void* state);
int buffers_read_double_be  (double*   result, buffers_read_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Write functions — little-endian
 * ------------------------------------------------------------------------- */
int buffers_write_uint8_t (uint8_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_uint16_t(uint16_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint32_t(uint32_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint64_t(uint64_t value, buffers_write_callback_t cb, void* state);
int buffers_write_int8_t  (int8_t   value, buffers_write_callback_t cb, void* state);
int buffers_write_int16_t (int16_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int32_t (int32_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int64_t (int64_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_float   (float    value, buffers_write_callback_t cb, void* state);
int buffers_write_double  (double   value, buffers_write_callback_t cb, void* state);
/* aliases */
int buffers_write_char          (char               value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_char (unsigned char      value, buffers_write_callback_t cb, void* state);
int buffers_write_short         (short              value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_short(unsigned short     value, buffers_write_callback_t cb, void* state);
int buffers_write_int           (int                value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_int  (unsigned int       value, buffers_write_callback_t cb, void* state);
int buffers_write_long          (long               value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_long (unsigned long      value, buffers_write_callback_t cb, void* state);
int buffers_write_long_long         (long long          value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_long_long(unsigned long long value, buffers_write_callback_t cb, void* state);
int buffers_write_bool          (bool               value, buffers_write_callback_t cb, void* state);
int buffers_write_wchar_t       (wchar_t            value, buffers_write_callback_t cb, void* state);
int buffers_write_size_t        (size_t             value, buffers_write_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Write functions — big-endian
 * ------------------------------------------------------------------------- */
int buffers_write_uint16_t_be(uint16_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint32_t_be(uint32_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint64_t_be(uint64_t value, buffers_write_callback_t cb, void* state);
int buffers_write_int16_t_be (int16_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int32_t_be (int32_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int64_t_be (int64_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_float_be   (float    value, buffers_write_callback_t cb, void* state);
int buffers_write_double_be  (double   value, buffers_write_callback_t cb, void* state);

#ifdef __cplusplus
}
#endif
#endif /* HTCW_BUFFERS_H */
"""

BUFFERS_C_CONTENT = r"""#include "buffers.h"

/* =========================================================================
 * Internal helpers
 * ========================================================================= */

static int read_byte(buffers_read_callback_t cb, void* state, uint8_t* out) {
    int b = cb(state);
    if (b == -1) return BUFFERS_ERROR_EOF;
    if (b  <  0) return b;
    *out = (uint8_t)b;
    return 0;
}

static int write_byte(uint8_t v, buffers_write_callback_t cb, void* state) {
    int r = cb(v, state);
    if (r < 0) return r;
    return 0;
}

/* =========================================================================
 * uint8_t
 * ========================================================================= */
int buffers_read_uint8_t(uint8_t* result, buffers_read_callback_t cb, void* state) {
    return read_byte(cb, state, result);
}
int buffers_write_uint8_t(uint8_t value, buffers_write_callback_t cb, void* state) {
    return write_byte(value, cb, state);
}

/* =========================================================================
 * int8_t
 * ========================================================================= */
int buffers_read_int8_t(int8_t* result, buffers_read_callback_t cb, void* state) {
    uint8_t tmp; int r = read_byte(cb, state, &tmp); if (r < 0) return r;
    *result = (int8_t)tmp; return 0;
}
int buffers_write_int8_t(int8_t value, buffers_write_callback_t cb, void* state) {
    return write_byte((uint8_t)value, cb, state);
}

/* =========================================================================
 * uint16_t  — little-endian: low byte first
 * ========================================================================= */
int buffers_read_uint16_t(uint16_t* result, buffers_read_callback_t cb, void* state) {
    uint8_t lo, hi; int r;
    r = read_byte(cb, state, &lo); if (r < 0) return r;
    r = read_byte(cb, state, &hi); if (r < 0) return r;
    *result = (uint16_t)((hi << 8) | lo);
    return 0;
}
int buffers_write_uint16_t(uint16_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = write_byte((uint8_t)(value      ), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >> 8 ), cb, state); if (r < 0) return r;
    return 0;
}

/* big-endian */
int buffers_read_uint16_t_be(uint16_t* result, buffers_read_callback_t cb, void* state) {
    uint8_t hi, lo; int r;
    r = read_byte(cb, state, &hi); if (r < 0) return r;
    r = read_byte(cb, state, &lo); if (r < 0) return r;
    *result = (uint16_t)((hi << 8) | lo);
    return 0;
}
int buffers_write_uint16_t_be(uint16_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = write_byte((uint8_t)(value >> 8), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value     ), cb, state); if (r < 0) return r;
    return 0;
}

/* =========================================================================
 * int16_t
 * ========================================================================= */
int buffers_read_int16_t(int16_t* result, buffers_read_callback_t cb, void* state) {
    uint16_t tmp; int r = buffers_read_uint16_t(&tmp, cb, state); if (r < 0) return r;
    *result = (int16_t)tmp; return 0;
}
int buffers_write_int16_t(int16_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint16_t((uint16_t)value, cb, state);
}
int buffers_read_int16_t_be(int16_t* result, buffers_read_callback_t cb, void* state) {
    uint16_t tmp; int r = buffers_read_uint16_t_be(&tmp, cb, state); if (r < 0) return r;
    *result = (int16_t)tmp; return 0;
}
int buffers_write_int16_t_be(int16_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint16_t_be((uint16_t)value, cb, state);
}

/* =========================================================================
 * uint32_t
 * ========================================================================= */
int buffers_read_uint32_t(uint32_t* result, buffers_read_callback_t cb, void* state) {
    uint8_t b0, b1, b2, b3; int r;
    r = read_byte(cb, state, &b0); if (r < 0) return r;
    r = read_byte(cb, state, &b1); if (r < 0) return r;
    r = read_byte(cb, state, &b2); if (r < 0) return r;
    r = read_byte(cb, state, &b3); if (r < 0) return r;
    *result = ((uint32_t)b3 << 24) | ((uint32_t)b2 << 16) |
              ((uint32_t)b1 <<  8) |  (uint32_t)b0;
    return 0;
}
int buffers_write_uint32_t(uint32_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = write_byte((uint8_t)(value      ), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >>  8), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >> 16), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >> 24), cb, state); if (r < 0) return r;
    return 0;
}
int buffers_read_uint32_t_be(uint32_t* result, buffers_read_callback_t cb, void* state) {
    uint8_t b0, b1, b2, b3; int r;
    r = read_byte(cb, state, &b0); if (r < 0) return r;
    r = read_byte(cb, state, &b1); if (r < 0) return r;
    r = read_byte(cb, state, &b2); if (r < 0) return r;
    r = read_byte(cb, state, &b3); if (r < 0) return r;
    *result = ((uint32_t)b0 << 24) | ((uint32_t)b1 << 16) |
              ((uint32_t)b2 <<  8) |  (uint32_t)b3;
    return 0;
}
int buffers_write_uint32_t_be(uint32_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = write_byte((uint8_t)(value >> 24), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >> 16), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value >>  8), cb, state); if (r < 0) return r;
    r = write_byte((uint8_t)(value      ), cb, state); if (r < 0) return r;
    return 0;
}

/* =========================================================================
 * int32_t
 * ========================================================================= */
int buffers_read_int32_t(int32_t* result, buffers_read_callback_t cb, void* state) {
    uint32_t tmp; int r = buffers_read_uint32_t(&tmp, cb, state); if (r < 0) return r;
    *result = (int32_t)tmp; return 0;
}
int buffers_write_int32_t(int32_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint32_t((uint32_t)value, cb, state);
}
int buffers_read_int32_t_be(int32_t* result, buffers_read_callback_t cb, void* state) {
    uint32_t tmp; int r = buffers_read_uint32_t_be(&tmp, cb, state); if (r < 0) return r;
    *result = (int32_t)tmp; return 0;
}
int buffers_write_int32_t_be(int32_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint32_t_be((uint32_t)value, cb, state);
}

/* =========================================================================
 * uint64_t
 * ========================================================================= */
int buffers_read_uint64_t(uint64_t* result, buffers_read_callback_t cb, void* state) {
    uint32_t lo, hi; int r;
    r = buffers_read_uint32_t(&lo, cb, state); if (r < 0) return r;
    r = buffers_read_uint32_t(&hi, cb, state); if (r < 0) return r;
    *result = ((uint64_t)hi << 32) | lo;
    return 0;
}
int buffers_write_uint64_t(uint64_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = buffers_write_uint32_t((uint32_t)(value      ), cb, state); if (r < 0) return r;
    r = buffers_write_uint32_t((uint32_t)(value >> 32), cb, state); if (r < 0) return r;
    return 0;
}
int buffers_read_uint64_t_be(uint64_t* result, buffers_read_callback_t cb, void* state) {
    uint32_t hi, lo; int r;
    r = buffers_read_uint32_t_be(&hi, cb, state); if (r < 0) return r;
    r = buffers_read_uint32_t_be(&lo, cb, state); if (r < 0) return r;
    *result = ((uint64_t)hi << 32) | lo;
    return 0;
}
int buffers_write_uint64_t_be(uint64_t value, buffers_write_callback_t cb, void* state) {
    int r;
    r = buffers_write_uint32_t_be((uint32_t)(value >> 32), cb, state); if (r < 0) return r;
    r = buffers_write_uint32_t_be((uint32_t)(value      ), cb, state); if (r < 0) return r;
    return 0;
}

/* =========================================================================
 * int64_t
 * ========================================================================= */
int buffers_read_int64_t(int64_t* result, buffers_read_callback_t cb, void* state) {
    uint64_t tmp; int r = buffers_read_uint64_t(&tmp, cb, state); if (r < 0) return r;
    *result = (int64_t)tmp; return 0;
}
int buffers_write_int64_t(int64_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint64_t((uint64_t)value, cb, state);
}
int buffers_read_int64_t_be(int64_t* result, buffers_read_callback_t cb, void* state) {
    uint64_t tmp; int r = buffers_read_uint64_t_be(&tmp, cb, state); if (r < 0) return r;
    *result = (int64_t)tmp; return 0;
}
int buffers_write_int64_t_be(int64_t value, buffers_write_callback_t cb, void* state) {
    return buffers_write_uint64_t_be((uint64_t)value, cb, state);
}

/* =========================================================================
 * float  (IEEE 754, reinterpreted as uint32_t)
 * ========================================================================= */
int buffers_read_float(float* result, buffers_read_callback_t cb, void* state) {
    uint32_t tmp; int r = buffers_read_uint32_t(&tmp, cb, state); if (r < 0) return r;
    memcpy(result, &tmp, sizeof(float)); return 0;
}
int buffers_write_float(float value, buffers_write_callback_t cb, void* state) {
    uint32_t tmp; memcpy(&tmp, &value, sizeof(float));
    return buffers_write_uint32_t(tmp, cb, state);
}
int buffers_read_float_be(float* result, buffers_read_callback_t cb, void* state) {
    uint32_t tmp; int r = buffers_read_uint32_t_be(&tmp, cb, state); if (r < 0) return r;
    memcpy(result, &tmp, sizeof(float)); return 0;
}
int buffers_write_float_be(float value, buffers_write_callback_t cb, void* state) {
    uint32_t tmp; memcpy(&tmp, &value, sizeof(float));
    return buffers_write_uint32_t_be(tmp, cb, state);
}

/* =========================================================================
 * double  (IEEE 754, reinterpreted as uint64_t)
 * ========================================================================= */
int buffers_read_double(double* result, buffers_read_callback_t cb, void* state) {
    uint64_t tmp; int r = buffers_read_uint64_t(&tmp, cb, state); if (r < 0) return r;
    memcpy(result, &tmp, sizeof(double)); return 0;
}
int buffers_write_double(double value, buffers_write_callback_t cb, void* state) {
    uint64_t tmp; memcpy(&tmp, &value, sizeof(double));
    return buffers_write_uint64_t(tmp, cb, state);
}
int buffers_read_double_be(double* result, buffers_read_callback_t cb, void* state) {
    uint64_t tmp; int r = buffers_read_uint64_t_be(&tmp, cb, state); if (r < 0) return r;
    memcpy(result, &tmp, sizeof(double)); return 0;
}
int buffers_write_double_be(double value, buffers_write_callback_t cb, void* state) {
    uint64_t tmp; memcpy(&tmp, &value, sizeof(double));
    return buffers_write_uint64_t_be(tmp, cb, state);
}

/* =========================================================================
 * Alias functions (delegate to the wire-type counterpart)
 * ========================================================================= */

int buffers_read_char(char* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int8_t((int8_t*)r, cb, s); }
int buffers_write_char(char v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int8_t((int8_t)v, cb, s); }

int buffers_read_unsigned_char(unsigned char* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_uint8_t((uint8_t*)r, cb, s); }
int buffers_write_unsigned_char(unsigned char v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint8_t((uint8_t)v, cb, s); }

int buffers_read_short(short* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int16_t((int16_t*)r, cb, s); }
int buffers_write_short(short v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int16_t((int16_t)v, cb, s); }

int buffers_read_unsigned_short(unsigned short* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_uint16_t((uint16_t*)r, cb, s); }
int buffers_write_unsigned_short(unsigned short v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint16_t((uint16_t)v, cb, s); }

int buffers_read_int(int* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int32_t((int32_t*)r, cb, s); }
int buffers_write_int(int v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int32_t((int32_t)v, cb, s); }

int buffers_read_unsigned_int(unsigned int* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_uint32_t((uint32_t*)r, cb, s); }
int buffers_write_unsigned_int(unsigned int v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint32_t((uint32_t)v, cb, s); }

int buffers_read_long(long* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int32_t((int32_t*)r, cb, s); }
int buffers_write_long(long v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int32_t((int32_t)v, cb, s); }

int buffers_read_unsigned_long(unsigned long* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_uint32_t((uint32_t*)r, cb, s); }
int buffers_write_unsigned_long(unsigned long v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint32_t((uint32_t)v, cb, s); }

int buffers_read_long_long(long long* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int64_t((int64_t*)r, cb, s); }
int buffers_write_long_long(long long v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int64_t((int64_t)v, cb, s); }

int buffers_read_unsigned_long_long(unsigned long long* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_uint64_t((uint64_t*)r, cb, s); }
int buffers_write_unsigned_long_long(unsigned long long v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint64_t((uint64_t)v, cb, s); }

int buffers_read_bool(bool* r, buffers_read_callback_t cb, void* s) {
    uint8_t tmp; int res = buffers_read_uint8_t(&tmp, cb, s); if (res < 0) return res;
    *r = tmp ? 1 : 0; return 0; }
int buffers_write_bool(bool v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint8_t(v ? 1 : 0, cb, s); }

int buffers_read_wchar_t(wchar_t* r, buffers_read_callback_t cb, void* s) {
    return buffers_read_int16_t((int16_t*)r, cb, s); }
int buffers_write_wchar_t(wchar_t v, buffers_write_callback_t cb, void* s) {
    return buffers_write_int16_t((int16_t)v, cb, s); }

int buffers_read_size_t(size_t* r, buffers_read_callback_t cb, void* s) {
    uint32_t tmp; int res = buffers_read_uint32_t(&tmp, cb, s); if (res < 0) return res;
    *r = (size_t)tmp; return 0; }
int buffers_write_size_t(size_t v, buffers_write_callback_t cb, void* s) {
    return buffers_write_uint32_t((uint32_t)v, cb, s); }
"""


def main():
    args = sys.argv[1:]
    gen_buffers = False
    out_dir = ""
    user_prefix = ""
    while args and args[0].startswith('--'):
        opt = args.pop(0)
        if opt == '--buffers':
            gen_buffers = True
        elif opt == '--out':
            if not args:
                error("--out requires an argument")
            out_dir = args.pop(0)
        elif opt == '--prefix':
            if not args:
                error("--prefix requires an argument")
            user_prefix = args.pop(0)
        else:
            error(f"Unknown option: {opt}")

    if len(args) != 1:
        print(f"Usage: {sys.argv[0]} [--buffers] [--out <dir>] [--prefix <pfx>] <header.h>", file=sys.stderr)
        sys.exit(1)

    path = args[0]
    try:
        with open(path, 'r') as f:
            text = f.read()
    except OSError as e:
        error(f"Cannot open file: {e}")

    structs = parse_header(text)
    if not structs:
        error("No structs found in header")

    stem = os.path.splitext(os.path.basename(path))[0]

    if len(out_dir) == 0:
        out_dir = os.path.dirname(path) or '.'

    h_path = os.path.join(out_dir, f"{stem}_buffers.h")
    c_path = os.path.join(out_dir, f"{stem}_buffers.c")

    with open(h_path, 'w') as f:
        f.write(generate_h(path, user_prefix, structs))
    with open(c_path, 'w') as f:
        f.write(generate_c(path, user_prefix, structs))

    print(f"Written: {h_path}")
    print(f"Written: {c_path}")

    if gen_buffers:
        bh_path = os.path.join(out_dir, "buffers.h")
        bc_path = os.path.join(out_dir, "buffers.c")
        with open(bh_path, 'w') as f:
            f.write(BUFFERS_H_CONTENT.lstrip('\n'))
        with open(bc_path, 'w') as f:
            f.write(BUFFERS_C_CONTENT.lstrip('\n'))
        print(f"Written: {bh_path}")
        print(f"Written: {bc_path}")


if __name__ == '__main__':
    main()