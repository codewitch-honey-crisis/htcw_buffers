#ifndef EXAMPLE_BUFFERS_H
#define EXAMPLE_BUFFERS_H
#include "example.h"
#include "buffers.h"

#define EXAMPLE_MAX_SIZE (162)
#define EXAMPLE_EXAMPLE_COLOR_SIZE (4)
#define EXAMPLE_EXAMPLE_VALUE_SIZE (8)
#define EXAMPLE_EXAMPLE_VALUES_ENTRY_SIZE (16)
#define EXAMPLE_EXAMPLE_DATA_MESSAGE_SIZE (32)
#define EXAMPLE_EXAMPLE_SCREEN_VALUE_ENTRY_SIZE (16)
#define EXAMPLE_EXAMPLE_SCREEN_ENTRY_SIZE (68)
#define EXAMPLE_EXAMPLE_SCREEN_MESSAGE_SIZE (138)
#define EXAMPLE_EXAMPLE_NOP_MESSAGE_SIZE (0)
#define EXAMPLE_EXAMPLE_CLEAR_MESSAGE_SIZE (0)
#define EXAMPLE_EXAMPLE_MODE_MESSAGE_SIZE (1)
#define EXAMPLE_EXAMPLE_RESET_SCREEN_MESSAGE_SIZE (0)
#define EXAMPLE_EXAMPLE_IDENT_REQUEST_MESSAGE_SIZE (0)
#define EXAMPLE_EXAMPLE_IDENT_MESSAGE_SIZE (162)

#ifdef __cplusplus
extern "C" {
#endif

int example_read_example_color(example_color_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_color(const example_color_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_value(example_value_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_value(const example_value_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_values_entry(example_values_entry_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_values_entry(const example_values_entry_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_data_message(example_data_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_data_message(const example_data_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_screen_value_entry(example_screen_value_entry_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_screen_value_entry(const example_screen_value_entry_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_screen_entry(example_screen_entry_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_screen_entry(const example_screen_entry_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_screen_message(example_screen_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_screen_message(const example_screen_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_nop_message(example_nop_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_nop_message(const example_nop_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_clear_message(example_clear_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_clear_message(const example_clear_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_mode_message(example_mode_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_mode_message(const example_mode_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_reset_screen_message(example_reset_screen_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_reset_screen_message(const example_reset_screen_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_ident_request_message(example_ident_request_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_ident_request_message(const example_ident_request_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

int example_read_example_ident_message(example_ident_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int example_write_example_ident_message(const example_ident_message_t* s, buffers_write_callback_t on_write, void* on_write_state);

#ifdef __cplusplus
}
#endif
#endif /* EXAMPLE_BUFFERS_H */
