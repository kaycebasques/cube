# cube

Experimental repo. I am learning how to create Bazel-based Pigweed projects.
I recently struggled to use the bare metal STM32F429I target in combination
with the STM32Cube HAL library. This repo demonstrates what I tried and where
I struggled.

This repo will probably get archived or deleted in Q2 2024.

## Notes

[stm32f429i-disc1]: https://pigweed.dev/targets/stm32f429i_disc1/target_docs.html
[stm32f429i-disc1: STM32Cube]: https://pigweed.dev/targets/stm32f429i_disc1_stm32cube/target_docs.html

For a long time I actually did not know that STM32Cube was a HAL library.
"Cube" made me think it was a different, cube-shaped development board.
[stm32f429i-disc1] could probably make the purpose of STM32Cube more obvious.

**Takeaway**: Our docs should clearly state what each thing is. E.g. X is the
development board. Y is a HAL for that development board. Etc. It only takes
a few sentences to do and clears up a lot of confusion for any Pigweed users
who aren't familiar with a given manufacturer's hardware/software ecosystem.
