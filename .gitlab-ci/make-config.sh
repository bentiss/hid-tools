#!/bin/bash

# set exit on failure
set -e

# input specific options
cat <<EOF > input.config
CONFIG_GPIOLIB=y

CONFIG_USB=y
CONFIG_USB_SUPPORT=y
CONFIG_USB_XHCI_HCD=y
CONFIG_USB_EHCI_HCD=y
CONFIG_USB_UHCI_HCD=y
CONFIG_USB_OHCI_HCD=y

CONFIG_I2C=y

CONFIG_HID=y
CONFIG_UHID=y
CONFIG_USB_HID=y
CONFIG_I2C_HID_CORE=y
CONFIG_I2C_HID_ACPI=y
CONFIG_HIDRAW=y
CONFIG_HID_BATTERY_STRENGTH=y
CONFIG_HID_GENERIC=y
CONFIG_USB_HIDDEV=y

CONFIG_INPUT_EVDEV=y
CONFIG_INPUT_MISC=y
CONFIG_INPUT_UINPUT=y

CONFIG_LEDS_CLASS_MULTICOLOR=y
EOF

# change the local version
cat <<EOF > local.config
CONFIG_LOCALVERSION="-CI-PIPELINE-$CI_PIPELINE_ID"
EOF

vng --custom local.config --custom input.config --kconfig

for i in 0 1 2
do
  # switch all HID to y
  sed -i -E 's/^# CONFIG_HID(.*) is not set/CONFIG_HID\1=y/' .config

  # force the HID_FF modules to be set
  sed -i -E 's/^# CONFIG_(.*_FF) is not set/CONFIG_\1=y/' .config

  # check for new CONFIGS
  make olddefconfig
done
