#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "rg_led.h"

static void test_fixed_patterns(void)
{
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_OFF, 0, 0.f) == 0);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_SOLID, 0, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_SOLID, 500, 100.f) == 255);
}

static void test_breathe_pattern_has_low_and_high_points(void)
{
    uint8_t low = rg_led_pattern_brightness(RG_LED_PATTERN_BREATHE, 0, 0.f);
    uint8_t high = rg_led_pattern_brightness(RG_LED_PATTERN_BREATHE, 1000, 0.f);
    assert(low < 32);
    assert(high > 220);
}

static void test_slow_breathe_pattern_has_longer_cycle(void)
{
    uint8_t start = rg_led_pattern_brightness(RG_LED_PATTERN_BREATHE_SLOW, 0, 0.f);
    uint8_t midpoint = rg_led_pattern_brightness(RG_LED_PATTERN_BREATHE_SLOW, 1000, 0.f);
    uint8_t peak = rg_led_pattern_brightness(RG_LED_PATTERN_BREATHE_SLOW, 2000, 0.f);

    assert(start == 0);
    assert(midpoint > start && midpoint < peak);
    assert(peak == 255);
}

static void test_flash_patterns_have_expected_boundaries(void)
{
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_SLOW, 0, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_SLOW, 600, 0.f) == 0);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_FAST, 0, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_FAST, 200, 0.f) == 0);
}

static void test_heartbeat_has_two_pulses(void)
{
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_HEARTBEAT, 0, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_HEARTBEAT, 250, 0.f) == 0);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_HEARTBEAT, 450, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_HEARTBEAT, 700, 0.f) == 0);
}

static void test_activity_period_shortens_with_load(void)
{
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_ACTIVITY, 0, 0.f) == 255);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_ACTIVITY, 100, 0.f) == 0);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_ACTIVITY, 200, 0.f) == 0);
    assert(rg_led_pattern_brightness(RG_LED_PATTERN_ACTIVITY, 200, 100.f) == 255);
}

int main(void)
{
    test_fixed_patterns();
    test_breathe_pattern_has_low_and_high_points();
    test_slow_breathe_pattern_has_longer_cycle();
    test_flash_patterns_have_expected_boundaries();
    test_heartbeat_has_two_pulses();
    test_activity_period_shortens_with_load();
    puts("led tests passed");
    return 0;
}
