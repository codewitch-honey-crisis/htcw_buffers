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

int st_esp_idf_version_message_read(st_esp_idf_version_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int st_esp_idf_version_message_write(const st_esp_idf_version_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

size_t st_esp_idf_version_message_size(const st_esp_idf_version_message_t* s) {
    size_t size = 0;
    return size;
}

int st_rng_message_read(st_rng_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int st_rng_message_write(const st_rng_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

size_t st_rng_message_size(const st_rng_message_t* s) {
    size_t size = 0;
    return size;
}

int st_gpio_get_message_read(st_gpio_get_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->mask, on_read, on_read_state);
    return res;
}

int st_gpio_get_message_write(const st_gpio_get_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->mask, on_write, on_write_state);
    return res;
}

size_t st_gpio_get_message_size(const st_gpio_get_message_t* s) {
    size_t size = 0;
    size += 8;
    return size;
}

int st_gpio_set_message_read(st_gpio_set_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->mask, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint64_t(&s->values, on_read, on_read_state);
    return res;
}

int st_gpio_set_message_write(const st_gpio_set_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->mask, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint64_t(s->values, on_write, on_write_state);
    return res;
}

size_t st_gpio_set_message_size(const st_gpio_set_message_t* s) {
    size_t size = 0;
    size += 8;
    size += 8;
    return size;
}

int st_gpio_mode_message_read(st_gpio_mode_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint8_t(&s->gpio, on_read, on_read_state);
    if(res < 0) { return res; }
    res = read_st_gpio_mode_t(&s->mode, on_read, on_read_state);
    return res;
}

int st_gpio_mode_message_write(const st_gpio_mode_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint8_t(s->gpio, on_write, on_write_state);
    if(res < 0) { return res; }
    res = write_st_gpio_mode_t(s->mode, on_write, on_write_state);
    return res;
}

size_t st_gpio_mode_message_size(const st_gpio_mode_message_t* s) {
    size_t size = 0;
    size += 1;
    size += 1;
    return size;
}

int st_mac_address_message_read(st_mac_address_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    return 0;
}

int st_mac_address_message_write(const st_mac_address_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    return 0;
}

size_t st_mac_address_message_size(const st_mac_address_message_t* s) {
    size_t size = 0;
    return size;
}

int st_esp_idf_version_response_message_read(st_esp_idf_version_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    {
        uint8_t _len_version;
        res = buffers_read_uint8_t(&_len_version, on_read, on_read_state);
        if(res < 0) { return res; }
        if(_len_version > 64) { return BUFFERS_ERROR_EOF; }
        for(int i = 0; i < (int)_len_version; ++i) {
            res = buffers_read_char(&s->version[i], on_read, on_read_state);
            if(res < 0) { return res; }
        }
        if(_len_version < 64) {
            s->version[_len_version] = '\0';
        }
    }
    res = buffers_read_uint8_t(&s->major, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->minor, on_read, on_read_state);
    if(res < 0) { return res; }
    res = buffers_read_uint8_t(&s->patch, on_read, on_read_state);
    return res;
}

int st_esp_idf_version_response_message_write(const st_esp_idf_version_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    {
        uint8_t _len_version = 0;
        for(int i = 0; i < 64; ++i) {
            if(s->version[i] == '\0') break;
            _len_version++;
        }
        res = buffers_write_uint8_t(_len_version, on_write, on_write_state);
        if(res < 0) { return res; }
        for(int i = 0; i < (int)_len_version; ++i) {
            res = buffers_write_char(s->version[i], on_write, on_write_state);
            if(res < 0) { return res; }
        }
    }
    res = buffers_write_uint8_t(s->major, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->minor, on_write, on_write_state);
    if(res < 0) { return res; }
    res = buffers_write_uint8_t(s->patch, on_write, on_write_state);
    return res;
}

size_t st_esp_idf_version_response_message_size(const st_esp_idf_version_response_message_t* s) {
    size_t size = 0;
    {
        uint8_t _len = 0;
        for(int i = 0; i < 64; ++i) {
            if(s->version[i] == '\0') break;
            _len++;
        }
        size += 1 + (size_t)_len * 1;
    }
    size += 1;
    size += 1;
    size += 1;
    return size;
}

int st_rng_response_message_read(st_rng_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint32_t(&s->value, on_read, on_read_state);
    return res;
}

int st_rng_response_message_write(const st_rng_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint32_t(s->value, on_write, on_write_state);
    return res;
}

size_t st_rng_response_message_size(const st_rng_response_message_t* s) {
    size_t size = 0;
    size += 4;
    return size;
}

int st_gpio_get_response_message_read(st_gpio_get_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    res = buffers_read_uint64_t(&s->values, on_read, on_read_state);
    return res;
}

int st_gpio_get_response_message_write(const st_gpio_get_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    res = buffers_write_uint64_t(s->values, on_write, on_write_state);
    return res;
}

size_t st_gpio_get_response_message_size(const st_gpio_get_response_message_t* s) {
    size_t size = 0;
    size += 8;
    return size;
}

int st_mac_address_response_message_read(st_mac_address_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state) {
    int res;
    {
        uint8_t _len_address;
        res = buffers_read_uint8_t(&_len_address, on_read, on_read_state);
        if(res < 0) { return res; }
        if(_len_address > 6) { return BUFFERS_ERROR_EOF; }
        for(int i = 0; i < (int)_len_address; ++i) {
            res = buffers_read_uint8_t(&s->address[i], on_read, on_read_state);
            if(res < 0) { return res; }
        }
        for(int i = (int)_len_address; i < 6; ++i) {
            memset(&s->address[i], 0, sizeof(s->address[i]));
        }
    }
    return res;
}

int st_mac_address_response_message_write(const st_mac_address_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state) {
    int res;
    {
        uint8_t _len_address = 6;
        res = buffers_write_uint8_t(_len_address, on_write, on_write_state);
        if(res < 0) { return res; }
        for(int i = 0; i < (int)_len_address; ++i) {
            res = buffers_write_uint8_t(s->address[i], on_write, on_write_state);
            if(res < 0) { return res; }
        }
    }
    return res;
}

size_t st_mac_address_response_message_size(const st_mac_address_response_message_t* s) {
    size_t size = 0;
    size += 1 + (size_t)6 * 1;
    return size;
}
