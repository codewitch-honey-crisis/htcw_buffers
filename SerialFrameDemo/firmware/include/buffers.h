#ifndef HTCW_BUFFERS_H
#define HTCW_BUFFERS_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>  /* memcpy */
#ifdef __cplusplus
extern "C" {
#endif

enum {
    BUFFERS_ERROR_EOF = -2,
    BUFFERS_EOF       = -1,
    BUFFERS_SUCCESS   =  0
};

typedef int  (*buffers_read_callback_t )(void* state);
typedef int  (*buffers_write_callback_t)(uint8_t value, void* state);

/* -------------------------------------------------------------------------
 * Read functions — little-endian (native/default)
 * ------------------------------------------------------------------------- */
int buffers_read_uint8_t (uint8_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_uint16_t(uint16_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint32_t(uint32_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint64_t(uint64_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_int8_t  (int8_t*   result, buffers_read_callback_t cb, void* state);
int buffers_read_int16_t (int16_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int32_t (int32_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int64_t (int64_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_float   (float*    result, buffers_read_callback_t cb, void* state);
int buffers_read_double  (double*   result, buffers_read_callback_t cb, void* state);
/* aliases */
int buffers_read_char          (char*               result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_char (unsigned char*      result, buffers_read_callback_t cb, void* state);
int buffers_read_short         (short*              result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_short(unsigned short*     result, buffers_read_callback_t cb, void* state);
int buffers_read_int           (int*                result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_int  (unsigned int*       result, buffers_read_callback_t cb, void* state);
int buffers_read_long          (long*               result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_long (unsigned long*      result, buffers_read_callback_t cb, void* state);
int buffers_read_long_long         (long long*          result, buffers_read_callback_t cb, void* state);
int buffers_read_unsigned_long_long(unsigned long long* result, buffers_read_callback_t cb, void* state);
int buffers_read_bool          (bool*                result, buffers_read_callback_t cb, void* state);
int buffers_read_wchar_t       (wchar_t*            result, buffers_read_callback_t cb, void* state);
int buffers_read_size_t        (size_t*             result, buffers_read_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Read functions — big-endian (_be variants)
 * ------------------------------------------------------------------------- */
int buffers_read_uint16_t_be(uint16_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint32_t_be(uint32_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_uint64_t_be(uint64_t* result, buffers_read_callback_t cb, void* state);
int buffers_read_int16_t_be (int16_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int32_t_be (int32_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_int64_t_be (int64_t*  result, buffers_read_callback_t cb, void* state);
int buffers_read_float_be   (float*    result, buffers_read_callback_t cb, void* state);
int buffers_read_double_be  (double*   result, buffers_read_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Write functions — little-endian
 * ------------------------------------------------------------------------- */
int buffers_write_uint8_t (uint8_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_uint16_t(uint16_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint32_t(uint32_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint64_t(uint64_t value, buffers_write_callback_t cb, void* state);
int buffers_write_int8_t  (int8_t   value, buffers_write_callback_t cb, void* state);
int buffers_write_int16_t (int16_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int32_t (int32_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int64_t (int64_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_float   (float    value, buffers_write_callback_t cb, void* state);
int buffers_write_double  (double   value, buffers_write_callback_t cb, void* state);
/* aliases */
int buffers_write_char          (char               value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_char (unsigned char      value, buffers_write_callback_t cb, void* state);
int buffers_write_short         (short              value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_short(unsigned short     value, buffers_write_callback_t cb, void* state);
int buffers_write_int           (int                value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_int  (unsigned int       value, buffers_write_callback_t cb, void* state);
int buffers_write_long          (long               value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_long (unsigned long      value, buffers_write_callback_t cb, void* state);
int buffers_write_long_long         (long long          value, buffers_write_callback_t cb, void* state);
int buffers_write_unsigned_long_long(unsigned long long value, buffers_write_callback_t cb, void* state);
int buffers_write_bool          (bool                value, buffers_write_callback_t cb, void* state);
int buffers_write_wchar_t       (wchar_t            value, buffers_write_callback_t cb, void* state);
int buffers_write_size_t        (size_t             value, buffers_write_callback_t cb, void* state);

/* -------------------------------------------------------------------------
 * Write functions — big-endian
 * ------------------------------------------------------------------------- */
int buffers_write_uint16_t_be(uint16_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint32_t_be(uint32_t value, buffers_write_callback_t cb, void* state);
int buffers_write_uint64_t_be(uint64_t value, buffers_write_callback_t cb, void* state);
int buffers_write_int16_t_be (int16_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int32_t_be (int32_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_int64_t_be (int64_t  value, buffers_write_callback_t cb, void* state);
int buffers_write_float_be   (float    value, buffers_write_callback_t cb, void* state);
int buffers_write_double_be  (double   value, buffers_write_callback_t cb, void* state);

#ifdef __cplusplus
}
#endif
#endif /* HTCW_BUFFERS_H */