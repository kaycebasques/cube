# Copyright 2023 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Flash the echo binary to a connected STM32 Discovery Board.

Usage:
  bazel run //tools:flash
"""

import subprocess

from rules_python.python.runfiles import runfiles
from serial.tools import list_ports

_BINARY_PATH = "__main__/src/echo.elf"
_OPENOCD_PATH = "openocd/bin/openocd"
_OPENOCD_CONFIG_PATH = "pigweed/targets/stm32f429i_disc1/py/stm32f429i_disc1_utils/openocd_stm32f4xx.cfg"

# Vendor ID and model ID for the STM32 Discovery Board.
_ST_VENDOR_ID = 0x0483
_DISCOVERY_MODEL_ID = 0x374B


def get_board_serial() -> str:
  for dev in list_ports.comports():
    if dev.vid == _ST_VENDOR_ID and dev.pid == _DISCOVERY_MODEL_ID:
      return dev.serial_number

  raise IOError("Failed to detect connected board")


def flash(board_serial):
  r = runfiles.Create()
  openocd = r.Rlocation(_OPENOCD_PATH)
  binary = r.Rlocation(_BINARY_PATH)
  openocd_cfg = r.Rlocation(_OPENOCD_CONFIG_PATH)

  print(f"binary Rlocation is: {binary}")
  print(f"openocd Rlocation is: {openocd}")
  print(f"openocd config Rlocation is: {openocd_cfg}")

  assert binary is not None
  assert openocd_cfg is not None

  # Variables referred to by the OpenOCD config.
  env = {
      "PW_STLINK_SERIAL": board_serial,
      "PW_GDB_PORT": "disabled",
  }

  subprocess.check_call(
      [
          openocd,
          "-f",
          f"{openocd_cfg}",
          "-c",
          f"program {binary} reset exit",
      ],
      env=env,
  )


if __name__ == "__main__":
  flash(get_board_serial())
