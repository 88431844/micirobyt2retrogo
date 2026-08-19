#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "rg_system_info.h"

static void test_formats_binary_sizes(void)
{
    char value[32];

    rg_system_info_format_size(value, sizeof(value), 0);
    assert(strcmp(value, "0 B") == 0);

    rg_system_info_format_size(value, sizeof(value), 1024);
    assert(strcmp(value, "1.0 KB") == 0);

    rg_system_info_format_size(value, sizeof(value), 1536);
    assert(strcmp(value, "1.5 KB") == 0);

    rg_system_info_format_size(value, sizeof(value), 4 * 1024 * 1024);
    assert(strcmp(value, "4.0 MB") == 0);
}

int main(void)
{
    test_formats_binary_sizes();
    puts("system info tests passed");
    return 0;
}
