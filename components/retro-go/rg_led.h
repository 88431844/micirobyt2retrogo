#pragma once

#include <stdint.h>

typedef enum
{
    RG_LED_PATTERN_OFF = 0,
    RG_LED_PATTERN_ACTIVITY,
    RG_LED_PATTERN_SOLID,
    RG_LED_PATTERN_BREATHE,
    RG_LED_PATTERN_SLOW,
    RG_LED_PATTERN_FAST,
    RG_LED_PATTERN_HEARTBEAT,
    RG_LED_PATTERN_BREATHE_SLOW,
    RG_LED_PATTERN_COUNT,
} rg_led_pattern_t;

uint8_t rg_led_pattern_brightness(rg_led_pattern_t pattern, int64_t elapsed_ms, float load_percent);
