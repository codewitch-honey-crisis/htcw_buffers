#ifndef INTERFACE_BUFFERS_H
#define INTERFACE_BUFFERS_H
#include "interface.h"
#include "buffers.h"

#define INTERFACE_MAX_SIZE (68)
#define ST_ESP_IDF_VERSION_MESSAGE_SIZE (0)
#define ST_RNG_MESSAGE_SIZE (0)
#define ST_GPIO_GET_MESSAGE_SIZE (8)
#define ST_GPIO_SET_MESSAGE_SIZE (16)
#define ST_GPIO_MODE_MESSAGE_SIZE (2)
#define ST_MAC_ADDRESS_MESSAGE_SIZE (0)
#define ST_ESP_IDF_VERSION_RESPONSE_MESSAGE_SIZE (68)
#define ST_RNG_RESPONSE_MESSAGE_SIZE (4)
#define ST_GPIO_GET_RESPONSE_MESSAGE_SIZE (8)
#define ST_MAC_ADDRESS_RESPONSE_MESSAGE_SIZE (7)

#ifdef __cplusplus
extern "C" {
#endif

int st_esp_idf_version_message_read(st_esp_idf_version_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_esp_idf_version_message_write(const st_esp_idf_version_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_esp_idf_version_message_size(const st_esp_idf_version_message_t* s);

int st_rng_message_read(st_rng_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_rng_message_write(const st_rng_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_rng_message_size(const st_rng_message_t* s);

int st_gpio_get_message_read(st_gpio_get_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_gpio_get_message_write(const st_gpio_get_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_gpio_get_message_size(const st_gpio_get_message_t* s);

int st_gpio_set_message_read(st_gpio_set_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_gpio_set_message_write(const st_gpio_set_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_gpio_set_message_size(const st_gpio_set_message_t* s);

int st_gpio_mode_message_read(st_gpio_mode_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_gpio_mode_message_write(const st_gpio_mode_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_gpio_mode_message_size(const st_gpio_mode_message_t* s);

int st_mac_address_message_read(st_mac_address_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_mac_address_message_write(const st_mac_address_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_mac_address_message_size(const st_mac_address_message_t* s);

int st_esp_idf_version_response_message_read(st_esp_idf_version_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_esp_idf_version_response_message_write(const st_esp_idf_version_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_esp_idf_version_response_message_size(const st_esp_idf_version_response_message_t* s);

int st_rng_response_message_read(st_rng_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_rng_response_message_write(const st_rng_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_rng_response_message_size(const st_rng_response_message_t* s);

int st_gpio_get_response_message_read(st_gpio_get_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_gpio_get_response_message_write(const st_gpio_get_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_gpio_get_response_message_size(const st_gpio_get_response_message_t* s);

int st_mac_address_response_message_read(st_mac_address_response_message_t* s, buffers_read_callback_t on_read, void* on_read_state);
int st_mac_address_response_message_write(const st_mac_address_response_message_t* s, buffers_write_callback_t on_write, void* on_write_state);
size_t st_mac_address_response_message_size(const st_mac_address_response_message_t* s);

#ifdef __cplusplus
}
#endif
#endif /* INTERFACE_BUFFERS_H */
