#include "rg_system_info.h"

#include <string.h>

#include "config.h"
#include "rg_storage.h"

#ifdef ESP_PLATFORM
#include <esp_heap_caps.h>
#include <esp_spi_flash.h>
#endif

void rg_system_info_get(rg_system_info_t *info)
{
    if (!info)
        return;

    memset(info, 0, sizeof(*info));
    info->storage_total = -1;
    info->storage_free = -1;

#ifdef ESP_PLATFORM
    info->flash_size = spi_flash_get_chip_size();
    info->psram_size = heap_caps_get_total_size(MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
#endif

    info->storage_ready = rg_storage_ready();
    if (info->storage_ready)
    {
        info->storage_total = rg_storage_get_total_space(RG_STORAGE_ROOT);
        info->storage_free = rg_storage_get_free_space(RG_STORAGE_ROOT);
    }
}
