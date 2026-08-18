#pragma once

#include <stddef.h>

#include "rg_audio.h"

size_t rg_audio_tone_length_samples(rg_audio_tone_t tone, int sample_rate);
void rg_audio_tone_render(rg_audio_tone_t tone, int sample_rate, size_t offset,
                          rg_audio_frame_t *frames, size_t count);
