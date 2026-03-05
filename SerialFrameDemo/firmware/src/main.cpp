#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_idf_version.h"
#include "esp_system.h"
#include <memory.h>
#include <stdio.h>
#include "serial.hpp"
#include "example_buffers.h"
static void loop();
static void loop_task(void* arg) {
    TickType_t wdt_ts = xTaskGetTickCount();
    while(1) {
        TickType_t ticks = xTaskGetTickCount();
        if(ticks>wdt_ts+pdMS_TO_TICKS(200)) {
            wdt_ts = ticks;
            vTaskDelay(5);
        }
        loop();
    }
}
extern "C" void app_main() {
    serial_init();
    TaskHandle_t loop_handle;
    xTaskCreate(loop_task,"loop_task",8192,NULL,1,&loop_handle);
}
typedef struct {
    size_t remaining;
    uint8_t* ptr;
} buffer_write_cursor_t;
typedef struct {
    size_t remaining;
    const uint8_t* ptr;
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
static void loop() {
    static uint8_t msg_buffer[EXAMPLE_MAX_SIZE];
    serial_update();
    uint8_t cmd;
    void* ptr;
    size_t length;
    if(serial_try_get_frame(&cmd,&ptr,&length)) {
        buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
        switch((example_message_command_t)cmd) {
            case CMD_NOP: {
                example_nop_message_t msg;
                if(-1<example_read_example_nop_message(&msg,on_read_buffer,&read_cur)) {
                    puts("NOP received");
                }
            }
            break;
            case CMD_SCREEN: {
                example_screen_message_t msg;
                if(-1<example_read_example_screen_message(&msg,on_read_buffer,&read_cur)) {
                    puts("Screen received");
                }
            }
            break;
            case CMD_DATA: {
                example_data_message_t msg;
                if(-1<example_read_example_data_message(&msg,on_read_buffer,&read_cur)) {
                    puts("Data received");
                }
            }
            break;
            case CMD_IDENT_REQUEST: {
                example_ident_request_message_t msg;
                if(-1<example_read_example_ident_request_message(&msg,on_read_buffer,&read_cur)) {
                    buffer_write_cursor_t write_cur = {EXAMPLE_MAX_SIZE,msg_buffer};
                    example_ident_message_t ident;
                    memset(&ident,0,sizeof(ident));
                    ident.build = 01234567;
                    ident.id=32768;
                    ident.version_major = 4;
                    ident.version_minor = 0;
                    ident.dpi = 96.f;
                    ident.pixel_size = 1.f;
                    ident.input_type = INPUT_TOUCH;
                    ident.is_monochrome = false;
                    ident.horizontal_resolution = 320;
                    ident.vertical_resolution = 240;
                    strcpy(ident.display_name,"Test Display Name");
                    strcpy(ident.slug,"test-slug");
                    memcpy(ident.mac_address,(uint8_t[]){1,2,3,4,5,6},6);
                    if(-1<example_write_example_ident_message(&ident,on_write_buffer,&write_cur)) {
                        if(!serial_put_frame(CMD_IDENT,msg_buffer,EXAMPLE_EXAMPLE_IDENT_MESSAGE_SIZE)) {
                            puts("Write error");
                        }
                    }
                }
            }
            break;
            case CMD_MODE: {
                example_mode_message_t msg;
                if(-1<example_read_example_mode_message(&msg,on_read_buffer,&read_cur)) {
                    puts("Mode received");
                }
            }
            break;
            case CMD_RESET_SCREEN: {
                example_reset_screen_message_t msg;
                if(-1<example_read_example_reset_screen_message(&msg,on_read_buffer,&read_cur)) {
                    puts("Reset screen received");
                }
            }
            break;
            case CMD_CLEAR: {
                example_clear_message_t msg;
                if(-1<example_read_example_clear_message(&msg,on_read_buffer,&read_cur)) {
                    puts("Clear received");
                }
            }
            break;
            default: {
                printf("Unknown command received %d\n",(int)cmd);
                serial_discard_frame();
            }
            break;
        }
    }
}
