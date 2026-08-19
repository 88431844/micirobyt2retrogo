#include "rg_led.h"

#include <stddef.h>

static uint8_t pulse(int64_t phase, int64_t on_ms)
{
    return phase < on_ms ? 255 : 0;
}

uint8_t rg_led_pattern_brightness(rg_led_pattern_t pattern, int64_t elapsed_ms, float load_percent)
{
    if (elapsed_ms < 0)
        elapsed_ms = 0;
    if (load_percent < 0.f)
        load_percent = 0.f;
    if (load_percent > 100.f)
        load_percent = 100.f;

    switch (pattern)
    {
    case RG_LED_PATTERN_OFF:
        return 0;
    case RG_LED_PATTERN_SOLID:
        return 255;
    case RG_LED_PATTERN_BREATHE:
    {
        int64_t phase = elapsed_ms % 2000;
        if (phase <= 1000)
            return (uint8_t)(phase * 255 / 1000);
        return (uint8_t)((2000 - phase) * 255 / 1000);
    }
    case RG_LED_PATTERN_SLOW:
        return pulse(elapsed_ms % 1000, 500);
    case RG_LED_PATTERN_FAST:
        return pulse(elapsed_ms % 400, 200);
    case RG_LED_PATTERN_HEARTBEAT:
    {
        int64_t phase = elapsed_ms % 800;
        return (phase < 150 || (phase >= 350 && phase < 500)) ? 255 : 0;
    }
    case RG_LED_PATTERN_BREATHE_SLOW:
    {
        int64_t phase = elapsed_ms % 4000;
        if (phase <= 2000)
            return (uint8_t)(phase * 255 / 2000);
        return (uint8_t)((4000 - phase) * 255 / 2000);
    }
    case RG_LED_PATTERN_ACTIVITY:
    default:
    {
        int64_t period = 2000 - (int64_t)(load_percent * 18.f);
        if (period < 200)
            period = 200;
        return pulse(elapsed_ms % period, 100);
    }
    }
}
