#include "buffers.h"
#include "example_buffers.h"

static int read_example_input_type_t(example_input_type_t* e, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    uint8_t tmp;
    res = buffers_read_uint8_t(&tmp, on_read, on_read_state);
    if(res < 0) { return res; }
    *e = (example_input_type_t)tmp;
    return res;
}

static int write_example_input_type_t(example_input_type_t e, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    uint8_t tmp = (uint8_t)e;
    res = buffers_write_uint8_t(tmp, on_write, on_write_state);
    return res;
}

int example_read_example_color(example_color_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint8_t(&s->a, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->r, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->g, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->b, on_read, on_read_state);
    return res;
}

int example_write_example_color(const example_color_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint8_t(s->a, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->r, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->g, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->b, on_write, on_write_state);
    return res;
}

int example_read_example_value(example_value_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_float(&s->value, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_float(&s->scaled, on_read, on_read_state);
    return res;
}

int example_write_example_value(const example_value_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_float(s->value, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_float(s->scaled, on_write, on_write_state);
    return res;
}

int example_read_example_values_entry(example_values_entry_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = example_read_example_value(&s->value1, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_value(&s->value2, on_read, on_read_state);
    return res;
}

int example_write_example_values_entry(const example_values_entry_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = example_write_example_value(&s->value1, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_value(&s->value2, on_write, on_write_state);
    return res;
}

int example_read_example_data_message(example_data_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = example_read_example_values_entry(&s->top, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_values_entry(&s->bottom, on_read, on_read_state);
    return res;
}

int example_write_example_data_message(const example_data_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = example_write_example_values_entry(&s->top, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_values_entry(&s->bottom, on_write, on_write_state);
    return res;
}

int example_read_example_screen_value_entry(example_screen_value_entry_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    for(int i = 0; i < 12; ++i) {
        res = buffers_read_char(&s->suffix[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    res = example_read_example_color(&s->color, on_read, on_read_state);
    return res;
}

int example_write_example_screen_value_entry(const example_screen_value_entry_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    for(int i = 0; i < 12; ++i) {
        res = buffers_write_char(s->suffix[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    res = example_write_example_color(&s->color, on_write, on_write_state);
    return res;
}

int example_read_example_screen_entry(example_screen_entry_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    for(int i = 0; i < 32; ++i) {
        res = buffers_read_char(&s->label[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    res = example_read_example_color(&s->color, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_screen_value_entry(&s->value1, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_screen_value_entry(&s->value2, on_read, on_read_state);
    return res;
}

int example_write_example_screen_entry(const example_screen_entry_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    for(int i = 0; i < 32; ++i) {
        res = buffers_write_char(s->label[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    res = example_write_example_color(&s->color, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_screen_value_entry(&s->value1, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_screen_value_entry(&s->value2, on_write, on_write_state);
    return res;
}

int example_read_example_screen_message(example_screen_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_int8_t(&s->index, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->flags, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_screen_entry(&s->top, on_read, on_read_state);
    if(res < 0) { return res; }
    res = example_read_example_screen_entry(&s->bottom, on_read, on_read_state);
    return res;
}

int example_write_example_screen_message(const example_screen_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_int8_t(s->index, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->flags, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_screen_entry(&s->top, on_write, on_write_state);
    if(res < 0) { return res; }
    res = example_write_example_screen_entry(&s->bottom, on_write, on_write_state);
    return res;
}

int example_read_example_nop_message(example_nop_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int example_write_example_nop_message(const example_nop_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int example_read_example_clear_message(example_clear_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int example_write_example_clear_message(const example_clear_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int example_read_example_mode_message(example_mode_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint8_t(&s->mode, on_read, on_read_state);
    return res;
}

int example_write_example_mode_message(const example_mode_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint8_t(s->mode, on_write, on_write_state);
    return res;
}

int example_read_example_reset_screen_message(example_reset_screen_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int example_write_example_reset_screen_message(const example_reset_screen_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int example_read_example_ident_request_message(example_ident_request_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int example_write_example_ident_request_message(const example_ident_request_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int example_read_example_ident_message(example_ident_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint16_t(&s->version_major, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint16_t(&s->version_minor, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint64_t(&s->build, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint16_t(&s->id, on_read, on_read_state);
    if(res < 0) { return res; }
    for(int i = 0; i < 6; ++i) {
        res = buffers_read_uint8_t(&s->mac_address[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    for(int i = 0; i < 64; ++i) {
        res = buffers_read_char(&s->display_name[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    for(int i = 0; i < 64; ++i) {
        res = buffers_read_char(&s->slug[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    res = buffers_read_uint16_t(&s->horizontal_resolution, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint16_t(&s->vertical_resolution, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_bool(&s->is_monochrome, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_float(&s->dpi, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_float(&s->pixel_size, on_read, on_read_state);
    if(res < 0) { return res; }
    res = read_example_input_type_t(&s->input_type, on_read, on_read_state);
    return res;
}

int example_write_example_ident_message(const example_ident_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint16_t(s->version_major, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint16_t(s->version_minor, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint64_t(s->build, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint16_t(s->id, on_write, on_write_state);
    if(res < 0) { return res; }
    for(int i = 0; i < 6; ++i) {
        res = buffers_write_uint8_t(s->mac_address[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    for(int i = 0; i < 64; ++i) {
        res = buffers_write_char(s->display_name[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    for(int i = 0; i < 64; ++i) {
        res = buffers_write_char(s->slug[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    res = buffers_write_uint16_t(s->horizontal_resolution, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint16_t(s->vertical_resolution, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_bool(s->is_monochrome, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_float(s->dpi, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_float(s->pixel_size, on_write, on_write_state);
    if(res < 0) { return res; }
    res = write_example_input_type_t(s->input_type, on_write, on_write_state);
    return res;
}
