// Target definition
#define RG_TARGET_NAME             "MICROBYTE"
#define RG_LANG_DEFAULT            RG_LANG_ZH_CN
#define RG_FONT_DEFAULT            RG_FONT_DEJAVU_12
#define RG_GUI_DEFAULTS_VERSION    1

// Status LED - GPIO2 (RUN indicator on MicroByte PCB)
// Active HIGH: ESP32 drives GPIO2 high to turn on the LED via R2 to GND
#define RG_GPIO_LED                GPIO_NUM_2

// Storage - SD Card via SPI
#define RG_STORAGE_ROOT             "/sd"
#define RG_STORAGE_SDSPI_HOST       SPI3_HOST    // VSPI
#define RG_STORAGE_SDSPI_SPEED      4000

// I2C Configuration (for TCA9555 GPIO expander)
#define RG_GPIO_I2C_SDA             GPIO_NUM_21
#define RG_GPIO_I2C_SCL             GPIO_NUM_22

// GPIO Extender - TCA9555 (register-compatible with PCF9539)
#define RG_I2C_GPIO_DRIVER          2   // 2 = PCF9539 (compatible with TCA9555)
#define RG_I2C_GPIO_ADDR            0x20

// Audio - External I2S DAC (MAX98357A)
#define RG_AUDIO_USE_INT_DAC        0   // Disable internal DAC
#define RG_AUDIO_USE_EXT_DAC        1   // Enable external I2S DAC
#define RG_GPIO_SND_I2S_BCK         GPIO_NUM_27
#define RG_GPIO_SND_I2S_WS          GPIO_NUM_26
#define RG_GPIO_SND_I2S_DATA        GPIO_NUM_25

// Video - ST7789 240x240 IPS display
#define RG_SCREEN_DRIVER            0   // 0 = ILI9341/ST7789 SPI driver
#define RG_SCREEN_HOST              SPI2_HOST    // HSPI
#define RG_SCREEN_SPEED             SPI_MASTER_FREQ_40M
#define RG_SCREEN_BACKLIGHT         1
#define RG_SCREEN_WIDTH             240
#define RG_SCREEN_HEIGHT            240
#define RG_SCREEN_ROTATE            0
#define RG_SCREEN_VISIBLE_AREA      {0, 0, 0, 0}
#define RG_SCREEN_SAFE_AREA         {0, 0, 0, 0}

// LCD GPIO Pins (CS is grounded on the module, so NC)
#define RG_GPIO_LCD_MISO            GPIO_NUM_NC   // Not connected (write-only)
#define RG_GPIO_LCD_MOSI            GPIO_NUM_13
#define RG_GPIO_LCD_CLK             GPIO_NUM_14
#define RG_GPIO_LCD_CS              GPIO_NUM_NC
#define RG_GPIO_LCD_DC              GPIO_NUM_32
#define RG_GPIO_LCD_BCKL            GPIO_NUM_15
#define RG_GPIO_LCD_RST             GPIO_NUM_33

// SD Card SPI Pins (Dedicated VSPI bus)
#define RG_GPIO_SDSPI_MISO          GPIO_NUM_19
#define RG_GPIO_SDSPI_MOSI          GPIO_NUM_23
#define RG_GPIO_SDSPI_CLK           GPIO_NUM_18
#define RG_GPIO_SDSPI_CS            GPIO_NUM_5

// Battery monitoring via ADC (BAT_STATUS is on SENSOR_VP / GPIO36)
#define RG_BATTERY_DRIVER           1
#define RG_BATTERY_ADC_UNIT         ADC_UNIT_1
#define RG_BATTERY_ADC_CHANNEL      ADC_CHANNEL_0  // GPIO 36
// Default battery calc (approximate for typical dividers)
#define RG_BATTERY_CALC_PERCENT(raw) (((raw) * 2.0f - 3500) / (4200 - 3500) * 100.0f)
#define RG_BATTERY_CALC_VOLTAGE(raw) ((raw) * 2.0f / 1000.0f)

// Gamepad - TCA9555 I2C button mapping
// TCA9555 Port 0 (register 0x00)
// TCA9555 Port 1 (register 0x01)
#define RG_GAMEPAD_I2C_MAP {\
    {RG_KEY_DOWN,   .num = 0,  .level = 0},\
    {RG_KEY_LEFT,   .num = 1,  .level = 0},\
    {RG_KEY_UP,     .num = 2,  .level = 0},\
    {RG_KEY_RIGHT,  .num = 3,  .level = 0},\
    {RG_KEY_L,      .num = 6,  .level = 0},\
    {RG_KEY_R,      .num = 7,  .level = 0},\
    {RG_KEY_B,      .num = 8,  .level = 0},\
    {RG_KEY_A,      .num = 9,  .level = 0},\
    {RG_KEY_START,  .num = 10, .level = 0},\
    {RG_KEY_MENU,   .num = 11, .level = 0},\
    {RG_KEY_SELECT, .num = 12, .level = 0},\
}

// ST7789 requires SPI mode 3 since CS is tied to GND
#define RG_SCREEN_SPI_MODE                  3

// ST7789 initialization sequence (from microByte firmware)
// Note: Sleep Out (0x11) and Display On (0x29) are sent by the driver after this init
#define RG_SCREEN_INIT()                        \
    ILI9341_CMD(0x36, 0x00);                    \
    ILI9341_CMD(0x3A, 0x55);                    \
    ILI9341_CMD(0x21);                          \
    ILI9341_CMD(0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33); \
    ILI9341_CMD(0xB7, 0x14);                    \
    ILI9341_CMD(0xBB, 0x37);                    \
    ILI9341_CMD(0xC2, 0x01, 0xFF);              \
    ILI9341_CMD(0xC3, 0x12);                    \
    ILI9341_CMD(0xC4, 0x20);                    \
    ILI9341_CMD(0xD0, 0xA4, 0xA1);              \
    ILI9341_CMD(0xC6, 0x0F);                    \
    ILI9341_CMD(0x26, 0x01);                    \
    ILI9341_CMD(0xE0, 0xD0, 0x08, 0x11, 0x08, 0x0C, 0x15, 0x39, 0x33, 0x50, 0x36, 0x13, 0x14, 0x29, 0x2D); \
    ILI9341_CMD(0xE1, 0xD0, 0x08, 0x10, 0x08, 0x06, 0x06, 0x39, 0x44, 0x51, 0x0B, 0x16, 0x14, 0x2F, 0x31);
