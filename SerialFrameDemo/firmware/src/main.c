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
#include "serial.h"
#include "frame.h"
#include "interface_buffers.h"
static frame_handle_t frame_handle = NULL;
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
int serial_read(void* state) {
    return serial_getc();
}
int serial_write(uint8_t value, void* state) {
    serial_putc(value);
    return 1;
}
void app_main() {
    serial_init(INTERFACE_MAX_SIZE+16);
    frame_handle = frame_create(INTERFACE_MAX_SIZE,serial_read,NULL,serial_write,NULL);
    TaskHandle_t loop_handle;
    xTaskCreate(loop_task,"loop_task",8192,NULL,1,&loop_handle);
}
typedef struct {
    uint8_t* ptr;
    size_t remaining;
} buffer_write_cursor_t;
typedef struct {
    const uint8_t* ptr;
    size_t remaining;
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
    void* ptr;
    size_t length;
    int res = frame_get(frame_handle,&ptr,&length);
    if(res>0) {
        buffer_read_cursor_t read_cur = {(const uint8_t*)ptr,length};
        // the following is only used when we need to respond
        buffer_write_cursor_t write_cur = {msg_buffer,INTERFACE_MAX_SIZE};
        switch((st_message_command_t)res) {
            case CMD_ESP_IDF_VERSION: {
                st_esp_idf_version_message_t msg;
                if(-1<st_esp_idf_version_message_read(&msg,on_read_buffer,&read_cur)) {
                    puts("ESP-IDF version requested");
                    st_esp_idf_version_response_message_t resp;
                    strcpy(resp.version,"ESP-IDF v");
                    strcat(resp.version,esp_get_idf_version());
                    resp.major = ESP_IDF_VERSION_MAJOR;
                    resp.minor = ESP_IDF_VERSION_MINOR;
                    resp.patch = ESP_IDF_VERSION_PATCH;
                    int count = st_esp_idf_version_response_message_write(&resp,on_write_buffer,&write_cur);
                    frame_put(frame_handle,CMD_ESP_IDF_VERSION_RESPONSE,msg_buffer,count);
                }
            }
            break;
            case CMD_RNG: {
                st_rng_message_t msg;
                if(-1<st_rng_message_read(&msg,on_read_buffer,&read_cur)) {
                    puts("RNG generation requested");
                    st_rng_response_message_t resp;
                    resp.value = esp_random();
                    int count = st_rng_response_message_write(&resp,on_write_buffer,&write_cur);
                    frame_put(frame_handle,CMD_RNG_RESPONSE,msg_buffer,count);
                }
            }
            break;
            case CMD_GPIO_GET: {
                st_gpio_get_message_t msg;
                uint64_t result = 0;
                if(-1<st_gpio_get_message_read(&msg,on_read_buffer,&read_cur)) {
                    for(int i = 0; i<64;++i) {
                        if(0!=(msg.mask & (((uint64_t)1)<<i))) {
                            printf("GPIO get request for %d\n",(int)i);
                            if(gpio_get_level((gpio_num_t)i)) {
                                result |= (((uint64_t)1)<<i);
                            }
                        }
                    }
                    st_gpio_get_response_message_t resp;
                    resp.values = result;
                    int count = st_gpio_get_response_message_write(&resp,on_write_buffer,&write_cur);
                    frame_put(frame_handle,CMD_GPIO_GET_RESPONSE,msg_buffer,count);
                }
            }
            break;
            case CMD_GPIO_SET: {
                st_gpio_set_message_t msg;
                if(-1<st_gpio_set_message_read(&msg,on_read_buffer,&read_cur)) {
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
                if(-1<st_gpio_mode_message_read(&msg,on_read_buffer,&read_cur)) {
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
                if(-1<st_mac_address_message_read(&msg,on_read_buffer,&read_cur)) {
                    puts("MAC Address requested");
                    st_mac_address_response_message_t resp;
                    memset(&resp,0,sizeof(resp));
                    esp_read_mac(resp.address,ESP_MAC_BASE);
                    int count = st_mac_address_response_message_write(&resp,on_write_buffer,&write_cur);
                    frame_put(frame_handle, CMD_MAC_ADDRESS_RESPONSE,msg_buffer,count);
                }
            }
            break;
            default: {
                printf("Unknown command received %d\n",res);
            }
            break;
        }
    }
}
