#include "rg_utils.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(condition)                                                        \
    do                                                                          \
    {                                                                           \
        if (!(condition))                                                       \
        {                                                                       \
            fprintf(stderr, "%s:%d: check failed: %s\n", __FILE__, __LINE__,  \
                    #condition);                                                \
            failures++;                                                         \
        }                                                                       \
    } while (0)

static void test_decode(void)
{
    const char ascii[] = "A";
    const char *ptr = ascii;
    CHECK(rg_utf8_decode(&ptr) == 'A');
    CHECK(ptr == ascii + 1);

    const char two_byte[] = "\xC2\xA2";
    ptr = two_byte;
    CHECK(rg_utf8_decode(&ptr) == 0x00A2);
    CHECK(ptr == two_byte + 2);

    const char chinese[] = "中文游戏";
    const int expected[] = {0x4E2D, 0x6587, 0x6E38, 0x620F};
    ptr = chinese;
    for (size_t i = 0; i < sizeof(expected) / sizeof(expected[0]); ++i)
        CHECK(rg_utf8_decode(&ptr) == expected[i]);
    CHECK(*ptr == '\0');

    const char four_byte[] = "\xF0\x9F\x98\x80";
    ptr = four_byte;
    CHECK(rg_utf8_decode(&ptr) == 0x1F600);
    CHECK(ptr == four_byte + 4);

    const char invalid[] = {'\xE4', 'A', '\0'};
    ptr = invalid;
    CHECK(rg_utf8_decode(&ptr) == -1);
    CHECK(ptr == invalid + 1);
    CHECK(rg_utf8_decode(&ptr) == 'A');

    CHECK(rg_utf8_decode(NULL) == -1);
}

static void test_decode_rejects_invalid_scalars(void)
{
    static const char overlong_two[] = "\xC0\x80";
    static const char overlong_three[] = "\xE0\x9F\xBF";
    static const char overlong_four[] = "\xF0\x8F\xBF\xBF";
    static const char surrogate[] = "\xED\xA0\x80";
    static const char above_unicode_max[] = "\xF4\x90\x80\x80";
    static const char invalid_f5[] = "\xF5\x80\x80\x80";
    static const char invalid_f6[] = "\xF6\x80\x80\x80";
    static const char invalid_f7[] = "\xF7\x80\x80\x80";
    const char *invalid_sequences[] = {
        overlong_two,
        overlong_three,
        overlong_four,
        surrogate,
        above_unicode_max,
        invalid_f5,
        invalid_f6,
        invalid_f7,
    };

    for (size_t i = 0; i < sizeof(invalid_sequences) / sizeof(invalid_sequences[0]); ++i)
    {
        const char *ptr = invalid_sequences[i];
        CHECK(rg_utf8_decode(&ptr) == -1);
        CHECK(ptr == invalid_sequences[i] + 1);
    }
}

static void test_decode_accepts_valid_boundaries(void)
{
    struct boundary_case
    {
        const char *bytes;
        int codepoint;
        size_t width;
    };
    const struct boundary_case boundaries[] = {
        {"\xE0\xA0\x80", 0x0800, 3},
        {"\xED\x9F\xBF", 0xD7FF, 3},
        {"\xEE\x80\x80", 0xE000, 3},
        {"\xF0\x90\x80\x80", 0x10000, 4},
        {"\xF4\x8F\xBF\xBF", 0x10FFFF, 4},
    };

    for (size_t i = 0; i < sizeof(boundaries) / sizeof(boundaries[0]); ++i)
    {
        const char *ptr = boundaries[i].bytes;
        CHECK(rg_utf8_decode(&ptr) == boundaries[i].codepoint);
        CHECK(ptr == boundaries[i].bytes + boundaries[i].width);
    }
}

static void test_encode(void)
{
    char output[5] = {0};

    CHECK(rg_utf8_encode(output, 'A') == 1);
    CHECK(memcmp(output, "A", 1) == 0);

    memset(output, 0, sizeof(output));
    CHECK(rg_utf8_encode(output, 0x00A2) == 2);
    CHECK(memcmp(output, "\xC2\xA2", 2) == 0);

    memset(output, 0, sizeof(output));
    CHECK(rg_utf8_encode(output, 0x4E2D) == 3);
    CHECK(memcmp(output, "中", 3) == 0);

    memset(output, 0, sizeof(output));
    CHECK(rg_utf8_encode(output, 0x1F600) == 4);
    CHECK(memcmp(output, "\xF0\x9F\x98\x80", 4) == 0);

    memset(output, 'X', sizeof(output));
    CHECK(rg_utf8_encode(output, 0x110000) == 0);
    CHECK(output[0] == 'X');

    memset(output, 'X', sizeof(output));
    CHECK(rg_utf8_encode(output, -1) == 0);
    CHECK(memcmp(output, "XXXXX", sizeof(output)) == 0);

    memset(output, 'X', sizeof(output));
    CHECK(rg_utf8_encode(output, 0xD800) == 0);
    CHECK(memcmp(output, "XXXXX", sizeof(output)) == 0);

    memset(output, 'X', sizeof(output));
    CHECK(rg_utf8_encode(output, 0xDFFF) == 0);
    CHECK(memcmp(output, "XXXXX", sizeof(output)) == 0);
}

static void test_strlen(void)
{
    const char invalid[] = {'\xE4', 'A', '\0'};

    CHECK(rg_utf8_strlen("ASCII") == 5);
    CHECK(rg_utf8_strlen("中文游戏") == 4);
    CHECK(rg_utf8_strlen(invalid) == 1);
    CHECK(rg_utf8_strlen("") == 0);
    CHECK(rg_utf8_strlen(NULL) == 0);
}

static void test_copy_complete_strings(void)
{
    char ascii[16] = {0};
    CHECK(rg_utf8_copy(ascii, sizeof(ascii), "Retro-Go") == 8);
    CHECK(strcmp(ascii, "Retro-Go") == 0);

    char chinese[32] = {0};
    CHECK(rg_utf8_copy(chinese, sizeof(chinese), "中文游戏") == 12);
    CHECK(strcmp(chinese, "中文游戏") == 0);

    char exact[sizeof("中文游戏")];
    memset(exact, 'X', sizeof(exact));
    CHECK(rg_utf8_copy(exact, sizeof(exact), "中文游戏") == 12);
    CHECK(memcmp(exact, "中文游戏", sizeof(exact)) == 0);
    CHECK(exact[sizeof(exact) - 1] == '\0');
}

static void test_copy_truncation(void)
{
    char before_chinese[5] = {'X', 'X', 'X', 'X', 'G'};
    CHECK(rg_utf8_copy(before_chinese, 4, "A中文") == 1);
    CHECK(strcmp(before_chinese, "A") == 0);
    CHECK(before_chinese[4] == 'G');

    char after_chinese[5] = {'X', 'X', 'X', 'X', 'G'};
    CHECK(rg_utf8_copy(after_chinese, 4, "中A") == 3);
    CHECK(memcmp(after_chinese, "中\0", 4) == 0);
    CHECK(after_chinese[4] == 'G');
}

static void test_copy_small_destinations(void)
{
    char zero_size = 'G';
    CHECK(rg_utf8_copy(&zero_size, 0, "A") == 0);
    CHECK(zero_size == 'G');

    char one_byte[2] = {'X', 'G'};
    CHECK(rg_utf8_copy(one_byte, 1, "A") == 0);
    CHECK(one_byte[0] == '\0');
    CHECK(one_byte[1] == 'G');

    char empty[2] = {'X', 'G'};
    CHECK(rg_utf8_copy(empty, sizeof(empty), "") == 0);
    CHECK(empty[0] == '\0');
    CHECK(empty[1] == 'G');
}

static void test_copy_invalid_utf8(void)
{
    const char invalid[] = {'A', '\xE4', 'B', '\0'};
    char output[sizeof(invalid) + 1];
    memset(output, 'G', sizeof(output));

    CHECK(rg_utf8_copy(output, sizeof(output), invalid) == 1);
    CHECK(strcmp(output, "A") == 0);
    CHECK(output[sizeof(invalid)] == 'G');

    const char invalid_at_start[] = {'\xE4', 'A', '\0'};
    char one_byte_payload[2] = {'X', 'G'};
    CHECK(rg_utf8_copy(one_byte_payload, sizeof(one_byte_payload),
                       invalid_at_start) == 0);
    CHECK(one_byte_payload[0] == '\0');
    CHECK(one_byte_payload[1] == 'G');
}

static void test_copy_rejects_invalid_scalars(void)
{
    static const char overlong_two[] = "\xC0\x80";
    static const char overlong_three[] = "\xE0\x9F\xBF";
    static const char overlong_four[] = "\xF0\x8F\xBF\xBF";
    static const char surrogate[] = "\xED\xA0\x80";
    static const char above_unicode_max[] = "\xF4\x90\x80\x80";
    static const char invalid_f5[] = "\xF5\x80\x80\x80";
    static const char invalid_f6[] = "\xF6\x80\x80\x80";
    static const char invalid_f7[] = "\xF7\x80\x80\x80";
    const char *invalid_sequences[] = {
        overlong_two,
        overlong_three,
        overlong_four,
        surrogate,
        above_unicode_max,
        invalid_f5,
        invalid_f6,
        invalid_f7,
    };

    for (size_t i = 0; i < sizeof(invalid_sequences) / sizeof(invalid_sequences[0]); ++i)
    {
        char output[8];
        memset(output, 'G', sizeof(output));

        CHECK(rg_utf8_copy(output, sizeof(output), invalid_sequences[i]) == 0);
        CHECK(output[0] == '\0');
        CHECK(output[1] == 'G');
    }
}

static void test_decode_null_input(void)
{
    const char *ptr = NULL;
    CHECK(rg_utf8_decode(&ptr) == -1);
    CHECK(ptr == NULL);
}

int main(void)
{
    test_decode();
    test_decode_rejects_invalid_scalars();
    test_decode_accepts_valid_boundaries();
    test_encode();
    test_strlen();
    test_copy_complete_strings();
    test_copy_truncation();
    test_copy_small_destinations();
    test_copy_invalid_utf8();
    test_copy_rejects_invalid_scalars();
    test_decode_null_input();

    if (failures != 0)
    {
        fprintf(stderr, "UTF-8 tests failed: %d\n", failures);
        return 1;
    }

    puts("UTF-8 tests passed");
    return 0;
}
