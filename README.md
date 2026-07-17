# htcw_buffers

htcw_buffers is a code generator that generates code to serialize and deserialize simple fixed size structures.

It allows you to define your interface as a C header file, accepting a fair subset of C, including structs and enums.

The structs can reference other structs in the file and can contain fixed size arrays and fixed size strings.

The generated C code is fast, zero allocation, and flexible, allowing you to stream from and to arbitrary sources using custom callbacks

The generated C# code is fairly efficient, but the classic version does allocate, leveraging the GC in order to give you a cleanly typed API. It also renames the definitions to follow dotnet naming guidelines, so `ip_address` becomes `IPAddress`. You can use the C#12 `buffers_gen_cs12.py` version to avoid allocating.

You'll need python installed to run the scripts.

Any shared code can be produced by the scripts so you don't need to reference any runtimes.

By default strings are prefixed with a length, and then only that number of characters up to the terminating `\0` are sent. If `--fixed` is indicated, no length is indicated, and the total number of characters in the string are always sent.

Non-string fixed-size arrays are always sent at their full declared length. The `--lengths` option (see [Runtime-length arrays](#runtime-length-arrays) below) lets you opt specific arrays into runtime-sized serialization by pairing them with a preceding `size_t` count field.

### Why not protobuf?

Protobuf is kind of heavy for little devices, and even with nanopb the runtime has a significant footprint.

### Why not msgpack?

Msgpack suffers from similar limitations I mentioned as protobuf, just not as bad.

### Why not flatbuffers?

Flatbuffers has complicated build requirements and doesn't lend itself to building inside the ESP-IDF environment.

## Generating C code
Options:
- `--buffers` generate shared code
- `--big-endian` generate big endian wire format (defaults little endian)
- `--fixed` generate fixed size serialization/deserialization code. Note that fixed vs variable length is a change to the wire protocol.
- `--lengths` enable runtime-length arrays. When a struct has a `size_t` field that *immediately precedes* a fixed-size array, the count is treated as the actual number of elements in the array on the wire. See [Runtime-length arrays](#runtime-length-arrays) below. Mutually exclusive with `--fixed`.
- `--out <dir>` override the output directory
- `--out_h <dir>` override the header output directory (defaults to output directory)
- `--prefix <prefix>` use the given prefix on generated method and define code.
```
python .\buffers_gen_c.py --buffers example.h
```

## C# code
Options:
- `--buffers` generate shared code
- `--big-endian` generate big endian wire format (defaults little endian)
- `--fixed` generate fixed size serialization/deserialization code. Note that fixed vs variable length is a change to the wire protocol.
- `--lengths` enable runtime-length arrays (see [Runtime-length arrays](#runtime-length-arrays)). Mutually exclusive with `--fixed`. On the C# side the `size_t` count field is *hidden* — it does not appear as a property; the count is taken from the array property's `.Length` / `.Count` on write and consumed (but discarded) on read.
- `--public` generate public types
- `--namespace <namespace>` generate under the indicated namespace
- `--out <dir>` override the output directory

```
python .\buffers_gen_cs.py --namespace Example --buffers example.h
```
Here is an example schema for an idea of what it looks like and supports.
```c
#ifndef EXAMPLE_H
#define EXAMPLE_H
#include <stdint.h>
#include <stdbool.h>

typedef enum {
    CMD_NONE,
    CMD_DATA,
    CMD_SCREEN,
    CMD_NOP,
    CMD_CLEAR,
    CMD_MODE,
    CMD_RESET_SCREEN,
    CMD_IDENT_REQUEST,
    CMD_IDENT
} example_message_command_t;

typedef enum { // flags
    INPUT_NONE   = 0,
    INPUT_TOUCH  = 1,
    INPUT_BUTTON = 2
} example_input_type_t;

typedef struct {
  uint8_t a;
  uint8_t r;
  uint8_t g;
  uint8_t b;
} example_color_t;

typedef struct {
    float value;
    float scaled;
} example_value_t;

typedef struct {
    example_value_t value1;
    example_value_t value2;
} example_values_entry_t;

typedef struct {
    example_values_entry_t top;
    example_values_entry_t bottom;
} example_data_message_t;

typedef struct {
    char suffix[12];
    example_color_t color;
} example_screen_value_entry_t;

typedef struct {
    char label[32];
    example_color_t color;
    example_screen_value_entry_t value1;
    example_screen_value_entry_t value2;
} example_screen_entry_t;

typedef struct {
    int8_t index;
    uint8_t flags;
    example_screen_entry_t top;
    example_screen_entry_t bottom;
} example_screen_message_t;

// you don't technically need to declare empty messages here, but
// doing so can make your code that uses the API more consistent
// because you won't have to corner case for empty messages
typedef struct {
} example_nop_message_t;

typedef struct {
} example_clear_message_t;
typedef struct {
    uint8_t mode;
} example_mode_message_t;
typedef struct {
} example_reset_screen_message_t;
typedef struct {
} example_ident_request_message_t;

typedef struct {
    uint16_t version_major;
    uint16_t version_minor;
    uint64_t build;
    uint16_t id;
    uint8_t mac_address[6];
    char display_name[64];
    char slug[64];
    uint16_t horizontal_resolution;
    uint16_t vertical_resolution;
    bool is_monochrome;
    float dpi;
    float pixel_size;
    example_input_type_t input_type;
} example_ident_message_t;

// this is skipped (don't expect unions to be part of the interface)
typedef union {
    example_data_message_t data;
    example_screen_message_t screen;
    example_nop_message_t nop;
    example_clear_message_t clear;
    example_mode_message_t mode;
    example_reset_screen_message_t reset_screen;
    example_ident_request_message_t ident_request;
    example_ident_message_t ident;
} example_message_t;
#endif // EXAMPLE_H
```

This will generate `example_buffers.h`/`.c` which will give you an API you can use to serialize and deserialize.

For example, to serialize and deserialize `example_data_message_t` from above the following API members are provided.
```c
#define EXAMPLE_DATA_MESSAGE_SIZE (32) // the maximum wire size of the message
int example_data_message_read(example_data_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_data_message_write(const example_data_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t example_data_message_size(const example_data_message_t* s); // not available with --fixed
```
On return the read and write functions return a non-negative number indicating the bytes read or written, and a negative number on error.

To read and write, you need to provide callbacks that support a streaming cursor. This is simple enough, for example over an array/buffer using the following code:
```c
typedef struct {
    uint8_t* ptr;
    size_t remaining;
} buffer_write_cursor_t;
typedef struct {
    const uint8_t* ptr;
    size_t remaining;
} buffer_read_cursor_t;
int on_write_buffer(uint8_t value, void* state) {
    buffer_write_cursor_t* cur = (buffer_write_cursor_t*)state;
    if(cur->remaining==0) {
        return BUFFERS_ERROR_EOF;
    }
    *cur->ptr++=value;
    --cur->remaining;
    return 1;
}
int on_read_buffer(void* state) {
    buffer_read_cursor_t* cur = (buffer_read_cursor_t*)state;
    if(cur->remaining==0) {
        return BUFFERS_EOF;
    }
    uint8_t result = *cur->ptr++;
    --cur->remaining;
    return result;
}
```
You can then deserialize like this:
```c
// EXAMPLE_MAX_SIZE is defined in example_buffers.h and indicates the longest defined message length
uint8_t buffer[EXAMPLE_MAX_SIZE];
// at some point populate the above buffer with data... 
example_data_message_t msg;
buffer_read_cursor_t read_cur = {(const uint8_t*)buffer, EXAMPLE_DATA_MESSAGE_SIZE};
if(-1<example_data_message_read(&msg,on_read_buffer,&read_cur)) {
    // msg is filled
}
```
And you can serialize like this:
```c
uint8_t buffer[EXAMPLE_MAX_SIZE];
example_data_message_t msg;
// at some point populate the above msg with data... 
buffer_write_cursor_t write_cur = {(uint8_t*)buffer, EXAMPLE_DATA_MESSAGE_SIZE};
if(-1<example_data_message_write(&msg,on_write_buffer,&write_cur)) {
    // The first 32 bytes of buffer is filled with the message
}
```
The C# API is exposed slightly differently, in a way that is more dotnet-styled.

For example from above, deserialization in C# is like this:
```cs
var buffer = new byte[ExampleMaxSize.Value];
// at some point populate buffer above with data...
if(ExampleDataMessage.TryRead(buffer,out var exMsg, out _)) 
{
    // exMsg is filled
}
```
Serializing works like this:
```cs
var buffer = new byte[ExampleMaxSize.Value];
var exMsg = new ExampleDataMessage();
// populate exMsg with data...
// buffer could have used exMsg.SizeOfStruct to get the 
// wire size of the populated struct instead of the max
// possible size of any struct. In addition StructMaxSize
// gets the max possible wire size of a given struct
if(exMsg.TryWrite(buffer, out _)) {
    // buffer is filled
}
```
Note that these serialization methods work with spans, byte arrays, or streams.

### `buffers_gen_cs` vs `buffers_gen_cs12`

There are two C# generators. They parse the same headers and — importantly — emit the **same wire format**, so the choice between them is purely about the C# API and how it's implemented on the managed side. It never changes what goes over the wire, and either one interoperates with the C and JS sides.

- **`buffers_gen_cs`** works on older C# language versions. Fixed arrays and strings are surfaced through a cleanly typed, GC-allocated API (this is the "does allocate, leveraging the GC" behavior described near the top of this README). Pick it when you need to target a language version or runtime that predates the features `buffers_gen_cs12` relies on.
- **`buffers_gen_cs12`** requires the **C# 12** language version (and .NET 8+, since it depends on `[InlineArray]`). Every fixed array and fixed string is stored *inline* inside the owning struct via a generated `[InlineArray(N)]` helper — there is no per-field heap array behind the property. The default API exposes those fields as `ReadOnlySpan<T>` read views over that inline storage, so reads and the entire serialize/deserialize path are allocation-free. The cleanly typed, allocating surface (`string` / `T[]`) is opt-in per build via `--friendly`; even then a zero-alloc `Get…Span()` accessor is emitted alongside it.

| | `buffers_gen_cs` | `buffers_gen_cs12` |
|---|---|---|
| C# language version | pre-12 is fine | **12** required |
| Key dependency | — | `[InlineArray]` (.NET 8+) |
| Fixed array / string storage | GC-allocated, typed | inline, in-struct (`[InlineArray]`) |
| Default field access | typed, allocating | `ReadOnlySpan<T>`, zero-alloc |
| Cleanly-typed `string` / `T[]` API | always (the default) | opt-in via `--friendly` |
| Struct layout control | — | `--bltable` or `--reorder` |
| Wire format | identical | identical |

`buffers_gen_cs12` adds a few options on top of the shared ones listed above:
- `--friendly` expose allocating `string` / `T[]` members as the primary API (with `Get…Span()` still available), instead of the default span-first surface.
- `--bltable` emit `[StructLayout(LayoutKind.Sequential, Pack = 1)]` on each struct for a blittable, packed layout. Off by default, because forcing `Pack = 1` can misalign fields and slow member access. Mutually exclusive with `--reorder`.
- `--reorder` emit `[StructLayout(LayoutKind.Auto)]` so the runtime may reorder fields to reduce padding (which makes the struct non-blittable). Mutually exclusive with `--bltable`.

Inline helper structs are named `<Header>Inline<ClrType>Length<N>` (e.g. `InterfaceInlineUInt32Length1024`), prefixed with the header stem so helpers generated from different headers into the same namespace don't collide.

In short: reach for `buffers_gen_cs12` on .NET 8+ when you want the tighter, lower-allocation API, and `buffers_gen_cs` when you need to support an older language version or runtime.

## JS code
Options:
- `--buffers` generate shared code
- `--big-endian` generate big endian wire format (defaults little endian)
- `--fixed` generate fixed size serialization/deserialization code. Note that fixed vs variable length is a change to the wire protocol.
- `--lengths` enable runtime-length arrays (see [Runtime-length arrays](#runtime-length-arrays)). Mutually exclusive with `--fixed`. On the JS side the `size_t` count field is *hidden* — it does not appear as a property; the count is taken from the array property's `.length` on write and consumed (but discarded) on read.
- `--out <dir>` override the output directory

```
python .\buffers_gen_js.py --buffers example.h
```

The JS generator targets modern browsers (and Node). It emits an ES module per header (`example_buffers.js`) plus a shared `buffers.js` (produced with `--buffers`) that the module imports for its string codecs and the `asBytes` input normalizer. Everything is `import`/`export`; there are no runtime dependencies to reference.

The JS API is exposed in a way that is idiomatic to JavaScript rather than mirroring C or .NET. A "struct" is just a plain object — you read one out and add properties to it at runtime. There are no classes and the objects carry no methods. Reading and writing are done with exported free functions, named after the type:
- `<name>Read(u8, offset = 0, outBytesRead = null)` decodes a struct from a byte source. The first argument may be a `Uint8Array`, an `ArrayBuffer` (or `SharedArrayBuffer`), or any `ArrayBuffer` view such as a `DataView` or other typed array — anything that isn't already a `Uint8Array` is wrapped in a zero-copy view over the same memory, so nothing is copied even for large messages. It returns the decoded object, or `null` on failure (buffer too small, or a runtime count that exceeds capacity). If you pass an array as `outBytesRead`, `outBytesRead[0]` receives the number of bytes consumed.
- `<name>Write(obj, u8, offset = 0)` encodes a struct into a byte destination. It accepts the same input types as `Read`; because the destination is wrapped in a zero-copy view, writing into an `ArrayBuffer` (or `DataView`, etc.) mutates that underlying buffer in place. It returns the number of bytes written, or `-1` on failure. The optional `offset` lets you pack several messages into one buffer.
- `<name>Size(obj)` returns the actual wire size of a populated object (not generated with `--fixed`).

The C# generator renamed definitions to follow dotnet naming guidelines (`ip_address` becomes `IPAddress`). The JS generator does the analogous thing for JavaScript: identifiers become `camelCase`, so `ip_address` becomes `ipAddress`, `display_name` becomes `displayName`, and `mac_address` becomes `macAddress`. Because JavaScript has no two-letter-acronym convention, the casing is plain — `device_id` becomes `deviceId`, not `deviceID`. Enums are exported as frozen objects in `PascalCase` with `PascalCase` members, so `example_input_type_t` / `INPUT_TOUCH` becomes `ExampleInputType.InputTouch`. Per-struct size constants (`EXAMPLE_DATA_MESSAGE_SIZE`) and the module-wide maximum (`EXAMPLE_MAX_SIZE`) are exported as `SCREAMING_SNAKE_CASE` to match the C `#define`s.

64-bit integer fields (`uint64_t` / `int64_t`) are surfaced as `BigInt`, since JS numbers can't represent the full 64-bit range exactly. Every smaller integer is a plain `number`. `bool` is a JS `boolean`.

For example, to deserialize `example_data_message_t` from above:
```js
import { exampleDataMessageRead, EXAMPLE_MAX_SIZE } from './example_buffers.js';

const buffer = new Uint8Array(EXAMPLE_MAX_SIZE);
// at some point populate buffer above with data...
const msg = exampleDataMessageRead(buffer);
if (msg !== null) {
    // msg is filled, e.g. msg.top.value1.value
}
```
Serializing works like this:
```js
import { exampleDataMessageWrite, exampleDataMessageSize, EXAMPLE_MAX_SIZE } from './example_buffers.js';

const buffer = new Uint8Array(EXAMPLE_MAX_SIZE);
const msg = {};
// populate msg with data...
// you could have used exampleDataMessageSize(msg) to size the buffer to the
// wire size of the populated struct instead of the max size of any struct.
const written = exampleDataMessageWrite(msg, buffer);
if (written >= 0) {
    // the first `written` bytes of buffer are filled with the message
}
```
The `offset` argument and the `outBytesRead` out-array make it easy to read or write a sequence of messages back-to-back over a single `Uint8Array`:
```js
const out = [0];
const first = exampleModeMessageRead(buffer, 0, out);
const second = exampleModeMessageRead(buffer, out[0], out);
```

### Working with binary transports (WebSocket, fetch, etc.)

Because the read/write functions accept an `ArrayBuffer` or any `ArrayBuffer` view directly, you can hand them the payload from a binary transport without an intermediate copy. A `WebSocket` message is the common case — just make sure the socket is in `arraybuffer` mode, since browsers default `binaryType` to `blob`:

```js
import { exampleDataMessageRead } from './example_buffers.js';

const ws = new WebSocket(url);
ws.binaryType = 'arraybuffer';            // event.data is now an ArrayBuffer
ws.onmessage = (event) => {
    const msg = exampleDataMessageRead(event.data);   // no copy, no wrapping
    if (msg !== null) {
        // handle msg
    }
};
```

The wrapping is always a zero-copy view over the same memory, so this stays cheap even for large frames. A few things worth knowing:

- **`Blob` is not accepted** (it's the browser default for `binaryType`). A `Blob`'s bytes are only available asynchronously, so read it first: `const buf = await blob.arrayBuffer();` then pass `buf`. Node's `ws` library hands you a `Buffer` (a `Uint8Array` subclass) or `ArrayBuffer`, both of which work as-is.
- **The `offset` argument stacks on a view's own `byteOffset`.** If you pass a `DataView` that starts at byte 100 of its buffer and call with `offset = 8`, it reads at absolute byte 108. Passing a whole `ArrayBuffer` is equivalent to `byteOffset` 0, so `offset` is just the position within it.
- **Writing into an `ArrayBuffer` mutates it in place.** The view shares memory with the buffer you passed, so after `write` the bytes are already in your `ArrayBuffer` — ready to `ws.send()`.


## Runtime-length arrays

By default, fixed-size arrays in your structs (other than strings) are always serialized at their full declared length. That's the right tradeoff most of the time — it keeps the wire format predictable and the code simple. But sometimes you have an array whose declared size is just a *cap*, and the actual number of valid elements varies per message.

Passing `--lengths` to either generator turns on a small extension to the schema. When a struct has a `size_t` field that *immediately precedes* a fixed-size array, the generator pairs them: the `size_t` is treated as the runtime element count, and only that many elements appear on the wire.

For example, this schema:
```c
typedef struct {
    uint16_t id;
    size_t   count;
    uint8_t  bytes[256];
} blob_message_t;
```
With `--lengths`, the wire format for a `blob_message_t` is:
- `id` (2 bytes)
- `count` (4 bytes — `size_t` is normalized to `uint32_t` on the wire regardless of platform)
- `count` × 1 byte of `bytes`

So a message with `count = 5` takes 11 bytes on the wire, not 262. The declared `[256]` is the maximum capacity, used for the `BLOB_MESSAGE_SIZE` / `StructMaxSize` constants and for the runtime bounds check during read/write.

A few rules to keep the behavior predictable:

- **It must be a `size_t`.** Other unsigned types like `uint32_t` or `uint16_t` won't trigger pairing, even though `size_t` happens to map to `uint32_t` on the wire. The strict match keeps the schema's intent obvious.
- **It must immediately precede the array.** Any other field between them — even another scalar — and pairing is skipped. The `size_t` then just serializes as a normal `uint32_t`.
- **Strings are unaffected.** `char[N]` and `wchar_t[N]` still use their existing length-prefix behavior driven by the null terminator.
- **Each `size_t` pairs with at most one array.** A lonely `size_t` at the end of a struct, or a `size_t` followed by a string or scalar, just serializes as a regular field.
- **Mutually exclusive with `--fixed`.** The two flags imply different things about the wire format; combining them errors out.
- **The `MAX_SIZE` / `StructMaxSize` constants don't shrink.** They still reflect the worst case, so you can keep allocating fixed buffers the same way you did before.

### C side

The generated C struct is unchanged — both the `size_t` count and the array stay as ordinary fields. You populate `s->count` yourself before writing, and the read function fills it in for you on the way back. If you set `count` larger than the array's declared capacity, write returns `BUFFERS_ERROR_EOF`.

```c
blob_message_t out = {0};
out.id = 0xBEEF;
out.count = 5;
for (size_t i = 0; i < 5; ++i) out.bytes[i] = (uint8_t)i;

uint8_t buffer[BLOB_MESSAGE_SIZE];
buffer_write_cursor_t cur = { buffer, sizeof(buffer) };
if (-1 < blob_message_write(&out, on_write_buffer, &cur)) {
    // 11 bytes written
}
```

The `*_size()` runtime function returns the actual wire size of a populated instance, taking the runtime count into account.

### C# side

The C# API is rendered idiomatically: the `size_t` count field is **hidden** — it does not appear as a property. The count is taken from the array property's `.Length` (or `.Count` for `IList<T>` of nested structs) on write, and on read the count is consumed from the wire but discarded; the resulting array's length carries the information.

```cs
var msg = new BlobMessage {
    ID = 0xBEEF,
    Bytes = new byte[] { 0, 1, 2, 3, 4 }
};
var buf = new byte[BlobMessage.StructMaxSize];
if (msg.TryWrite(buf, out int written)) {
    // 11 bytes written; msg has no Count property to manage
}
```

If the array is longer than the declared capacity, `TryWrite` returns `false`. A `null` array is treated as count zero on write; on read, an empty count produces a zero-length array (not `null`).

### JS side

The JS API is rendered idiomatically, the same way the C# one is: the `size_t` count field is **hidden** — it does not appear as a property. The count is taken from the array property's `.length` on write, and on read the count is consumed from the wire but discarded; the resulting array's length carries the information.

```js
import { blobMessageWrite, BLOB_MESSAGE_SIZE } from './blob_buffers.js';

const msg = {
    id: 0xBEEF,
    bytes: [0, 1, 2, 3, 4]
};
const buf = new Uint8Array(BLOB_MESSAGE_SIZE);
const written = blobMessageWrite(msg, buf);
if (written >= 0) {
    // 11 bytes written; msg has no count property to manage
}
```

If the array is longer than the declared capacity, `blobMessageWrite` returns `-1`. A `null` or absent array is treated as count zero on write; on read, an empty count produces a zero-length array (not `null`). The `<name>Size()` function returns the actual wire size of a populated object, taking the runtime count into account.

## The SerialFrameDemo example

![Demo](https://github.com/codewitch-honey-crisis/htcw_buffers/blob/9a5458748cf929c11df9b00d5e2e1a6b178488c7/SerialFrameDemo.jpg)

To build the app, this requires Visual Studio w/ .NET 8 installed, as well as a recent Python installed and in your PATH.

To build the firmware, this requires PlatformIO with the Espressif toolchain installed

The CLI app currently requires Windows in order to run, unfortunately.

The issue is that Microsoft's SerialPort implementation is hopelessly flawed to the point of not being stable in this scenario, and I've never raw dogged an asynchronous linux serial port implementation. I haven't had the time to pick it up.

### What it does:

The CLI application accepts a COM port on the command line to a connected ESP32 with the firmware flashed on it, after which it connects and provides a prompt.

You can type "help" or "?" to get a list of commands to send to the ESP32, or "LOG" which gives you any non-framed data that the ESP32 emitted since the last call to "LOG". By non-framed data, this means any data that is not in the packet format, such as the boot messages displayed when the ESP32 resets, or arbitrary text written out using the C stdio facilities.

With it you can do things like get the MAC address, get/set GPIO, and query the ESP32 RNG hardware for random numbers.

It works by framing the data with 8 command bytes, followed by the frame payload length, then the payload CRC, both 32-bit unsigned integers, although len is effectively restricted to 32768 with the remaining numeric space being used to detect serial corruption. After that comes the payload.

Built on top of that, htcw_buffers serializes and deserializes messages defined in `interface.h` into frame payloads on either end.