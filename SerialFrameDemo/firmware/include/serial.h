#ifndef SERIAL_H
#define SERIAL_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
bool serial_init(size_t max_payload_size);
bool serial_update(void);
bool serial_try_get_frame(uint8_t* out_cmd,void** out_ptr, size_t* out_length);
bool serial_put_frame(uint8_t cmd, void* frame, size_t frame_length);
bool serial_discard_frame(void);
#ifdef __cplusplus
}
#endif
#endif // SERIAL_H