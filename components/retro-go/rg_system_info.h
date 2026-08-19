#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct
{
    size_t flash_size;
    size_t psram_size;
    int64_t storage_total;
    int64_t storage_free;
    bool storage_ready;
} rg_system_info_t;

void rg_system_info_get(rg_system_info_t *info);
void rg_system_info_format_size(char *dest, size_t dest_size, uint64_t bytes);
