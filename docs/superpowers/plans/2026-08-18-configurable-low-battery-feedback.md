# Configurable Low-Battery Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-configurable LED patterns, short low-battery tone alerts, and two-stage low-battery screen handling to the MicroByte Retro-Go target.

**Architecture:** Keep battery sampling and threshold detection in the existing input/system monitor paths, but move LED waveform calculation into a pure `rg_led` module. Persist integer enum settings in the global namespace; the monitor task only raises edge-triggered events, while the main thread owns GUI, save-state, and sleep operations.

**Tech Stack:** C99, ESP-IDF GPIO/LEDC/I2S drivers, existing Retro-Go GUI/settings/audio APIs, host C tests and Python localization tests.

---

### Task 1: Add the pure LED pattern engine

**Files:**
- Create: `components/retro-go/rg_led.h`
- Create: `components/retro-go/rg_led.c`
- Create: `tests/test_led.c`
- Modify: `tests/run_host_tests.sh`

- [ ] **Step 1: Write failing host tests** for OFF, SOLID, BREATHE, SLOW, FAST, HEARTBEAT, and load-based ACTIVITY brightness at deterministic timestamps.
- [ ] **Step 2: Run `./tests/run_host_tests.sh led`** and verify compilation fails because the new API is absent.
- [ ] **Step 3: Implement `rg_led_pattern_brightness(rg_led_pattern_t pattern, int64_t elapsed_ms, float load_percent)`** returning 0..255, with clamped load input and deterministic 100ms/1000ms periods.
- [ ] **Step 4: Run the LED tests** and verify all pattern boundary assertions pass under `-Wall -Wextra -Werror -pedantic`.
- [ ] **Step 5: Commit** with `feat: add configurable led pattern engine`.

### Task 2: Add persistent LED and sound settings

**Files:**
- Modify: `components/retro-go/rg_system.h`
- Modify: `components/retro-go/rg_system.c`
- Modify: `components/retro-go/rg_gui.c`
- Modify: `components/retro-go/translations.h`
- Modify: `tests/test_led.c`

- [ ] **Step 1: Add settings constants and validated getters/setters** for `LedSystemPattern`, `LedLowPattern`, and `LowBatterySound`; missing or out-of-range values must return defaults.
- [ ] **Step 2: Replace the current boolean-only LED submenu** with pattern cycling for system activity and low battery, retaining the disk-activity toggle.
- [ ] **Step 3: Add translated labels** for all pattern names and the low-battery sound choices, then run localization tests to catch missing catalog keys and format mismatches.
- [ ] **Step 4: Add host assertions** for defaults and invalid enum fallback, then run `./tests/run_host_tests.sh all`.
- [ ] **Step 5: Commit** with `feat: expose led and battery alert settings`.

### Task 3: Render patterns on the MicroByte LED

**Files:**
- Modify: `components/retro-go/targets/microbyte/config.h`
- Modify: `components/retro-go/rg_system.c`

- [ ] **Step 1: Add MicroByte LEDC channel/timer definitions** using a channel distinct from the LCD backlight channel, and leave digital GPIO fallback enabled for other targets.
- [ ] **Step 2: Initialize and deinitialize the optional PWM LED driver** without changing the existing GPIO2 polarity.
- [ ] **Step 3: Replace `update_activity_led()` and the old low-indicator color path** with a 100ms renderer that gives low-battery mode priority, maps 0..255 brightness to PWM duty, and falls back to GPIO on/off when PWM is unavailable.
- [ ] **Step 4: Verify disk/system activity and low-battery masking still work**, including the existing `LED options` setting.
- [ ] **Step 5: Commit** with `feat: render configurable status led patterns`.

### Task 4: Add short audio alert tones

**Files:**
- Modify: `components/retro-go/rg_audio.h`
- Modify: `components/retro-go/rg_audio.c`
- Modify: `components/retro-go/rg_system.c`
- Modify: `components/retro-go/translations.h`

- [ ] **Step 1: Add `rg_audio_play_tone(const rg_audio_tone_t *tone)`** using a fixed-size stack buffer and integer phase accumulation; return safely when the audio sink is dummy, muted, or uninitialized.
- [ ] **Step 2: Define low-battery single and critical double-tone sequences** without adding binary sound assets.
- [ ] **Step 3: Trigger tones only on low/critical threshold edges**, and enforce a 30-second repeat interval for the repeat setting.
- [ ] **Step 4: Run localization and host regression tests**, then document that the sound follows the system volume and is silent when audio is unavailable.
- [ ] **Step 5: Commit** with `feat: add low battery tone alerts`.

### Task 5: Implement the two-stage screen flow and protection choices

**Files:**
- Modify: `components/retro-go/rg_system.c`
- Modify: `components/retro-go/rg_gui.c`
- Modify: `components/retro-go/translations.h`
- Modify: `tests/test_battery.c`

- [ ] **Step 1: Extend the battery state machine** with edge-triggered low notification, critical prompt, and ignored-until-retry timestamps while preserving 15/20% and 3/8% hysteresis.
- [ ] **Step 2: Add a non-modal 15% message** that fires once per low-battery episode.
- [ ] **Step 3: Add a main-thread critical dialog** with `Ignore` and `Save & shutdown`; the save path calls `rg_emu_save_state(app.saveSlot)` before `rg_system_sleep()`.
- [ ] **Step 4: Make Ignore suppress the prompt for 60 seconds** and clear suppression when the battery reaches the 8% recovery threshold or is no longer present.
- [ ] **Step 5: Add pure state transition tests** for edge de-duplication, retry timing, recovery reset, and save-request behavior; run all host tests.
- [ ] **Step 6: Commit** with `feat: add two-stage low battery protection dialog`.

### Task 6: Verify, document, and prepare the visual demo

**Files:**
- Modify: `README.md`
- Modify: `tests/run_host_tests.sh`
- Create: `.superpowers/brainstorm/83997-1786985992/content/low-battery-settings.html`

- [ ] **Step 1: Add a concise MicroByte documentation section** describing the menu path, safe 0% calibration voltage, LED patterns, sound modes, and 15%/3% thresholds.
- [ ] **Step 2: Run `python3 -m unittest discover -s tests -p 'test_localization.py'`, `./tests/run_host_tests.sh all`, and `git diff --check`**; record any unavailable ESP-IDF build limitation.
- [ ] **Step 3: Replace the brainstorming page with an interactive settings mockup** showing LED mode, sound mode, and the two critical-dialog choices; verify the local URL renders.
- [ ] **Step 4: Attempt the MicroByte build with the repository's documented `rg_tool.py` command** and report the exact missing-toolchain error if unavailable.
- [ ] **Step 5: Commit documentation and test changes** with `docs: document configurable low battery feedback`.

## Self-Review

- Spec coverage: LED patterns and PWM are covered by Tasks 1-3; sound modes and tones by Task 4; two-stage screen flow and save/ignore behavior by Task 5; persistence, localization, tests, and web demonstration by Tasks 2, 5, and 6.
- No placeholder steps remain; each step names concrete files, APIs, commands, and expected behavior.
- API names are consistent: `rg_led_pattern_brightness`, `rg_audio_play_tone`, `LedSystemPattern`, `LedLowPattern`, and `LowBatterySound` are used consistently throughout.
