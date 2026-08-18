#include "rg_battery.h"

#include <math.h>

float rg_battery_calculate_level(float millivolts, rg_battery_calibration_t calibration)
{
    if (!isfinite(calibration.empty_mv) || !isfinite(calibration.full_mv) ||
        !(calibration.empty_mv > 0.f) || !(calibration.full_mv > calibration.empty_mv))
        return 0.f;

    float level = (millivolts - calibration.empty_mv) * 100.f /
                  (calibration.full_mv - calibration.empty_mv);
    if (!isfinite(level))
        return 0.f;
    if (level < 0.f)
        return 0.f;
    if (level > 100.f)
        return 100.f;
    return level;
}

bool rg_battery_hysteresis(bool active, float value, float enter_threshold, float exit_threshold)
{
    if (!(exit_threshold >= enter_threshold))
        return false;
    if (active)
        return value < exit_threshold;
    return value <= enter_threshold;
}

bool rg_battery_alert_should_prompt(bool critical_latched, bool prompt_pending,
                                    bool prompt_open, int64_t now, int64_t retry_at)
{
    return critical_latched && !prompt_pending && !prompt_open && now >= retry_at;
}
