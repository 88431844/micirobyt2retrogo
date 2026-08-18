#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

#include "rg_battery.h"

static void test_level_is_clamped_and_interpolated(void)
{
    const rg_battery_calibration_t calibration = {3500.f, 4200.f};

    assert(rg_battery_calculate_level(3400.f, calibration) == 0.f);
    assert(rg_battery_calculate_level(3500.f, calibration) == 0.f);
    assert(rg_battery_calculate_level(3850.f, calibration) > 49.9f);
    assert(rg_battery_calculate_level(3850.f, calibration) < 50.1f);
    assert(rg_battery_calculate_level(4200.f, calibration) == 100.f);
    assert(rg_battery_calculate_level(4300.f, calibration) == 100.f);
}

static void test_invalid_calibration_uses_zero_level(void)
{
    assert(rg_battery_calculate_level(3800.f, (rg_battery_calibration_t){4200.f, 3500.f}) == 0.f);
    assert(rg_battery_calculate_level(3800.f, (rg_battery_calibration_t){0.f, 4200.f}) == 0.f);
}

static void test_hysteresis_prevents_low_battery_flicker(void)
{
    assert(rg_battery_hysteresis(false, 14.f, 15.f, 20.f));
    assert(rg_battery_hysteresis(true, 18.f, 15.f, 20.f));
    assert(!rg_battery_hysteresis(true, 20.f, 15.f, 20.f));
    assert(!rg_battery_hysteresis(false, 16.f, 15.f, 20.f));
}

static void test_critical_prompt_retry_gate(void)
{
    assert(rg_battery_alert_should_prompt(true, false, false, 0, 0));
    assert(!rg_battery_alert_should_prompt(true, true, false, 1, 0));
    assert(!rg_battery_alert_should_prompt(true, false, true, 1, 0));
    assert(!rg_battery_alert_should_prompt(true, false, false, 59, 60));
    assert(rg_battery_alert_should_prompt(true, false, false, 60, 60));
    assert(!rg_battery_alert_should_prompt(false, false, false, 100, 0));
}

int main(void)
{
    test_level_is_clamped_and_interpolated();
    test_invalid_calibration_uses_zero_level();
    test_hysteresis_prevents_low_battery_flicker();
    test_critical_prompt_retry_gate();
    puts("battery tests passed");
    return 0;
}
