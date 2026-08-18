#include "rg_audio_tone.h"

#include <stdint.h>

static size_t milliseconds_to_samples(int milliseconds, int sample_rate)
{
    return (size_t)((int64_t)milliseconds * sample_rate / 1000);
}

size_t rg_audio_tone_length_samples(rg_audio_tone_t tone, int sample_rate)
{
    if (sample_rate <= 0)
        return 0;
    switch (tone)
    {
    case RG_AUDIO_TONE_LOW:
        return milliseconds_to_samples(120, sample_rate);
    case RG_AUDIO_TONE_CRITICAL:
        return milliseconds_to_samples(180, sample_rate);
    default:
        return 0;
    }
}

static int tone_frequency(rg_audio_tone_t tone, size_t sample, int sample_rate)
{
    size_t first = milliseconds_to_samples(60, sample_rate);
    if (tone == RG_AUDIO_TONE_LOW)
        return sample < first ? 880 : 660;
    if (tone == RG_AUDIO_TONE_CRITICAL)
    {
        size_t separator = milliseconds_to_samples(90, sample_rate);
        if (sample < first)
            return 1200;
        if (sample < separator)
            return 0;
        return 880;
    }
    return 0;
}

void rg_audio_tone_render(rg_audio_tone_t tone, int sample_rate, size_t offset,
                          rg_audio_frame_t *frames, size_t count)
{
    if (!frames || sample_rate <= 0)
        return;

    size_t length = rg_audio_tone_length_samples(tone, sample_rate);
    for (size_t i = 0; i < count; ++i)
    {
        size_t sample = offset + i;
        int frequency = sample < length ? tone_frequency(tone, sample, sample_rate) : 0;
        int16_t value = 0;
        if (frequency > 0)
        {
            uint64_t phase = ((uint64_t)sample * (uint64_t)frequency) % (uint64_t)sample_rate;
            value = phase < (uint64_t)sample_rate / 2 ? 6000 : -6000;
        }
        frames[i] = (rg_audio_frame_t){value, value};
    }
}
