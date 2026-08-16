#include <stdbool.h>
#include <stdio.h>

#include "rg_gui_defaults.h"

static int failures;

#define CHECK(condition)                                                        \
    do                                                                          \
    {                                                                           \
        if (!(condition))                                                       \
        {                                                                       \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
            failures++;                                                         \
        }                                                                       \
    } while (0)

static void test_legacy_settings_are_migrated_once(void)
{
    rg_gui_defaults_t settings = {
        .version = 0,
        .language = 0,
        .font = 0,
    };
    const rg_gui_defaults_t defaults = {
        .version = 1,
        .language = 3,
        .font = 3,
    };

    CHECK(rg_gui_defaults_apply(&settings, &defaults));
    CHECK(settings.version == 1);
    CHECK(settings.language == 3);
    CHECK(settings.font == 3);

    settings.language = 0;
    settings.font = 5;

    CHECK(!rg_gui_defaults_apply(&settings, &defaults));
    CHECK(settings.language == 0);
    CHECK(settings.font == 5);
}

static void test_targets_without_a_migration_keep_existing_settings(void)
{
    rg_gui_defaults_t settings = {
        .version = 0,
        .language = 1,
        .font = 6,
    };
    const rg_gui_defaults_t defaults = {
        .version = 0,
        .language = 0,
        .font = 5,
    };

    CHECK(!rg_gui_defaults_apply(&settings, &defaults));
    CHECK(settings.version == 0);
    CHECK(settings.language == 1);
    CHECK(settings.font == 6);
}

int main(void)
{
    test_legacy_settings_are_migrated_once();
    test_targets_without_a_migration_keep_existing_settings();

    if (failures)
        return 1;

    puts("GUI defaults migration tests passed");
    return 0;
}
