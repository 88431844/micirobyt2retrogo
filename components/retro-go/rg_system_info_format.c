#include "rg_system_info.h"

#include <stdio.h>

void rg_system_info_format_size(char *dest, size_t dest_size, uint64_t bytes)
{
    static const char *units[] = {"B", "KB", "MB", "GB"};
    size_t unit = 0;
    uint64_t divisor = 1;

    if (dest_size == 0)
        return;

    while (unit < 3 && bytes >= divisor * 1024)
    {
        divisor *= 1024;
        unit++;
    }

    if (unit == 0)
        snprintf(dest, dest_size, "%llu B", (unsigned long long)bytes);
    else
        snprintf(dest, dest_size, "%llu.%llu %s",
                 (unsigned long long)(bytes / divisor),
                 (unsigned long long)((bytes % divisor) * 10 / divisor),
                 units[unit]);
}
