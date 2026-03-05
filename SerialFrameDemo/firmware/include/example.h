// generate with:
// C code
// python .\buffers_gen_c.py --buffers example.h
// C# code
// python .\buffers_gen_cs.py --namespace Example --buffers example.h
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