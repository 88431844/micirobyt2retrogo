#include "rg_gui_defaults.h"

bool rg_gui_defaults_apply(rg_gui_defaults_t *settings, const rg_gui_defaults_t *defaults)
{
    if (!settings || !defaults || defaults->version <= 0 || settings->version >= defaults->version)
        return false;

    *settings = *defaults;
    return true;
}
