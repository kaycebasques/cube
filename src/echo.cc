// Copyright 2023 The Pigweed Authors
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not
// use this file except in compliance with the License. You may obtain a copy of
// the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations under
// the License.

#include <cstddef>

#include "pw_sys_io/sys_io.h"
#include "stm32f4xx.h"
#include "pw_sys_io_baremetal_stm32f429/init.h"

int main() {
  HAL_Init();
  pw_sys_io_stm32f429_Init();
  while (true) {
    std::byte data;
    pw::sys_io::ReadByte(&data).IgnoreError();
    std::byte c = (std::byte) 'c';  // new
    pw::sys_io::WriteByte(c).IgnoreError();  // new
  }
  return 0;
}
