#include "buffers.h"
#include "interface_buffers.h"

static int read_st_gpio_mode_t(st_gpio_mode_t* e, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    uint8_t tmp;
    res = buffers_read_uint8_t(&tmp, on_read, on_read_state);
    if(res < 0) { return res; }
    *e = (st_gpio_mode_t)tmp;
    return res;
}

static int write_st_gpio_mode_t(st_gpio_mode_t e, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    uint8_t tmp = (uint8_t)e;
    res = buffers_write_uint8_t(tmp, on_write, on_write_state);
    return res;
}

int interface_read_st_esp_idf_version_message(st_esp_idf_version_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int interface_write_st_esp_idf_version_message(const st_esp_idf_version_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int interface_read_st_rng_message(st_rng_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int interface_write_st_rng_message(const st_rng_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int interface_read_st_gpio_get_message(st_gpio_get_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->mask, on_read, on_read_state);
    return res;
}

int interface_write_st_gpio_get_message(const st_gpio_get_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->mask, on_write, on_write_state);
    return res;
}

int interface_read_st_gpio_set_message(st_gpio_set_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->mask, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint64_t(&s->values, on_read, on_read_state);
    return res;
}

int interface_write_st_gpio_set_message(const st_gpio_set_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->mask, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint64_t(s->values, on_write, on_write_state);
    return res;
}

int interface_read_st_gpio_mode_message(st_gpio_mode_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint8_t(&s->gpio, on_read, on_read_state);
    if(res < 0) { return res; }
    res = read_st_gpio_mode_t(&s->mode, on_read, on_read_state);
    return res;
}

int interface_write_st_gpio_mode_message(const st_gpio_mode_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint8_t(s->gpio, on_write, on_write_state);
    if(res < 0) { return res; }
    res = write_st_gpio_mode_t(s->mode, on_write, on_write_state);
    return res;
}

int interface_read_st_mac_address_message(st_mac_address_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int interface_write_st_mac_address_message(const st_mac_address_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

int interface_read_st_esp_idf_version_response_message(st_esp_idf_version_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    for(int i = 0; i < 64; ++i) {
        res = buffers_read_char(&s->version[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    res = buffers_read_uint8_t(&s->major, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->minor, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->patch, on_read, on_read_state);
    return res;
}

int interface_write_st_esp_idf_version_response_message(const st_esp_idf_version_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    for(int i = 0; i < 64; ++i) {
        res = buffers_write_char(s->version[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    res = buffers_write_uint8_t(s->major, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->minor, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->patch, on_write, on_write_state);
    return res;
}

int interface_read_st_rng_response_message(st_rng_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint32_t(&s->value, on_read, on_read_state);
    return res;
}

int interface_write_st_rng_response_message(const st_rng_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint32_t(s->value, on_write, on_write_state);
    return res;
}

int interface_read_st_gpio_get_response_message(st_gpio_get_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->values, on_read, on_read_state);
    return res;
}

int interface_write_st_gpio_get_response_message(const st_gpio_get_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->values, on_write, on_write_state);
    return res;
}

int interface_read_st_mac_address_response_message(st_mac_address_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    for(int i = 0; i < 6; ++i) {
        res = buffers_read_uint8_t(&s->address[i], on_read, on_read_state);
        if(res < 0) { return res; }
    }
    return res;
}

int interface_write_st_mac_address_response_message(const st_mac_address_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    for(int i = 0; i < 6; ++i) {
        res = buffers_write_uint8_t(s->address[i], on_write, on_write_state);
        if(res < 0) { return res; }
    }
    return res;
}
