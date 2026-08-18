#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "rg_audio_tone.h"

static void test_tone_lengths_are_short(void)
{
    size_t low = rg_audio_tone_length_samples(RG_AUDIO_TONE_LOW, 22050);
    size_t critical = rg_audio_tone_length_samples(RG_AUDIO_TONE_CRITICAL, 22050);
    assert(low == 2646);
    assert(critical == 3969);
}

static void test_low_tone_produces_bounded_audio(void)
{
    rg_audio_frame_t frames[64] = {0};
    rg_audio_tone_render(RG_AUDIO_TONE_LOW, 22050, 0, frames, 64);
    int nonzero = 0;
    for (size_t i = 0; i < 64; ++i)
    {
        assert(frames[i].left >= -6000 && frames[i].left <= 6000);
        assert(frames[i].right == frames[i].left);
        nonzero += frames[i].left != 0;
    }
    assert(nonzero > 0);
}

static void test_critical_tone_contains_separator_silence(void)
{
    rg_audio_frame_t frames[32] = {0};
    size_t separator = (size_t)(70 * 22050 / 1000);
    rg_audio_tone_render(RG_AUDIO_TONE_CRITICAL, 22050, separator, frames, 32);
    for (size_t i = 0; i < 32; ++i)
        assert(frames[i].left == 0 && frames[i].right == 0);
}

int main(void)
{
    test_tone_lengths_are_short();
    test_low_tone_produces_bounded_audio();
    test_critical_tone_contains_separator_silence();
    puts("audio tone tests passed");
    return 0;
}
