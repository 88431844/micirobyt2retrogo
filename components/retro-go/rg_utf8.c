#include "rg_utils.h"

#include <string.h>

int rg_utf8_decode(const char **ptr)
{
    if (!ptr || !*ptr)
        return -1;

    const unsigned char *input = (const unsigned char *)*ptr;
    int first_byte = input[0];
    int codepoint = 0;
    size_t extra_bytes = 0;

    *ptr += 1; // Always consume the first byte

    if ((first_byte & 0x80) == 0x00)
    {
        return first_byte;
    }
    else if (first_byte >= 0xC2 && first_byte <= 0xDF)
    {
        codepoint = first_byte & 0x1F;
        extra_bytes = 1;
    }
    else if (first_byte >= 0xE0 && first_byte <= 0xEF)
    {
        codepoint = first_byte & 0x0F;
        extra_bytes = 2;
    }
    else if (first_byte >= 0xF0 && first_byte <= 0xF4)
    {
        codepoint = first_byte & 0x07;
        extra_bytes = 3;
    }
    else // Invalid prefix
    {
        return -1; // first_byte
    }

    for (size_t i = 0; i < extra_bytes; ++i)
    {
        int next_byte = input[i + 1];
        if ((next_byte & 0xC0) != 0x80)
        {
            return -1; // first_byte
        }
        codepoint <<= 6;
        codepoint += next_byte & 0x3F;
    }

    if ((extra_bytes == 2 && codepoint < 0x800) ||
        (extra_bytes == 3 && codepoint < 0x10000) ||
        (codepoint >= 0xD800 && codepoint <= 0xDFFF) ||
        codepoint > 0x10FFFF)
    {
        return -1;
    }

    *ptr += extra_bytes;
    return codepoint;
}

size_t rg_utf8_encode(char *output, int codepoint)
{
    if (codepoint < 0 ||
        (codepoint >= 0xD800 && codepoint <= 0xDFFF) ||
        codepoint > 0x10FFFF)
    {
        return 0;
    }

    if (codepoint <= 0x7F) // 1 byte
    {
        output[0] = codepoint & 0xFF;
        return 1;
    }
    else if (codepoint <= 0x7FF) // 2 bytes
    {
        output[0] = 0xC0 | ((codepoint >> 6) & 0x1F);
        output[1] = 0x80 | (codepoint & 0x3F);
        return 2;
    }
    else if (codepoint <= 0xFFFF) // 3 bytes
    {
        output[0] = 0xE0 | ((codepoint >> 12) & 0x0F);
        output[1] = 0x80 | ((codepoint >> 6) & 0x3F);
        output[2] = 0x80 | (codepoint & 0x3F);
        return 3;
    }
    else // 4 bytes
    {
        output[0] = 0xF0 | ((codepoint >> 18) & 0x07);
        output[1] = 0x80 | ((codepoint >> 12) & 0x3F);
        output[2] = 0x80 | ((codepoint >> 6) & 0x3F);
        output[3] = 0x80 | (codepoint & 0x3F);
        return 4;
    }
}

size_t rg_utf8_strlen(const char *str)
{
    if (!str)
        return 0;

    size_t length = 0;
    while (*str)
    {
        if (rg_utf8_decode(&str) > 0)
            length++;
    }
    return length;
}

size_t rg_utf8_copy(char *dst, size_t dst_size, const char *src)
{
    if (!dst || dst_size == 0)
        return 0;

    size_t copied = 0;
    dst[0] = '\0';

    while (src && *src)
    {
        const char *next = src;
        if (rg_utf8_decode(&next) < 0)
            break;

        size_t codepoint_size = (size_t)(next - src);

        if (codepoint_size > dst_size - copied - 1)
            break;

        memcpy(dst + copied, src, codepoint_size);
        copied += codepoint_size;
        src = next;
    }

    dst[copied] = '\0';
    return copied;
}
