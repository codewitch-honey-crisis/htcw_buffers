#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_idf_version.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "driver/gpio.h"
#include <memory.h>
#include <stdio.h>
#include "serial.hpp"
#include "interface_buffers.h"
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
    static uint8_t msg_buffer[INTERFACE_MAX_SIZE];
    serial_update();
    uint8_t cmd;
    void* ptr;
    size_t length;
    if(serial_try_get_frame(&cmd,&ptr,&length)) {
        switch((st_message_command_t)cmd) {
            case CMD_ESP_IDF_VERSION: {
                st_esp_idf_version_message_t msg;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_esp_idf_version_message(&msg,on_read_buffer,&read_cur)) {
                    puts("ESP-IDF version requested");
                    buffer_write_cursor_t write_cur = {INTERFACE_MAX_SIZE,msg_buffer};
                    st_esp_idf_version_response_message_t resp;
                    strcpy(resp.version,esp_get_idf_version());
                    resp.major = ESP_IDF_VERSION_MAJOR;
                    resp.minor = ESP_IDF_VERSION_MINOR;
                    resp.patch = ESP_IDF_VERSION_PATCH;
                    interface_write_st_esp_idf_version_response_message(&resp,on_write_buffer,&write_cur);
                    serial_put_frame(CMD_ESP_IDF_VERSION_RESPONSE,msg_buffer,INTERFACE_ST_ESP_IDF_VERSION_RESPONSE_MESSAGE_SIZE);
                }
            }
            break;
            case CMD_RNG: {
                st_rng_message_t msg;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_rng_message(&msg,on_read_buffer,&read_cur)) {
                    puts("RNG generation requested");
                    buffer_write_cursor_t write_cur = {INTERFACE_MAX_SIZE,msg_buffer};
                    st_rng_response_message_t resp;
                    resp.value = esp_random();
                    interface_write_st_rng_response_message(&resp,on_write_buffer,&write_cur);
                    serial_put_frame(CMD_RNG_RESPONSE,msg_buffer,INTERFACE_ST_RNG_RESPONSE_MESSAGE_SIZE);
                }
            }
            break;
            case CMD_GPIO_GET: {
                st_gpio_get_message_t msg;
                uint64_t result = 0;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_gpio_get_message(&msg,on_read_buffer,&read_cur)) {
                    for(int i = 0; i<64;++i) {
                        if(0!=(msg.mask & (((uint64_t)1)<<i))) {
                            printf("GPIO get request for %d\n",(int)i);
                            if(gpio_get_level((gpio_num_t)i)) {
                                result |= (((uint64_t)1)<<i);
                            }
                        }
                    }
                    buffer_write_cursor_t write_cur = {INTERFACE_MAX_SIZE,msg_buffer};
                    st_gpio_get_response_message_t resp;
                    resp.values = result;
                    interface_write_st_gpio_get_response_message(&resp,on_write_buffer,&write_cur);
                    serial_put_frame(CMD_GPIO_GET_RESPONSE,msg_buffer,INTERFACE_ST_GPIO_GET_RESPONSE_MESSAGE_SIZE);
                }
            }
            break;
            case CMD_GPIO_SET: {
                st_gpio_set_message_t msg;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_gpio_set_message(&msg,on_read_buffer,&read_cur)) {
                    for(int i = 0; i<64;++i) {
                        if(0!=(msg.mask & (((uint64_t)1)<<i))) {
                            printf("GPIO set level request for %d\n",(int)i);
                            gpio_set_level((gpio_num_t)i,!!(msg.values&(((uint64_t)1)<<i)));
                        }
                    }
                }
            }
            break;
            case CMD_GPIO_MODE: {
                st_gpio_mode_message_t msg;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_gpio_mode_message(&msg,on_read_buffer,&read_cur)) {
                    printf("GPIO set mode for %d\n",(int)msg.gpio);
                    switch(msg.mode) {
                        case MODE_INPUT:
                            gpio_set_direction((gpio_num_t)msg.gpio,GPIO_MODE_INPUT);
                            gpio_set_pull_mode((gpio_num_t)msg.gpio,GPIO_FLOATING);
                            break;
                        case MODE_INPUT_PULLUP:
                            gpio_set_direction((gpio_num_t)msg.gpio,GPIO_MODE_INPUT);
                            gpio_set_pull_mode((gpio_num_t)msg.gpio,GPIO_PULLUP_ONLY);
                            break;
                        case MODE_INPUT_PULLDOWN:
                            gpio_set_direction((gpio_num_t)msg.gpio,GPIO_MODE_INPUT);
                            gpio_set_pull_mode((gpio_num_t)msg.gpio,GPIO_PULLDOWN_ONLY);
                            break;
                        case MODE_OUTPUT:
                            gpio_set_direction((gpio_num_t)msg.gpio,GPIO_MODE_OUTPUT);
                            break;
                        case MODE_OUTPUT_OPEN_DRAIN:
                            gpio_set_direction((gpio_num_t)msg.gpio,GPIO_MODE_OUTPUT_OD);
                            break;
                    }
                    
                }
            }
            break;
            case CMD_MAC_ADDRESS: {
                st_mac_address_message_t msg;
                buffer_read_cursor_t read_cur = {length,(const uint8_t*)ptr};
                if(-1<interface_read_st_mac_address_message(&msg,on_read_buffer,&read_cur)) {
                    puts("MAC Address requested");
                    buffer_write_cursor_t write_cur = {INTERFACE_MAX_SIZE,msg_buffer};
                    st_mac_address_response_message_t resp;
                    memset(&resp,0,sizeof(resp));
                    esp_read_mac(resp.address,ESP_MAC_BASE);
                    interface_write_st_mac_address_response_message(&resp,on_write_buffer,&write_cur);
                    serial_put_frame(CMD_MAC_ADDRESS_RESPONSE,msg_buffer,INTERFACE_ST_MAC_ADDRESS_RESPONSE_MESSAGE_SIZE);
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
