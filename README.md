# MicroByte to Retro-Go Port 🎮

本项目是将 [Retro-Go](https://github.com/ducalex/retro-go) 固件完美移植到 **MicroByte** 掌机（ESP32-WROVER-E，16MB Flash，8MB PSRAM）的开源工程。

## ⚙️ 硬件适配与 GPIO 引脚梳理

在适配过程中，我们对 MicroByte 的硬件结构进行了全面梳理。以下是针对 Retro-Go 框架的 GPIO 映射清单：

| 模块 | 引脚 | 说明 |
| --- | --- | --- |
| **屏幕 (LCD ST7789 240x240)** | | |
| SPI MOSI | GPIO 13 | |
| SPI CLK | GPIO 14 | |
| CS | GPIO NC | 屏幕模块硬接地常通 |
| DC | GPIO 32 | |
| RST | GPIO 33 | |
| 背光 (BCKL) | GPIO 15 | |
| **存储 (SD Card)** | | |
| SPI MOSI | GPIO 23 | |
| SPI MISO | GPIO 19 | |
| SPI CLK | GPIO 18 | |
| CS | GPIO 5 | |
| **音频 (MAX98357A I2S DAC)**| | |
| I2S BCLK | GPIO 26 | |
| I2S WS (LRCK) | GPIO 25 | |
| I2S DATA (DOUT)| GPIO 27 | |
| **电源与电池** | | |
| 电池检测 ADC | GPIO 35 | ADC_UNIT_1, ADC_CHANNEL_7 |
| **手柄按键 (TCA9555)** | | **I2C SDA: GPIO 21, SCL: GPIO 22 (0x20)** |
| UP | Port 0, Bit 2 | Active Low |
| DOWN | Port 0, Bit 0 | Active Low |
| LEFT | Port 0, Bit 1 | Active Low |
| RIGHT | Port 0, Bit 3 | Active Low |
| A | Port 0, Bit 9 | (num=9) |
| B | Port 0, Bit 8 | (num=8) |
| START | Port 1, Bit 2 | (num=10) |
| SELECT | Port 1, Bit 3 | (num=11) |
| MENU | Port 1, Bit 4 | (num=12) |
| L | Port 1, Bit 2 | (num=6) |
| R | Port 1, Bit 3 | (num=7) |

## MicroByte 电源反馈

MicroByte 默认使用简体中文菜单。进入启动器的“选项 → LED 选项”可以分别设置系统活动灯和低电量灯的节奏：关闭、常亮、呼吸灯、慢闪烁、快闪烁或双脉冲；还可以关闭低电量声音，或选择单次/每 30 秒重复提示。LED 指的是主板上的 GPIO2 RUN/STATUS 单色灯，不是 LCD 背光灯。

电池电压可在“选项 → 电池校准”中校准。电池完全放空后设置 0% 电压，充满后设置 100% 电压；两次读数必须保持 0% 电压低于 100% 电压。恢复默认校准会使用 MicroByte 的 3.50V 到 4.20V 范围。

低电量保护分两级：电量降至 15% 时屏幕提示一次“电量不足”；降至 3% 时弹出“忽略”或“存档并关机”。忽略后 60 秒会再次询问，电量回升至 8% 后清除本次低电状态。选择存档并关机会先保存当前存档，再进入深度休眠。完整交互预览见 [`led-patterns.html`](.superpowers/brainstorm/83997-1786985992/content/led-patterns.html)。

---

## 🛠 排错经验总结：幽灵“DOWN”键之谜

在移植过程中，我们经历了一次极其硬核的 Bug 排查，史称“幽灵 DOWN 键之谜”。

**问题现象**：
游戏运行时，屏幕出现了 3 个沙漏后直接闪退回菜单。当修复了这个问题后，掌机开机竟然直接进入了 Recovery Mode，并且菜单会疯狂地**无限向下滚动**，仿佛有人一直按着“DOWN”键。

**排查过程**：
1. **隐藏的语法错误**：最初游戏闪退的原因，是因为我们在 `config.h` 中配置 I2C 键盘映射时，错误地使用了 `.bit = 0` 的语法，而 Retro-Go 的框架实际期望的是 `.num = 0`。这个语法错误导致 I2C 手柄驱动在前期根本没有成功加载！所以前期虽然菜单没有往下滚，但其实是因为手柄驱动是瘫痪的。
2. **唤醒幽灵**：当我们修正了语法（改回 `.num`），手柄驱动成功通网。但刚一通网，驱动就立刻读到了底层硬件传来的信号：`port0=0xFE`。这表示第 0 位（也就是 DOWN 键）处于被拉低（按下）的状态。
3. **原版固件代码溯源**：为了确认 DOWN 键的定义是否正确，我们深度扒取了 MicroByte 原版固件源码。原版代码中明确写着 `if(!((inputs_value >> 0) & 0x01))`，这证实了 DOWN 键确实连接在 Bit 0 上，且的确是低电平触发。不仅如此，我们还意外发现了原版固件中一个严重的 C 语言指针 Bug —— 它在初始化 TCA9555 芯片时，错误地传入了指针变量的内存地址（`&data`），导致配置信息被写到了乱码寄存器上。由于这个美丽的巧合，原版固件意外保留了芯片的开机默认状态（全输入、Output全高）。
4. **终极修复**：Retro-Go 的严谨初始化逻辑将 TCA9555 的 Output 寄存器强行置为了 `0x00`。为了彻底排除这个干扰，我们将代码修改为 `0xFF` 以对齐原版固件的默认状态。但在最新的测试中，我们发现开机仍然偶尔会读到 `0xFE`，而在手动按压其他按键后，又瞬间恢复成了 `0xFF`。最终真相大白——**这是一个硬件层面的物理卡滞！**由于掌机按键上的导电胶没有及时回弹（或者螺丝过紧），导致 DOWN 键在物理上真的被一直按住了。经过按压活动后，物理按键复位，日志立刻恢复正常。

**经验总结**：
在做嵌入式底层移植时，当你怀疑是软件 Bug 时，如果通过修改 I2C 寄存器状态甚至对比原版源码排查到了最底层的二进制电平，结果依然无解，那就必须要相信你的代码：**软件是对的，问题在物理层！**

---

# Table of contents
- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
- [Issues](#issues)
- [Development](#development)
- [Acknowledgements](#acknowledgements)
- [License](#license)

# Description
Retro-Go is a firmware to play retro games on ESP32-based devices (officially supported are
ODROID-GO and MRGC-G32, check [this list for other devices](components/retro-go/README.md)).
The project consists of a launcher and half a dozen applications that have been heavily
optimized to reduce their cpu, memory, and flash needs without reducing compatibility!

### Supported systems:
- Nintendo: **NES, SNES (slow), Gameboy, Gameboy Color, Game & Watch**
- Sega: **SG-1000, Master System, Mega Drive / Genesis, Game Gear**
- Coleco: **Colecovision**
- NEC: **PC Engine**
- Atari: **Lynx**
- Others: **DOOM** (including mods!)

### Retro-Go features:
- In-game menu
- Favorites and recently played
- GB color palettes, RTC adjust and save
- NES color palettes, PAL roms, NSF support
- More emulators and applications
- Scaling and filtering options
- Better performance and compatibility
- Turbo Speed/Fast forward
- Customizable launcher
- Cover art and save state previews
- Multiple save slots per game
- Wifi file manager
- And more!

### Screenshots
![Preview](assets/retro-go-preview.jpg)


# Installation

### ODROID-GO
  1. Download `retro-go_1.x_odroid-go.fw` from the [release page](https://github.com/ducalex/retro-go/releases/) and copy it to `/odroid/firmware` on your sdcard.
  2. Power up the device while holding down B.
  3. Select retro-go in the files list and flash it.

### MyRetroGameCase G32 (GBC)
  1. Download `retro-go_1.x_mrgc-g32.fw` from the [release page](https://github.com/ducalex/retro-go/releases/) and copy it to `/espgbc/firmware` on your sdcard.
  2. Power up the device while holding down MENU (the volume knob).
  3. Select retro-go in the files list and flash it.

### Other devices
  1. Download the .img for your device from the [release page](https://github.com/ducalex/retro-go/releases/).
  2. Connect your device to a computer with a USB cable.
  3. Flash the image with esptool:
     - [Command line](https://github.com/espressif/esptool/releases/): Run `esptool.py write_flash --flash_size detect 0x0 retro-go_*.img`
     - [Web version](https://espressif.github.io/esptool-js/): Connect your device, click Erase Flash, then select your .img file and set address to 0x0, finally click Program)

Your particular device may require extra steps (like holding a button during power up) or different esptool flags or a special cable. If the above steps fail, you might need to ask the manufacturer for instructions on how to flash new firmware!

If your device is not already supported or if a prebuilt version isn't available for it you can check the [development section](#Development) for more information on how to build for your device.


# Usage

## Game covers / artwork
Game covers should be placed in the `romart` folder at the base of your sd card. You can obtain a pre-made pack [here](https://github.com/ducalex/retro-go-covers). Retro-Go is also compatible with the older Go-Play romart pack.

You can add missing cover art by creating a PNG image (160x168, 8bit). Two naming schemes are supported:
- Filename-based: `/romart/nes/Super Mario.png` (notice the rom extension is *not* included)
- CRC32-based: `/romart/nes/A/ABCDE123.png` where `nes` is the same as the rom folder, and `ABCDE123` is the CRC32 of the game (press A -> Properties in the launcher to find it), and `A` is the first character of the CRC32

_Note: CRC32-based, which is what is used in the pre-made pack, is much slower than name-based! This type is useful because filenames vary greatly despite having identical CRCs, but if you generate your own art I suggest you use filename-based format and delete all CRC-based art from your SD Card to improve responsiveness._


## BIOS files
Some emulators support loading a BIOS. The files should be placed as follows:
- GB: `/retro-go/bios/gb_bios.bin`
- GBC: `/retro-go/bios/gbc_bios.bin`
- FDS: `/retro-go/bios/fds_bios.bin`
- MSX: In folder `/retro-go/bios/msx/` put: `MSX.ROM` `MSX2.ROM` `MSX2EXT.ROM` `MSX2P.ROM` `MSX2PEXT.ROM` `FMPAC.ROM` `DISK.ROM` `MSXDOS2.ROM` `PAINTER.ROM` `KANJI.ROM`


## Game & Watch
The roms must be packed with [LCD-Game-Shrinker](https://github.com/bzhxx/LCD-Game-Shrinker) and a tutorial can be [found here](https://gist.github.com/DNA64/16fed499d6bd4664b78b4c0a9638e4ef).


## Wifi
To use wifi you will need to create a `/retro-go/config/wifi.json` config file. You can define up to 4 different networks, then selectable in the menu. Its content should look like this:

````json
{
  "ssid0": "my-network",
  "password0": "my-password",
  "ssid1": "my-other-network",
  "password1": "my-password",
  "ssid2": "my-third-network",
  "password2": "my-password",
  "ssid3": "my-last-network",
  "password3": "my-password"
}
````

### Time synchronization
Time synchronization happens in the launcher immediately after a successful connection to the network.
This is done via NTP by contacting `pool.ntp.org` and cannot be disabled at this time.
Timezone can be configured in the launcher's options menu.

### File manager
You can find the IP of your device in the *about* menu of retro-go. Then on your PC navigate to
http://192.168.x.x/ to access the file manager.


## External DAC (headphones)

Retro-Go supports [the external DAC mod for the ODROID-GO](https://github.com/backofficeshow/odroid-go-audio-hat)
which allows high quality audio through headphones. You can switch to it in the menu `Audio Out: Ext DAC`.

<details>
  <summary>Pinout</summary>

  | GO PIN | PCM5102A PIN |
  |--------|---------|
  | 1 | GND |
  | 2 | - |
  | 3 | LCK |
  | 4 | DIN |
  | 5 | BCK |
  | 6 | VIN |
  | 7 | - |
  | 8 | - |
  | 9 | - |
  | 10 | - |
</details>


# Issues

### Black screen / Boot loops
Retro-Go typically detects and resolves application crashes and freezes automatically. However, if you do
get stuck in a boot loop, you can hold `DOWN` while powering up the device to return to the launcher.

### Sound quality
The volume isn't correctly attenuated on the GO, resulting in upper volume levels that are too loud and
lower levels that are distorted due to DAC resolution. A quick way to improve the audio is to cut one
of the speaker wire and add a `33 Ohm (or thereabout)` resistor in series. Soldering is better but not
required, twisting the wires tightly will work just fine.
[A more involved solution can be seen here.](https://wiki.odroid.com/odroid_go/silent_volume)
Alternatively you can use the headphones DAC mod mentioned earlier in this document.

### Game Boy SRAM *(aka Save/Battery/Backup RAM)*
In Retro-Go, save states will provide you with the best and most reliable save experience. That being said, please
read on if you need or want SRAM saves. The SRAM format is compatible with VisualBoyAdvance so it may be used to
import or export saves.

You can configure automatic SRAM saving in the options menu. A longer delay will reduce stuttering at the cost
of losing data when powering down too quickly. Also note that when *resuming* a game, Retro-Go will give priority
to a save state if present.

### ZIP files
Most Retro-Go applications now support ZIP files. ZIP archives should contain only one ROM file and nothing else. ZIP support also depends on available memory and larger ROMs may fail to load on some devices unfortunately.


# Development
If you wish to build or modify Retro-Go, you can find help in the following documents:

- Build instructions in [BUILDING.md](BUILDING.md)
- Theming instructions [THEMING.md](THEMING.md)
- Porting instructions in [PORTING.md](PORTING.md)
- Translating instructions in [LOCALIZATION.md](LOCALIZATION.md)


# Acknowledgements
- The NES/GBC/SMS emulators and base library were originally from the "Triforce" fork of the [official Go-Play firmware](https://github.com/othercrashoverride/go-play) by crashoverride, Nemo1984, and many others.
- The design of the launcher was originally inspired/copied from [pelle7's go-emu](https://github.com/pelle7/odroid-go-emu-launcher).
- PCE-GO is a fork of [HuExpress](https://github.com/kallisti5/huexpress) and [pelle7's port](https://github.com/pelle7/odroid-go-pcengine-huexpress/) was used as reference.
- The Lynx emulator is a port of [libretro-handy](https://github.com/libretro/libretro-handy).
- The SNES emulator is a port of [Snes9x 2005](https://github.com/libretro/snes9x2005).
- The DOOM engine is a port of [PrBoom 2.5.0](http://prboom.sourceforge.net/).
- The Genesis emulator is a port of [Gwenesis](https://github.com/bzhxx/gwenesis/) by bzhxx.
- The Game & Watch emulator is a port of [lcd-game-emulator](https://github.com/bzhxx/lcd-game-emulator) by bzhxx.
- The MSX emulator is a port of [fMSX](https://fms.komkon.org/fMSX/) by Marat Fayzullin.
- PNG support is provided by [lodepng](https://github.com/lvandeve/lodepng/).
- PCE cover art is from [Christian_Haitian](https://github.com/christianhaitian).
- Some icons from [Rokey](https://iconarchive.com/show/seed-icons-by-rokey.html).
- Background images from [es-theme-gbz35](https://github.com/rxbrad/es-theme-gbz35).
- Special thanks to [RGHandhelds](https://www.rghandhelds.com/) and [MyRetroGamecase](https://www.myretrogamecase.com/) for sending me a [G32](https://www.myretrogamecase.com/products/game-mini-g32-esp32-retro-gaming-console-1) device.
- The [ODROID-GO](https://forum.odroid.com/viewtopic.php?f=159&t=37599) community for encouraging the development of retro-go!

# License
Everything in this project is licensed under the [GPLv2 license](COPYING) with the exception of the following components:
- fmsx/components/fmsx (MSX Emulator, custom non-commercial license)
- handy-go/components/handy (Lynx emulator, zlib)
- components/retro-go/fonts/cjk_*_data.inc (generated CJK assets from Noto Sans CJK SC, SIL Open Font License 1.1; see components/retro-go/fonts/NotoSansCJK-OFL.txt)
