#pragma once

#include <stdbool.h>

typedef struct
{
    int version;
    int language;
    int font;
} rg_gui_defaults_t;

bool rg_gui_defaults_apply(rg_gui_defaults_t *settings, const rg_gui_defaults_t *defaults);
