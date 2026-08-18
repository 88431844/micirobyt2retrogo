#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    float empty_mv;
    float full_mv;
} rg_battery_calibration_t;

float rg_battery_calculate_level(float millivolts, rg_battery_calibration_t calibration);
bool rg_battery_hysteresis(bool active, float value, float enter_threshold, float exit_threshold);
bool rg_battery_alert_should_prompt(bool critical_latched, bool prompt_pending,
                                    bool prompt_open, int64_t now, int64_t retry_at);
