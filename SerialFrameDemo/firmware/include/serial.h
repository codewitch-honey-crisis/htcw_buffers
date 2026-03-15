#ifndef SERIAL_H
#define SERIAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
bool serial_init(size_t max_payload_size);
int serial_getc(void);
void serial_putc(int value);
#ifdef __cplusplus
}
#endif
#endif  // SERIAL_H