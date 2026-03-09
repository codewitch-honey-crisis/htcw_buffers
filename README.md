# htcw_buffers

htcw_buffers is a code generator that generates code to serialize and deserialize simple fixed size structures.

It allows you to define your interface as a C header file, accepting a fair subset of C, including structs and enums.

The structs can reference other structs in the file and can contain fixed size arrays and fixed size strings.

The generated C code is fast, zero allocation, and flexible, allowing you to stream from and to arbitrary sources using custom callbacks

The generated C# code is fairly efficient, but does allocate, leveraging the GC in order to give you a cleanly typed API. It also renames the definitions to follow dotnet naming guidelines, so `ip_address` becaomes `IPAddress`.

You'll need python installed to run the scripts.

Any shared code can be produced by the scripts so you don't need to reference any runtimes.

By default strings and arrays are prefixed with a length, and then only that number of elements are sent. If `--fixed` is indicated, no length is indicated, and the total number of elements in the array or string are always sent.

### Why not protobuf?

Protobuf is kind of heavy for little devices, and even with nanopb the runtime has a significant footprint.

### Why not msgpack?

Msgpack suffers from similar limitations I mentioned as protobuf, just not as bad.

### Why not flatbuffers?

Flatbuffers has complicated build requirements and doesn't lend itself to building inside the ESP-IDF environment.

## Generating C code
Options:
- `--buffers` generate shared code
- `--fixed` generate fixed size serialization/deserialization code. Note that fixed vs variable length is a change to the wire protocol.
- `--out <dir>` override the output directory
- `--prefix <prefix>` use the given prefix on generated method and define code.
```
python .\buffers_gen_c.py --buffers example.h
```

## C# code
Options:
- `--buffers` generate shared code
- `--fixed` generate fixed size serialization/deserialization code. Note that fixed vs variable length is a change to the wire protocol.
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
#define EXAMPLE_DATA_MESSAGE_SIZE (32)
int example_data_message_read(example_data_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_data_message_write(const example_data_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t example_data_message_size(const example_data_message_t* s); // not available with --fixed
```

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

## The SerialFrameDemo example

To buiid the app, this requires Visual Studio w/ .NET 8 installed, as well as a recent Python installed and in your PATH.

To build the firmware, this requires PlatformIO with the Espressif toolchain installed

The CLI app currently requires Windows in order to run, unfortunately.

The issue is that Microsoft's SerialPort implementation is hopelessly flawed to the point of not being stable in this scenario, and I've never raw dogged an asynchronous linux serial port implementation. I haven't had the time to pick it up.

### What it does:

The CLI application accepts a COM port on the command line to a connected ESP32 with the firmware flashed on it, after which it connects and provides a prompt.

You can type "help" or "?" to get a list of commands to send to the ESP32, or "LOG" which gives you any non-framed data that the ESP32 emitted since the last call to "LOG". By non-framed data, this means any data that is not in the packet format, such as the boot messages displayed when the ESP32 resets, or arbitrary text written out using the C stdio facilities.

With it you can do things like get the MAC address, get/set GPIO, and query the ESP32 RNG hardware for random numbers.

It works by framing the data with 8 command bytes, followed by the frame payload length, then the payload CRC, both 32-bit unsigned integers, although len is effectively restricted to 32768 with the remaining numeric space being used to detect serial corruption. After that comes the payload.

Built on top of that, htcw_buffers serializes and deserializes messages defined in `interface.h` into frame payloads on either end.