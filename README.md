# cube

Experimental repo. I am learning how to create Bazel-based Pigweed projects.
I recently struggled to use the bare metal STM32F429I target in combination
with the STM32Cube HAL library. This repo demonstrates what I tried and where
I struggled.

This repo will probably get archived or deleted in Q2 2024.

## Notes

Notes are ordered chronologically, with the oldest stuff at the top. I'll
use H3 sections to make it easier to tell separate ideas apart.

[example/echo]: https://pigweed.googlesource.com/example/echo

[example/echo] was my starting point. Check out the pull request to see what
I changed: https://github.com/kaycebasques/cube/pull/1/files

### This is actually my second attempt

In my first attempt I was completely new to Bazel. I will note where I
struggled the most on that first attempt but I don't think it's worthwhile to
look directly at that first attempt. There's just too much noise from me
figuring out very basic Bazel things.

### STM32Cube...?

[stm32f429i-disc1]: https://pigweed.dev/targets/stm32f429i_disc1/target_docs.html
[stm32f429i-disc1: STM32Cube]: https://pigweed.dev/targets/stm32f429i_disc1_stm32cube/target_docs.html

For a long time I actually did not know that STM32Cube was a HAL library.
"Cube" made me think it was a different, cube-shaped development board.
[stm32f429i-disc1] could probably make the purpose of STM32Cube more obvious.

**Takeaway**: Our docs should clearly state what each thing is. E.g. X is the
development board. Y is a HAL for that development board. Etc. It only takes
a few sentences to do and clears up a lot of confusion for any Pigweed users
who aren't familiar with a given manufacturer's hardware/software ecosystem.

### example/echo works


Just a quick note to verify that I made sure that [example/echo] works on my
board before attempting these experiments.

### Pulling in STM32Cube

First things first, let's just try to pull in STM32Cube as a dep... How do I do
that? I actually don't remember. Let's search `stm32cube` on `pigweed.dev` and
see what shows up:

![search results for "stm32cube"](./img/stm32cube.png)

[pw_stm32cube_build]: https://web.archive.org/web/20240122213002/https://pigweed.dev/pw_stm32cube_build/

[pw_stm32cube_build] is coming up a lot. Let's try that.

I have to scroll that page for quite a while before I see anything related to
Bazel.

The Bazel section is kinda a wall-of-text. I was hoping for some simple setup
instructions presented as a numbered list.

In the Bazel section I see that I need to set up some other repos as external
deps, but first I'm going to just depend on `pw_stm32cube_build` and see what
happens when I try to build. 

So where do I put the `pw_stm32cube_build` dep? `//src/BUILD.bazel` makes sense
because it's the echo app that will be using the library. But
`//targets/BUILD.bazel` also makes sense because I'll be using the STM32Cube
lib with that target.

**Takeaway**: The `pw_stm32cube_build` should clearly and explicitly show where
to declare the dependency.

I'll just try `//src/BUILD.bazel` first. On my first attempt I tried this:

```
cc_binary(
    name = "echo",
    srcs = ["echo.cc"],
    malloc = select({
        "@platforms//cpu:armv7e-m": "@pigweed//pw_malloc",
        "//conditions:default": "@bazel_tools//tools/cpp:malloc",
    }),
    deps = [
        "@pigweed//pw_boot",
        "@pigweed//pw_sys_io",
        "@pigweed//targets:pw_assert_backend_impl",
        "@pigweed//pw_stm32cube_build",  # new
    ] + select({
        "@platforms//cpu:armv7e-m": [
            "@pigweed//targets/stm32f429i_disc1:basic_linker_script",
            "@pigweed//targets/stm32f429i_disc1:pre_init",
        ],
        "//conditions:default": [],
    }),
)
```

(In all code samples I always mark the code I changed with a `# new` comment.)

A major point of friction for me on my first attempt: it wasn't clear that
those top-level deps (`pw_boot`, `pw_sys_io`, etc.) will apply to all targets.
In this case both `host` and `stm32f429i`. I don't remember the exact error
but I was basically seeing errors about some assembly instructions being
missing, and I eventually figured out that STM32Cube should only be used within
the "context" of building for an Arm chip. In other words it probably makes
sense to nest the dep like this:

```
cc_binary(
    name = "echo",
    srcs = ["echo.cc"],
    malloc = select({
        "@platforms//cpu:armv7e-m": "@pigweed//pw_malloc",
        "//conditions:default": "@bazel_tools//tools/cpp:malloc",
    }),
    deps = [
        "@pigweed//pw_boot",
        "@pigweed//pw_sys_io",
        "@pigweed//targets:pw_assert_backend_impl",
    ] + select({
        "@platforms//cpu:armv7e-m": [
            "@pigweed//targets/stm32f429i_disc1:basic_linker_script",
            "@pigweed//targets/stm32f429i_disc1:pre_init",
            "@pigweed//pw_stm32cube_build",  # new
        ],
        "//conditions:default": [],
    }),
)
```

**Takeaway**: We should probably invest a lot more in the developer experience
for projects that build for multiple targets. I don't think vanilla Bazel does
enough for us here. developer experience = better docs, more tooling, etc.

OK, let's try to build that last change (`pw_stm32cube_build` nested as a dep
under `@platforms//cpu:armv7e-m`):

```
kayce@kayce0:~/repos/cube$ bazel build //...
ERROR: no such package '@@pigweed//pw_stm32cube_build': BUILD file not found in directory 'pw_stm32cube_build' of external repository @@pigweed. Add a BUILD file to a directory to mark it as a package.
ERROR: /home/kayce/repos/cube/src/BUILD.bazel:18:10: no such package '@@pigweed//pw_stm32cube_build': BUILD file not found in directory 'pw_stm32cube_build' of external repository @@pigweed. Add a BUILD file to a directory to mark it as a package. and referenced by '//src:echo'
Target //:pip_requirements up-to-date (nothing to build)
ERROR: Analysis of target '//src:echo.elf' failed; build aborted: Analysis failed
INFO: Elapsed time: 0.280s, Critical Path: 0.00s
INFO: 1 process: 1 internal.
ERROR: Build did NOT complete successfully
```

On my first attempt it took me a little while to figure out that when you pull in a
dep, that directory needs to have a `BUILD.bazel` file. It was just a minor
friction point though; Bazel's error message helped me figure this out fairly
quickly.

[pw_stm32cube_build source]: https://cs.opensource.google/pigweed/pigweed/+/main:pw_stm32cube_build/
[//third_party/stm32cube]: https://cs.opensource.google/pigweed/pigweed/+/main:third_party/stm32cube/

OK, so if I head over to the [pw_stm32cube_build source] I can verify that
there's no `BUILD` file in that dir. The top of the [pw_stm32cube_build] doc
says that `pw_stm32cube_build` is an alias to [//third_party/stm32cube]... I
guess I need to depend on that other directory instead? Yes, I can see a
`BUILD.bazel` file in there. There's a few `*.BUILD.bazel` files actually.
The stuff about "external dependencies" in the pw_stm32cube_build doc is
starting to make more sense. I see that there's a `BUILD.bazel` for many of the
external deps that the doc mentions.

[//third_party/stm32cube/BUILD.bazel]: https://cs.opensource.google/pigweed/pigweed/+/main:third_party/stm32cube/

In [//third_party/stm32cube/BUILD.bazel] I see a `cc_library` called
`stm32cube`, that seems to be what I need. Let's try that.

```
cc_binary(
    name = "echo",
    srcs = ["echo.cc"],
    malloc = select({
        "@platforms//cpu:armv7e-m": "@pigweed//pw_malloc",
        "//conditions:default": "@bazel_tools//tools/cpp:malloc",
    }),
    deps = [
        "@pigweed//pw_boot",
        "@pigweed//pw_sys_io",
        "@pigweed//targets:pw_assert_backend_impl",
    ] + select({
        "@platforms//cpu:armv7e-m": [
            "@pigweed//targets/stm32f429i_disc1:basic_linker_script",
            "@pigweed//targets/stm32f429i_disc1:pre_init",
            "@pigweed//third_party/stm32cube:stm32cube",  # new
        ],
        "//conditions:default": [],
    }),
)
```

I'm not sure if I need to add `:stm32cube` when the library name matches the
directory name but it's more explicit so I'll just keep it like that.

OK, build attempt:

```
kayce@kayce0:~/repos/cube$ bazel build //...
ERROR: no such package '@@hal_driver//': The repository '@@hal_driver' could not be resolved: Repository '@@hal_driver' is not defined
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/third_party/stm32cube/BUILD.bazel:36:11: every rule of type label_flag implicitly depends upon the target '@@hal_driver//:hal_driver', but this target could not be found because of: no such package '@@hal_driver//': The repository '@@hal_driver' could not be resolved: Repository '@@hal_driver' is not defined
Target //:pip_requirements up-to-date (nothing to build)
ERROR: Analysis of target '//src:echo.elf' failed; build aborted: Analysis failed
INFO: Elapsed time: 0.247s, Critical Path: 0.00s
INFO: 1 process: 1 internal.
ERROR: Build did NOT complete successfully
```

OK, this is expected. The doc mentions the need for external deps and the
`cc_library` definition also mentioned `:hal_driver` as a dep.

### Pulling in hal_driver

In my first attempt this was a big friction point for me. Possible the biggest.

Alright I need to add a dep called `hal_driver` but how do I do that?

The doc just says this:

```
stm32{family}xx_hal_driver (e.g., HAL driver repo for the F4 family).
We provide a Bazel build file which works for any family at
@pigweed//third_party/stm32cube/stm32_hal_driver.BUILD.bazel. By default,
we assume this repository will be named @hal_driver, but this can be
overriden with a label flag (discussed below).
```

How do I add the repo? Poking around the `WORKSPACE` file I inherited from
example/echo, I guess I add hal_driver via `local_repository`? Because that's
how we add Pigweed.

```
local_repository(
    name = "pigweed",
    path = "third_party/pigweed",
)
```

A URL isn't specified so presumably I add it as a Git submodule. I personally
don't like submodules. They're finicky. When I clone / initialize repos the
submodules often don't seem to initialize correctly.

Anyways, I init the submodule:

```
git submodule add https://github.com/STMicroelectronics/stm32f4xx_hal_driver \
    third_party/hal_driver
```

And then add a new `local_repository`:

```
local_repository(
    name = "hal_driver",
    path = "third_party/hal_driver",
)
```

And then I try to build again and get this long error output:

```
kayce@kayce0:~/repos/cube$ bazel build //...
Starting local Bazel server and connecting to it...
ERROR: /home/kayce/repos/cube/WORKSPACE:82:17: fetching local_repository rule //external:hal_driver: java.io.IOException: No WORKSPACE file found in /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/hal_driver
INFO: Repository cipd_client instantiated at:
  /home/kayce/repos/cube/WORKSPACE:95:23: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/pw_env_setup/bazel/cipd_setup/cipd_rules.bzl:44:28: in cipd_client_repository
Repository rule _cipd_client_repository defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/pw_env_setup/bazel/cipd_setup/cipd_rules.bzl:23:42: in <toplevel>
INFO: Repository pypi__pip instantiated at:
  /home/kayce/repos/cube/WORKSPACE:120:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: Repository pypi__setuptools instantiated at:
  /home/kayce/repos/cube/WORKSPACE:120:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: Repository pypi__click instantiated at:
  /home/kayce/repos/cube/WORKSPACE:120:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: repository @pypi__pip' used the following cache hits instead of downloading the corresponding file.
 * Hash '908c78e6bc29b676ede1c4d57981d490cb892eb45cd8c214ab6298125119e077' for https://files.pythonhosted.org/packages/09/bd/2410905c76ee14c62baf69e3f4aa780226c1bbfc9485731ad018e35b0cb5/pip-22.3.1-py3-none-any.whl
If the definition of 'repository @pypi__pip' was updated, verify that the hashes were also updated.
INFO: repository @pypi__setuptools' used the following cache hits instead of downloading the corresponding file.
 * Hash '782ef48d58982ddb49920c11a0c5c9c0b02e7d7d1c2ad0aa44e1a1e133051c96' for https://files.pythonhosted.org/packages/7c/5b/3d92b9f0f7ca1645cba48c080b54fe7d8b1033a4e5720091d1631c4266db/setuptools-60.10.0-py3-none-any.whl
If the definition of 'repository @pypi__setuptools' was updated, verify that the hashes were also updated.
INFO: repository @pypi__click' used the following cache hits instead of downloading the corresponding file.
 * Hash 'fba402a4a47334742d782209a7c79bc448911afe1149d07bdabdf480b3e2f4b6' for https://files.pythonhosted.org/packages/76/0a/b6c5f311e32aeb3b406e03c079ade51e905ea630fc19d1262a46249c1c86/click-8.0.1-py3-none-any.whl
If the definition of 'repository @pypi__click' was updated, verify that the hashes were also updated.
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/third_party/stm32cube/BUILD.bazel:36:11: @pigweed//third_party/stm32cube:hal_driver depends on @hal_driver//:hal_driver in repository @hal_driver which failed to fetch. no such package '@hal_driver//': No WORKSPACE file found in /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/hal_driver
ERROR: Analysis of target '//src:echo.elf' failed; build aborted: 
INFO: Elapsed time: 3.486s
INFO: 0 processes.
FAILED: Build did NOT complete successfully (68 packages loaded, 408 targets configured)
    Fetching repository @pypi__more_itertools; starting
    Fetching repository @pypi_pyserial; starting
    Fetching repository @pypi__zipp; starting
    Fetching repository @openocd; Restarting.
    Fetching ...bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__setuptools; Extracting setuptools-60.10.0-py3-none-any.whl.zip
    Fetching .../.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__pip; Extracting pip-22.3.1-py3-none-any.whl.zip
    Fetching ...ache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__click; Extracting click-8.0.1-py3-none-any.whl.zip
    Fetching repository @gcc_arm_none_eabi_toolchain; Restarting.
```

`hal_driver` doesn't have a `WORKSPACE` file? Not sure what to do about that.
I'm supposed to just clone the repo to use it as a dependency. Obviously I
shouldn't be modifying the repo itself by adding a `WORKSPACE` file.

Luckily I have GenAI assistants to help me now. Before, I probably would have
got stuck at this point and given up. But my assistant steers me towards using
`new_local_repository` instead, which lets me specify the path to a
`BUILD.bazel` file for the dep:

```
new_local_repository(
    name = "hal_driver",
    path = "third_party/hal_driver",
    build_file = "@pigweed//third_party/stm32cube:stm32_hal_driver.BUILD.bazel",
)
```

OK, we've made progress. The build is now failing on a missing `cmsis_device`
dep, which I recall pw_stm32cube_build mentioning:

```
kayce@kayce0:~/repos/cube$ bazel build //...
INFO: Repository pypi__pip instantiated at:
  /home/kayce/repos/cube/WORKSPACE:121:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: repository @pypi__pip' used the following cache hits instead of downloading the corresponding file.
 * Hash '908c78e6bc29b676ede1c4d57981d490cb892eb45cd8c214ab6298125119e077' for https://files.pythonhosted.org/packages/09/bd/2410905c76ee14c62baf69e3f4aa780226c1bbfc9485731ad018e35b0cb5/pip-22.3.1-py3-none-any.whl
If the definition of 'repository @pypi__pip' was updated, verify that the hashes were also updated.
INFO: Repository pypi__setuptools instantiated at:
  /home/kayce/repos/cube/WORKSPACE:121:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: repository @pypi__setuptools' used the following cache hits instead of downloading the corresponding file.
 * Hash '782ef48d58982ddb49920c11a0c5c9c0b02e7d7d1c2ad0aa44e1a1e133051c96' for https://files.pythonhosted.org/packages/7c/5b/3d92b9f0f7ca1645cba48c080b54fe7d8b1033a4e5720091d1631c4266db/setuptools-60.10.0-py3-none-any.whl
If the definition of 'repository @pypi__setuptools' was updated, verify that the hashes were also updated.
INFO: Repository rules_license instantiated at:
  /DEFAULT.WORKSPACE.SUFFIX:530:6: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: Repository rules_proto instantiated at:
  /home/kayce/repos/cube/WORKSPACE:37:13: in <toplevel>
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/hal_driver/BUILD.bazel:39:11: every rule of type label_flag implicitly depends upon the target '@cmsis_device//:default_cmsis_init', but this target could not be found because of: no such package '@cmsis_device//': The repository '@cmsis_device' could not be resolved: Repository '@cmsis_device' is not defined
ERROR: Analysis of target '//src:echo.elf' failed; build aborted: 
INFO: Elapsed time: 0.530s
INFO: 0 processes.
FAILED: Build did NOT complete successfully (29 packages loaded, 306 targets configured)
    currently loading: @pigweed//pw_log ... (2 packages)
    Fetching repository @pypi_pyserial; Restarting.
    Fetching repository @openocd; Restarting.
    Fetching repository @cipd_client; starting
    Fetching ...bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__setuptools; Extracting setuptools-60.10.0-py3-none-any.whl.zip
    Fetching .../.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__pip; Extracting pip-22.3.1-py3-none-any.whl.zip
    Fetching repository @gcc_arm_none_eabi_toolchain; Restarting.
    Fetching repository @pypi__installer; starting
    Fetching repository @llvm_toolchain; Restarting.
```

Let me go through the rigmarole of adding another submodule...

```
git submodule add https://github.com/STMicroelectronics/cmsis_device_f4 third_party/cmsis_device
```

And another local repo...

```
new_local_repository(
    name = "cmsis_device",
    path = "third_party/cmsis_device",
    build_file = "@pigweed//third_party/stm32cube:cmsis_device.BUILD.bazel",
)
```

Now the build is failing at a missing `cmsis_core`. This is also OK because
I remember the pw_stm32cube_build mentioning that it's required.

```
kayce@kayce0:~/repos/cube$ bazel build //...
INFO: Repository cipd_client instantiated at:
  /home/kayce/repos/cube/WORKSPACE:102:23: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/pw_env_setup/bazel/cipd_setup/cipd_rules.bzl:44:28: in cipd_client_repository
Repository rule _cipd_client_repository defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/pw_env_setup/bazel/cipd_setup/cipd_rules.bzl:23:42: in <toplevel>
INFO: Repository pypi__setuptools instantiated at:
  /home/kayce/repos/cube/WORKSPACE:127:10: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip.bzl:149:29: in pip_parse
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/rules_python/python/pip_install/repositories.bzl:141:14: in pip_install_dependencies
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: Repository rules_license instantiated at:
  /DEFAULT.WORKSPACE.SUFFIX:530:6: in <toplevel>
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/utils.bzl:233:18: in maybe
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: Repository rules_proto instantiated at:
  /home/kayce/repos/cube/WORKSPACE:37:13: in <toplevel>
Repository rule http_archive defined at:
  /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/bazel_tools/tools/build_defs/repo/http.bzl:372:31: in <toplevel>
INFO: repository @pypi__setuptools' used the following cache hits instead of downloading the corresponding file.
 * Hash '782ef48d58982ddb49920c11a0c5c9c0b02e7d7d1c2ad0aa44e1a1e133051c96' for https://files.pythonhosted.org/packages/7c/5b/3d92b9f0f7ca1645cba48c080b54fe7d8b1033a4e5720091d1631c4266db/setuptools-60.10.0-py3-none-any.whl
If the definition of 'repository @pypi__setuptools' was updated, verify that the hashes were also updated.
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/cmsis_device/BUILD.bazel:21:11: every rule of type label_flag implicitly depends upon the target '@cmsis_core//:cmsis_core', but this target could not be found because of: no such package '@cmsis_core//': The repository '@cmsis_core' could not be resolved: Repository '@cmsis_core' is not defined
ERROR: Analysis of target '//src:echo.elf' failed; build aborted: 
INFO: Elapsed time: 0.267s
INFO: 0 processes.
FAILED: Build did NOT complete successfully (25 packages loaded, 261 targets configured)
    currently loading: @pigweed//pw_log ... (2 packages)
    Fetching repository @llvm_toolchain; Restarting.
    Fetching repository @openocd; Restarting.
    Fetching repository @pypi_pyserial; starting
    Fetching repository @pypi__pip; starting
    Fetching repository @gcc_arm_none_eabi_toolchain; Restarting.
    Fetching ...bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__setuptools; Extracting setuptools-60.10.0-py3-none-any.whl.zip
    Fetching .../.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pypi__pip; Extracting pip-22.3.1-py3-none-any.whl.zip
```

Adding the `cmsis_core` submodule...

```
git submodule add https://github.com/STMicroelectronics/cmsis_core third_party/cmsis_core
```

And `new_local_repository`...

```
new_local_repository(
    name = "cmsis_core",
    path = "third_party/cmsis_core",
    build_file = "@pigweed//third_party/stm32cube:cmsis_core.BUILD.bazel",
)
```

OK what happens when I try to build now?

It seems like it's building correctly but it's taking a while.

OK it built! So how can I actually use this stuff now??

**Takeaway**: Is there any way to speed up / simplify this external dep stuff??

(In my first attempt I was lucky because I knew where to look for other
examples e.g. `sample_project` and upstream Pigweed itself. A real prospective
customer might not discover this stuff. Also, as a technical writer, it's
important to realize that I might have more patience to do research than
actual prospective customers. So "lack of discoverability of examples" might
be a major issue for real Pigweed prospective customers at this point.)

At this point I search around a lot just trying to find code examples on how
to use STM32Cube. I find this official-looking repo but it seems to rely on
a board support package that is not part of Pigweed's offering:
https://github.com/STMicroelectronics/STM32CubeF4/tree/master/Projects/STM32F429I-Discovery/Examples

I know that upstream Pigweed has a target that uses STM32Cube, maybe I can find
some usage examples there? https://cs.opensource.google/pigweed/pigweed/+/master:targets/stm32f429i_disc1_stm32cube/boot.cc

In `boot.cc` I see `stm32f4xx.h`. That seems like my HAL library. Let me
just try to include that file into my `echo.cc` and see if my project has
already somehow pulled it in for me:

```
#include <cstddef>

#include "pw_sys_io/sys_io.h"
#include "stm32f4xx.h"  // new

int main() {
  while (true) {
    std::byte data;
    pw::sys_io::ReadByte(&data).IgnoreError();
    pw::sys_io::WriteByte(data).IgnoreError();
  }
  return 0;
}
```

Nope:

```
kayce@kayce0:~/repos/cube$ bazel build //...
INFO: Analyzed 7 targets (25 packages loaded, 1024 targets configured).
INFO: Found 7 targets...
ERROR: /home/kayce/repos/cube/src/BUILD.bazel:18:10: Compiling src/echo.cc failed: (Exit 1): clang++ failed: error executing command (from target //src:echo) external/llvm_toolchain/bin/clang++ -Wall -Wextra -Werror '-Wno-error=cpp' '-Wno-error=deprecated-declarations' -Wthread-safety '-D_LIBCPP_ENABLE_THREAD_SAFETY_ANNOTATIONS=1' '-std=c++17' -g ... (remaining 90 arguments skipped)

Use --sandbox_debug to see verbose messages from the sandbox and retain the sandbox build root for debugging
src/echo.cc:18:10: fatal error: 'stm32f4xx.h' file not found
   18 | #include "stm32f4xx.h"
      |          ^~~~~~~~~~~~~
1 error generated.
INFO: Elapsed time: 0.630s, Critical Path: 0.40s
INFO: 2 processes: 2 internal.
FAILED: Build did NOT complete successfully
```

On my first attempt it took me a looooooong time to figure out that the error
only occurs when the project attempts to build for `host`. When it attempts to
build for the STM32 board it's fine. I eventually figure out how to specify on
the command line how to build for one target only:

```
kayce@kayce0:~/repos/cube$ bazel build --platforms=//targets:stm32 //...
INFO: Build option --platforms has changed, discarding analysis cache.
INFO: Analyzed 7 targets (0 packages loaded, 11796 targets configured).
INFO: Found 7 targets...
INFO: Elapsed time: 0.448s, Critical Path: 0.09s
INFO: 11 processes: 11 internal.
INFO: Build completed successfully, 11 total actions
```

I haven't done anything with the library yet. I've just included it. Does the
echo app still work?

```
kayce@kayce0:~/repos/cube$ bazel run //tools:flash
INFO: Build option --platforms has changed, discarding analysis cache.
ERROR: Target //tools:flash is incompatible and cannot be built, but was explicitly requested.
Dependency chain:
    //tools:flash (307454)
    //src:echo.elf (307454)
    //src:echo (22efee)
    @pigweed//third_party/stm32cube:stm32cube (22efee)
    @pigweed//third_party/stm32cube:hal_driver (22efee)
    @hal_driver//:hal_driver (22efee)
    @hal_driver//:hal_driver_without_timebase (22efee)
    @hal_driver//:hal_headers (22efee)
    @hal_driver//:hal_config (22efee)
    @hal_driver//:unspecified (22efee)   <-- target platform (//targets:stm32) didn't satisfy constraint @platforms//:incompatible
INFO: Elapsed time: 0.285s
INFO: 0 processes.
FAILED: Build did NOT complete successfully (0 packages loaded, 13303 targets configured)
ERROR: Build failed. Not running target
```

This is another point where I'm very lucky to have a GenAI assistant. It's
very likely I would have got stuck and given up at this point without an
assistant's help. But the assistant decodes the error for me and tells me that
the key is the `@hal_driver//:hal_config` line. That's the thing I need to fix.

So how do I set `@hal_driver//:hal_config`? [pw_stm32cube_build] mentions it
but doesn't provide details:

```
@hal_driver//:hal_config
Points to the cc_library target providing a header with the HAL configuration.
Note that this header needs an appropriate, family-specific name (e.g.,
stm32f4xx_hal_conf.h for the F4 family).
```

On my first attempt I saw `hal_config` in `//third_party/stm32cube/stm32_hal_driver.BUILD.bazel`
and tried pointing to that. Eventually I see the code comment and realized I
need to point somewhere else:

```
# Must point to a cc_library exposing a header named stm32f4xx_hal_conf.h (or
# similar for other families) that contains the HAL configuration
label_flag(
    name = "hal_config",
    build_setting_default = ":unspecified",
)
```

So I guess I really need something that mentions `stm32f4xx_hal_conf.h`,
let me search for that string in upstream Pigweed source code...

The string only shows up in two places:

* `//targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h`
* `//targets/stm32f429i_disc1_stm32cube/BUILD.bazel`

So I guess I need to use something in that 
`//targets/stm32f429i_disc1_stm32cube/BUILD.bazel` file?

Yes, there's a `cc_library` called `hal_config`. That seems to be what I need.

```
cc_library(
    name = "hal_config",
    hdrs = [
        "config/stm32f4xx_hal_conf.h",
    ],
    includes = ["config"],
)
```

I don't know where to put this. I guess I'll try putting it in the
`//src/BUILD.bazel` deps first?

It builds OK:

```
kayce@kayce0:~/repos/cube$ bazel build --platforms=//targets:stm32 //...
INFO: Build option --platforms has changed, discarding analysis cache.
INFO: Analyzed 7 targets (2 packages loaded, 11798 targets configured).
INFO: Found 7 targets...
INFO: Elapsed time: 0.247s, Critical Path: 0.01s
INFO: 1 process: 1 internal.
INFO: Build completed successfully, 1 total action
```

But does it flash?

```
kayce@kayce0:~/repos/cube$ bazel run //tools:flash
INFO: Build option --platforms has changed, discarding analysis cache.
ERROR: Target //tools:flash is incompatible and cannot be built, but was explicitly requested.
Dependency chain:
    //tools:flash (307454)
    //src:echo.elf (307454)
    //src:echo (22efee)
    @pigweed//third_party/stm32cube:stm32cube (22efee)
    @pigweed//third_party/stm32cube:hal_driver (22efee)
    @hal_driver//:hal_driver (22efee)
    @hal_driver//:hal_driver_without_timebase (22efee)
    @hal_driver//:hal_headers (22efee)
    @hal_driver//:hal_config (22efee)
    @hal_driver//:unspecified (22efee)   <-- target platform (//targets:stm32) didn't satisfy constraint @platforms//:incompatible
INFO: Elapsed time: 0.225s
INFO: 0 processes.
FAILED: Build did NOT complete successfully (0 packages loaded, 13305 targets configured)
ERROR: Build failed. Not running target
```

No, it does not. Same issue as before.

After quite a lot of mumbled swearing I figure out that I should put this in
`.bazelrc`:

```
build:stm32 --@hal_driver//:hal_config=@pigweed//targets/stm32f429i_disc1_stm32cube:hal_config
```

And run the flash script like this:

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash
INFO: Build option --@hal_driver//:hal_config has changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/hal_driver/BUILD.bazel:76:11: Compiling Src/stm32f4xx_ll_sdmmc.c failed: (Exit 1): arm-none-eabi-gcc failed: error executing command (from target @hal_driver//:hal_driver_without_timebase) external/gcc_arm_none_eabi_toolchain/bin/arm-none-eabi-gcc -O2 -g -fno-common -fno-exceptions -ffunction-sections -fdata-sections -no-canonical-prefixes '-mcpu=cortex-m4+nofp' '-mfloat-abi=soft' ... (remaining 69 arguments skipped)

Use --sandbox_debug to see verbose messages from the sandbox and retain the sandbox build root for debugging
In file included from external/hal_driver/Inc/stm32f4xx_hal_def.h:29,
                 from external/hal_driver/Inc/stm32f4xx_hal_cortex.h:27,
                 from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:96,
                 from external/hal_driver/Inc/stm32f4xx_hal.h:29,
                 from external/hal_driver/Src/stm32f4xx_ll_sdmmc.c:159:
external/cmsis_device/Include/stm32f4xx.h:174:2: error: #error "Please select first the target STM32F4xx device used in your application (in stm32f4xx.h file)"
  174 | #error "Please select first the target STM32F4xx device used in your application (in stm32f4xx.h file)"
      |  ^~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:261:27: error: unknown type name 'IRQn_Type'
  261 | void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t PreemptPriority, uint32_t SubPriority);
      |                           ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:262:25: error: unknown type name 'IRQn_Type'
  262 | void HAL_NVIC_EnableIRQ(IRQn_Type IRQn);
      |                         ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:263:26: error: unknown type name 'IRQn_Type'
  263 | void HAL_NVIC_DisableIRQ(IRQn_Type IRQn);
      |                          ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:275:27: error: unknown type name 'IRQn_Type'
  275 | void HAL_NVIC_GetPriority(IRQn_Type IRQn, uint32_t PriorityGroup, uint32_t* pPreemptPriority, uint32_t* pSubPriority);
      |                           ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:276:33: error: unknown type name 'IRQn_Type'
  276 | uint32_t HAL_NVIC_GetPendingIRQ(IRQn_Type IRQn);
      |                                 ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:277:29: error: unknown type name 'IRQn_Type'
  277 | void HAL_NVIC_SetPendingIRQ(IRQn_Type IRQn);
      |                             ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:278:31: error: unknown type name 'IRQn_Type'
  278 | void HAL_NVIC_ClearPendingIRQ(IRQn_Type IRQn);
      |                               ^~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_cortex.h:279:29: error: unknown type name 'IRQn_Type'
  279 | uint32_t HAL_NVIC_GetActive(IRQn_Type IRQn);
      |                             ^~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:99:
external/hal_driver/Inc/stm32f4xx_hal_dma.h:140:3: error: unknown type name 'DMA_Stream_TypeDef'
  140 |   DMA_Stream_TypeDef         *Instance;                                                        /*!< Register base address                  */
      |   ^~~~~~~~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_dma.h:146:3: error: unknown type name '__IO'
  146 |   __IO HAL_DMA_StateTypeDef  State;                                                            /*!< DMA transfer state                     */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_dma.h:146:30: error: expected ':', ',', ';', '}' or '__attribute__' before 'State'
  146 |   __IO HAL_DMA_StateTypeDef  State;                                                            /*!< DMA transfer state                     */
      |                              ^~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:105:
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:224:21: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  224 | void  HAL_GPIO_Init(GPIO_TypeDef  *GPIOx, GPIO_InitTypeDef *GPIO_Init);
      |                     ^~~~~~~~~~~~
      |                     GPIO_InitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:225:23: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  225 | void  HAL_GPIO_DeInit(GPIO_TypeDef  *GPIOx, uint32_t GPIO_Pin);
      |                       ^~~~~~~~~~~~
      |                       GPIO_InitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:234:32: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  234 | GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
      |                                ^~~~~~~~~~~~
      |                                GPIO_InitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:235:24: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  235 | void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState);
      |                        ^~~~~~~~~~~~
      |                        GPIO_InitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:236:25: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  236 | void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
      |                         ^~~~~~~~~~~~
      |                         GPIO_InitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_gpio.h:237:36: error: unknown type name 'GPIO_TypeDef'; did you mean 'GPIO_InitTypeDef'?
  237 | HAL_StatusTypeDef HAL_GPIO_LockPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
      |                                    ^~~~~~~~~~~~
      |                                    GPIO_InitTypeDef
In file included from external/hal_driver/Inc/stm32f4xx_hal_rcc.h:31,
                 from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:108:
external/hal_driver/Inc/stm32f4xx_hal_rcc_ex.h:6806:45: error: unknown type name 'RCC_PeriphCLKInitTypeDef'; did you mean 'RCC_PLLInitTypeDef'?
 6806 | HAL_StatusTypeDef HAL_RCCEx_PeriphCLKConfig(RCC_PeriphCLKInitTypeDef  *PeriphClkInit);
      |                                             ^~~~~~~~~~~~~~~~~~~~~~~~
      |                                             RCC_PLLInitTypeDef
external/hal_driver/Inc/stm32f4xx_hal_rcc_ex.h:6807:35: error: unknown type name 'RCC_PeriphCLKInitTypeDef'; did you mean 'RCC_PLLInitTypeDef'?
 6807 | void HAL_RCCEx_GetPeriphCLKConfig(RCC_PeriphCLKInitTypeDef  *PeriphClkInit);
      |                                   ^~~~~~~~~~~~~~~~~~~~~~~~
      |                                   RCC_PLLInitTypeDef
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:113:
external/hal_driver/Inc/stm32f4xx_hal_adc.h:198:3: error: unknown type name 'ADC_TypeDef'
  198 |   ADC_TypeDef                   *Instance;                   /*!< Register base address */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_adc.h:202:3: error: unknown type name '__IO'
  202 |   __IO uint32_t                 NbrOfCurrentConversionRank;  /*!< ADC number of current conversion rank */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_adc.h:202:33: error: expected ':', ',', ';', '}' or '__attribute__' before 'NbrOfCurrentConversionRank'
  202 |   __IO uint32_t                 NbrOfCurrentConversionRank;  /*!< ADC number of current conversion rank */
      |                                 ^~~~~~~~~~~~~~~~~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:127:
external/hal_driver/Inc/stm32f4xx_hal_crc.h:61:3: error: unknown type name 'CRC_TypeDef'
   61 |   CRC_TypeDef                 *Instance;   /*!< Register base address        */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_crc.h:65:3: error: unknown type name '__IO'
   65 |   __IO HAL_CRC_StateTypeDef   State;       /*!< CRC communication state      */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_crc.h:65:31: error: expected ':', ',', ';', '}' or '__attribute__' before 'State'
   65 |   __IO HAL_CRC_StateTypeDef   State;       /*!< CRC communication state      */
      |                               ^~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:158:
external/hal_driver/Inc/stm32f4xx_hal_flash.h:58:3: error: unknown type name '__IO'
   58 |   __IO FLASH_ProcedureTypeDef ProcedureOnGoing;   /*Internal variable to indicate which procedure is ongoing or not in IT context*/
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_flash.h:58:31: error: expected ':', ',', ';', '}' or '__attribute__' before 'ProcedureOnGoing'
   58 |   __IO FLASH_ProcedureTypeDef ProcedureOnGoing;   /*Internal variable to indicate which procedure is ongoing or not in IT context*/
      |                               ^~~~~~~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:178:
external/hal_driver/Inc/stm32f4xx_hal_i2c.h:190:3: error: unknown type name 'I2C_TypeDef'
  190 |   I2C_TypeDef                *Instance;      /*!< I2C registers base address               */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_i2c.h:198:3: error: unknown type name '__IO'
  198 |   __IO uint16_t              XferCount;      /*!< I2C transfer counter                     */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_i2c.h:198:30: error: expected ':', ',', ';', '}' or '__attribute__' before 'XferCount'
  198 |   __IO uint16_t              XferCount;      /*!< I2C transfer counter                     */
      |                              ^~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:182:
external/hal_driver/Inc/stm32f4xx_hal_i2s.h:92:3: error: unknown type name 'SPI_TypeDef'
   92 |   SPI_TypeDef                *Instance;    /*!< I2S registers base address */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_i2s.h:98:3: error: unknown type name '__IO'
   98 |   __IO uint16_t              TxXferSize;   /*!< I2S Tx transfer size */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_i2s.h:98:30: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferSize'
   98 |   __IO uint16_t              TxXferSize;   /*!< I2S Tx transfer size */
      |                              ^~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:186:
external/hal_driver/Inc/stm32f4xx_hal_irda.h:143:3: error: unknown type name 'USART_TypeDef'
  143 |   USART_TypeDef               *Instance;        /*!<  USART registers base address       */
      |   ^~~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_irda.h:151:3: error: unknown type name '__IO'
  151 |   __IO uint16_t               TxXferCount;      /*!<  IRDA Tx Transfer Counter           */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_irda.h:151:31: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferCount'
  151 |   __IO uint16_t               TxXferCount;      /*!<  IRDA Tx Transfer Counter           */
      |                               ^~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:189:
external/hal_driver/Inc/stm32f4xx_hal_iwdg.h:61:3: error: unknown type name 'IWDG_TypeDef'
   61 |   IWDG_TypeDef                 *Instance;  /*!< Register base address    */
      |   ^~~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:232:
external/hal_driver/Inc/stm32f4xx_hal_rtc.h:168:3: error: unknown type name 'RTC_TypeDef'
  168 |   RTC_TypeDef                 *Instance;  /*!< Register base address    */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_rtc.h:174:3: error: unknown type name '__IO'
  174 |   __IO HAL_RTCStateTypeDef    State;      /*!< Time communication state */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_rtc.h:174:31: error: expected ':', ',', ';', '}' or '__attribute__' before 'State'
  174 |   __IO HAL_RTCStateTypeDef    State;      /*!< Time communication state */
      |                               ^~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:248:
external/hal_driver/Inc/stm32f4xx_hal_smartcard.h:155:3: error: unknown type name 'USART_TypeDef'
  155 |   USART_TypeDef                    *Instance;        /*!< USART registers base address */
      |   ^~~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_smartcard.h:163:3: error: unknown type name '__IO'
  163 |   __IO uint16_t                    TxXferCount;      /*!< SmartCard Tx Transfer Counter */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_smartcard.h:163:36: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferCount'
  163 |   __IO uint16_t                    TxXferCount;      /*!< SmartCard Tx Transfer Counter */
      |                                    ^~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:252:
external/hal_driver/Inc/stm32f4xx_hal_smbus.h:153:3: error: unknown type name 'I2C_TypeDef'
  153 |   I2C_TypeDef                 *Instance;        /*!< SMBUS registers base address                            */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_smbus.h:161:3: error: unknown type name '__IO'
  161 |   __IO uint16_t                 XferCount;      /*!< SMBUS transfer counter                                  */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_smbus.h:161:33: error: expected ':', ',', ';', '}' or '__attribute__' before 'XferCount'
  161 |   __IO uint16_t                 XferCount;      /*!< SMBUS transfer counter                                  */
      |                                 ^~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:260:
external/hal_driver/Inc/stm32f4xx_hal_spi.h:106:3: error: unknown type name 'SPI_TypeDef'
  106 |   SPI_TypeDef                *Instance;      /*!< SPI registers base address               */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_spi.h:114:3: error: unknown type name '__IO'
  114 |   __IO uint16_t              TxXferCount;    /*!< SPI Tx Transfer Counter                  */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_spi.h:114:30: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferCount'
  114 |   __IO uint16_t              TxXferCount;    /*!< SPI Tx Transfer Counter                  */
      |                              ^~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:268:
external/hal_driver/Inc/stm32f4xx_hal_tim.h:340:3: error: unknown type name 'TIM_TypeDef'
  340 |   TIM_TypeDef                        *Instance;         /*!< Register base address                             */
      |   ^~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_tim.h:346:3: error: unknown type name '__IO'
  346 |   __IO HAL_TIM_StateTypeDef          State;             /*!< TIM operation state                               */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_tim.h:346:38: error: expected ':', ',', ';', '}' or '__attribute__' before 'State'
  346 |   __IO HAL_TIM_StateTypeDef          State;             /*!< TIM operation state                               */
      |                                      ^~~~~
external/hal_driver/Inc/stm32f4xx_hal_tim.h:2122:25: error: unknown type name 'TIM_TypeDef'; did you mean 'TIM_HandleTypeDef'?
 2122 | void TIM_Base_SetConfig(TIM_TypeDef *TIMx, const TIM_Base_InitTypeDef *Structure);
      |                         ^~~~~~~~~~~
      |                         TIM_HandleTypeDef
external/hal_driver/Inc/stm32f4xx_hal_tim.h:2123:24: error: unknown type name 'TIM_TypeDef'; did you mean 'TIM_HandleTypeDef'?
 2123 | void TIM_TI1_SetConfig(TIM_TypeDef *TIMx, uint32_t TIM_ICPolarity, uint32_t TIM_ICSelection, uint32_t TIM_ICFilter);
      |                        ^~~~~~~~~~~
      |                        TIM_HandleTypeDef
external/hal_driver/Inc/stm32f4xx_hal_tim.h:2124:24: error: unknown type name 'TIM_TypeDef'; did you mean 'TIM_HandleTypeDef'?
 2124 | void TIM_OC2_SetConfig(TIM_TypeDef *TIMx, const TIM_OC_InitTypeDef *OC_Config);
      |                        ^~~~~~~~~~~
      |                        TIM_HandleTypeDef
external/hal_driver/Inc/stm32f4xx_hal_tim.h:2125:24: error: unknown type name 'TIM_TypeDef'; did you mean 'TIM_HandleTypeDef'?
 2125 | void TIM_ETR_SetConfig(TIM_TypeDef *TIMx, uint32_t TIM_ExtTRGPrescaler,
      |                        ^~~~~~~~~~~
      |                        TIM_HandleTypeDef
external/hal_driver/Inc/stm32f4xx_hal_tim.h:2132:24: error: unknown type name 'TIM_TypeDef'; did you mean 'TIM_HandleTypeDef'?
 2132 | void TIM_CCxChannelCmd(TIM_TypeDef *TIMx, uint32_t Channel, uint32_t ChannelState);
      |                        ^~~~~~~~~~~
      |                        TIM_HandleTypeDef
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:272:
external/hal_driver/Inc/stm32f4xx_hal_uart.h:162:3: error: unknown type name 'USART_TypeDef'
  162 |   USART_TypeDef                 *Instance;        /*!< UART registers base address        */
      |   ^~~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_uart.h:170:3: error: unknown type name '__IO'
  170 |   __IO uint16_t                 TxXferCount;      /*!< UART Tx Transfer Counter           */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_uart.h:170:33: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferCount'
  170 |   __IO uint16_t                 TxXferCount;      /*!< UART Tx Transfer Counter           */
      |                                 ^~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:276:
external/hal_driver/Inc/stm32f4xx_hal_usart.h:100:3: error: unknown type name 'USART_TypeDef'
  100 |   USART_TypeDef                 *Instance;        /*!< USART registers base address        */
      |   ^~~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal_usart.h:108:3: error: unknown type name '__IO'
  108 |   __IO uint16_t                 TxXferCount;      /*!< Usart Tx Transfer Counter           */
      |   ^~~~
external/hal_driver/Inc/stm32f4xx_hal_usart.h:108:33: error: expected ':', ',', ';', '}' or '__attribute__' before 'TxXferCount'
  108 |   __IO uint16_t                 TxXferCount;      /*!< Usart Tx Transfer Counter           */
      |                                 ^~~~~~~~~~~
In file included from external/pigweed/targets/stm32f429i_disc1_stm32cube/config/stm32f4xx_hal_conf.h:280:
external/hal_driver/Inc/stm32f4xx_hal_wwdg.h:72:3: error: unknown type name 'WWDG_TypeDef'
   72 |   WWDG_TypeDef      *Instance;  /*!< Register base address */
      |   ^~~~~~~~~~~~
external/hal_driver/Inc/stm32f4xx_hal.h:204:8: error: unknown type name '__IO'
  204 | extern __IO uint32_t uwTick;
      |        ^~~~
external/hal_driver/Inc/stm32f4xx_hal.h:204:22: error: expected '=', ',', ';', 'asm' or '__attribute__' before 'uwTick'
  204 | extern __IO uint32_t uwTick;
      |                      ^~~~~~
Target //tools:flash failed to build
Use --verbose_failures to see the command lines of failed build steps.
INFO: Elapsed time: 0.776s, Critical Path: 0.35s
INFO: 25 processes: 15 internal, 10 linux-sandbox.
FAILED: Build did NOT complete successfully
ERROR: Build failed. Not running target
```

I am intentionally showing the full error messages so that you get a
high-fidelity account of my development experience :D

OK, so I see an error about needing to select a target STM32F4XX device.
pw_stm32cube_build does mention something about that:
https://pigweed.dev/pw_stm32cube_build/#stm32cube-header

It doesn't tell me explicitly what to do, though.

I eventually figure out to set it up in `.bazelrc` like this:

```
build:stm32 --copt="-DSTM32CUBE_HEADER=\"stm32f4xx.h\""  # new
```

Still getting an error about needing to select a STM32F4XX device:

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash
INFO: Build option --copt has changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/cmsis_device/BUILD.bazel:26:11: Compiling Source/Templates/system_stm32f4xx.c failed: (Exit 1): arm-none-eabi-gcc failed: error executing command (from target @cmsis_device//:default_cmsis_init) external/gcc_arm_none_eabi_toolchain/bin/arm-none-eabi-gcc -O2 -g -fno-common -fno-exceptions -ffunction-sections -fdata-sections -no-canonical-prefixes '-mcpu=cortex-m4+nofp' '-mfloat-abi=soft' ... (remaining 43 arguments skipped)

Use --sandbox_debug to see verbose messages from the sandbox and retain the sandbox build root for debugging
In file included from external/cmsis_device/Source/Templates/system_stm32f4xx.c:48:
external/cmsis_device/Include/stm32f4xx.h:174:2: error: #error "Please select first the target STM32F4xx device used in your application (in stm32f4xx.h file)"
  174 | #error "Please select first the target STM32F4xx device used in your application (in stm32f4xx.h file)"
      |  ^~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:137:1: error: unknown type name 'uint32_t'
  137 | uint32_t SystemCoreClock = 16000000;
      | ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:49:1: note: 'uint32_t' is defined in header '<stdint.h>'; did you forget to '#include <stdint.h>'?
   48 | #include "stm32f4xx.h"
  +++ |+#include <stdint.h>
   49 | 
external/cmsis_device/Source/Templates/system_stm32f4xx.c:138:7: error: unknown type name 'uint8_t'
  138 | const uint8_t AHBPrescTable[16] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 8, 9};
      |       ^~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:139:7: error: unknown type name 'uint8_t'
  139 | const uint8_t APBPrescTable[8]  = {0, 0, 0, 0, 1, 2, 3, 4};
      |       ^~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c: In function 'SystemCoreClockUpdate':
external/cmsis_device/Source/Templates/system_stm32f4xx.c:222:3: error: unknown type name 'uint32_t'
  222 |   uint32_t tmp = 0, pllvco = 0, pllp = 2, pllsource = 0, pllm = 2;
      |   ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:222:3: note: 'uint32_t' is defined in header '<stdint.h>'; did you forget to '#include <stdint.h>'?
external/cmsis_device/Source/Templates/system_stm32f4xx.c:225:9: error: 'RCC' undeclared (first use in this function)
  225 |   tmp = RCC->CFGR & RCC_CFGR_SWS;
      |         ^~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:225:9: note: each undeclared identifier is reported only once for each function it appears in
external/cmsis_device/Source/Templates/system_stm32f4xx.c:225:21: error: 'RCC_CFGR_SWS' undeclared (first use in this function)
  225 |   tmp = RCC->CFGR & RCC_CFGR_SWS;
      |                     ^~~~~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:55:26: error: 'uint32_t' undeclared (first use in this function)
   55 |   #define HSI_VALUE    ((uint32_t)16000000) /*!< Value of the Internal oscillator in Hz*/
      |                          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:230:25: note: in expansion of macro 'HSI_VALUE'
  230 |       SystemCoreClock = HSI_VALUE;
      |                         ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:55:26: note: 'uint32_t' is defined in header '<stdint.h>'; did you forget to '#include <stdint.h>'?
   55 |   #define HSI_VALUE    ((uint32_t)16000000) /*!< Value of the Internal oscillator in Hz*/
      |                          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:230:25: note: in expansion of macro 'HSI_VALUE'
  230 |       SystemCoreClock = HSI_VALUE;
      |                         ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:55:35: error: expected ')' before numeric constant
   55 |   #define HSI_VALUE    ((uint32_t)16000000) /*!< Value of the Internal oscillator in Hz*/
      |                        ~          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:230:25: note: in expansion of macro 'HSI_VALUE'
  230 |       SystemCoreClock = HSI_VALUE;
      |                         ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:51:35: error: expected ')' before numeric constant
   51 |   #define HSE_VALUE    ((uint32_t)25000000) /*!< Default value of the External oscillator in Hz */
      |                        ~          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:233:25: note: in expansion of macro 'HSE_VALUE'
  233 |       SystemCoreClock = HSE_VALUE;
      |                         ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:240:35: error: 'RCC_PLLCFGR_PLLSRC' undeclared (first use in this function)
  240 |       pllsource = (RCC->PLLCFGR & RCC_PLLCFGR_PLLSRC) >> 22;
      |                                   ^~~~~~~~~~~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:241:29: error: 'RCC_PLLCFGR_PLLM' undeclared (first use in this function)
  241 |       pllm = RCC->PLLCFGR & RCC_PLLCFGR_PLLM;
      |                             ^~~~~~~~~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:51:35: error: expected ')' before numeric constant
   51 |   #define HSE_VALUE    ((uint32_t)25000000) /*!< Default value of the External oscillator in Hz */
      |                        ~          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:246:19: note: in expansion of macro 'HSE_VALUE'
  246 |         pllvco = (HSE_VALUE / pllm) * ((RCC->PLLCFGR & RCC_PLLCFGR_PLLN) >> 6);
      |                   ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:246:56: error: 'RCC_PLLCFGR_PLLN' undeclared (first use in this function)
  246 |         pllvco = (HSE_VALUE / pllm) * ((RCC->PLLCFGR & RCC_PLLCFGR_PLLN) >> 6);
      |                                                        ^~~~~~~~~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:55:35: error: expected ')' before numeric constant
   55 |   #define HSI_VALUE    ((uint32_t)16000000) /*!< Value of the Internal oscillator in Hz*/
      |                        ~          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:251:19: note: in expansion of macro 'HSI_VALUE'
  251 |         pllvco = (HSI_VALUE / pllm) * ((RCC->PLLCFGR & RCC_PLLCFGR_PLLN) >> 6);
      |                   ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:254:32: error: 'RCC_PLLCFGR_PLLP' undeclared (first use in this function)
  254 |       pllp = (((RCC->PLLCFGR & RCC_PLLCFGR_PLLP) >>16) + 1 ) *2;
      |                                ^~~~~~~~~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:55:35: error: expected ')' before numeric constant
   55 |   #define HSI_VALUE    ((uint32_t)16000000) /*!< Value of the Internal oscillator in Hz*/
      |                        ~          ^~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:258:25: note: in expansion of macro 'HSI_VALUE'
  258 |       SystemCoreClock = HSI_VALUE;
      |                         ^~~~~~~~~
external/cmsis_device/Source/Templates/system_stm32f4xx.c:263:37: error: 'RCC_CFGR_HPRE' undeclared (first use in this function)
  263 |   tmp = AHBPrescTable[((RCC->CFGR & RCC_CFGR_HPRE) >> 4)];
      |                                     ^~~~~~~~~~~~~
Target //tools:flash failed to build
Use --verbose_failures to see the command lines of failed build steps.
INFO: Elapsed time: 0.456s, Critical Path: 0.23s
INFO: 17 processes: 14 internal, 3 linux-sandbox.
FAILED: Build did NOT complete successfully
ERROR: Build failed. Not running target
```

I actually don't even know how I figured out this next part. It's from my
first attempt but I don't see it in the pw_stm32cube_build doc. I passed
a flag to the compiler telling it what STM32F4XX device I'm using:

```
build:stm32 --copt="-DSTM32F429xx"  # new
```

And then at this point I start getting failures because of warnings being
treated as errors:

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash
INFO: Build option --copt has changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
ERROR: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/hal_driver/BUILD.bazel:52:11: Compiling Src/stm32f4xx_hal_timebase_tim_template.c failed: (Exit 1): arm-none-eabi-gcc failed: error executing command (from target @hal_driver//:default_timebase) external/gcc_arm_none_eabi_toolchain/bin/arm-none-eabi-gcc -O2 -g -fno-common -fno-exceptions -ffunction-sections -fdata-sections -no-canonical-prefixes '-mcpu=cortex-m4+nofp' '-mfloat-abi=soft' ... (remaining 65 arguments skipped)

Use --sandbox_debug to see verbose messages from the sandbox and retain the sandbox build root for debugging
external/hal_driver/Src/stm32f4xx_hal_timebase_tim_template.c: In function 'HAL_TIM_PeriodElapsedCallback':
external/hal_driver/Src/stm32f4xx_hal_timebase_tim_template.c:155:55: error: unused parameter 'htim' [-Werror=unused-parameter]
  155 | void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
      |                                    ~~~~~~~~~~~~~~~~~~~^~~~
cc1: all warnings being treated as errors
Target //tools:flash failed to build
Use --verbose_failures to see the command lines of failed build steps.
INFO: Elapsed time: 1.315s, Critical Path: 1.01s
INFO: 51 processes: 14 internal, 37 linux-sandbox.
FAILED: Build did NOT complete successfully
ERROR: Build failed. Not running target
```

Well, I just want to get this to compile and run. I don't need it perfect
yet. It looks like I'm using `arm-none-eabi-gcc`, can I just turn off that
"treat warnings as errors" feature?

(On my first attempt I tried many different things for an hour or two and
nothing seemed to work. On this second attempt I discovered the `-w` flag
and that seemed to do the trick.)

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash --copt="-w"
INFO: Build option --copt has changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
INFO: From Linking src/echo:
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-closer.o): in function `_close_r':
closer.c:(.text._close_r+0xc): warning: _close is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-signalr.o): in function `_getpid_r':
signalr.c:(.text._getpid_r+0x0): warning: _getpid is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-signalr.o): in function `_kill_r':
signalr.c:(.text._kill_r+0xe): warning: _kill is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-lseekr.o): in function `_lseek_r':
lseekr.c:(.text._lseek_r+0x10): warning: _lseek is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-readr.o): in function `_read_r':
readr.c:(.text._read_r+0x10): warning: _read is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-writer.o): in function `_write_r':
writer.c:(.text._write_r+0x10): warning: _write is not implemented and will always fail
Target //tools:flash up-to-date:
  bazel-bin/tools/flash
INFO: Elapsed time: 3.972s, Critical Path: 1.42s
INFO: 122 processes: 2 internal, 120 linux-sandbox.
INFO: Build completed successfully, 122 total actions
INFO: Running command line: bazel-bin/tools/flash
binary Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/execroot/__main__/bazel-out/k8-fastbuild/bin/src/echo.elf
openocd Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/openocd/bin/openocd
openocd config Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/targets/stm32f429i_disc1/py/stm32f429i_disc1_utils/openocd_stm32f4xx.cfg
xPack OpenOCD x86_64 Open On-Chip Debugger 0.11.0+dev (2021-12-07-17:30)
Licensed under GNU GPL v2
For bug reports, read
	http://openocd.org/doc/doxygen/bugs.html
DEPRECATED! use 'adapter driver' not 'interface'
DEPRECATED! use 'adapter serial' not 'hla_serial'
Info : The selected transport took over low-level target control. The results might differ compared to plain JTAG/SWD
srst_only separate srst_nogate srst_open_drain connect_deassert_srst

Info : clock speed 2000 kHz
Info : STLINK V2J36M26 (API v2) VID:PID 0483:374B
Info : Target voltage: 2.866822
Info : stm32f4x.cpu: Cortex-M4 r0p1 processor detected
Info : stm32f4x.cpu: target has 6 breakpoints, 4 watchpoints
Info : gdb port disabled
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
target halted due to debug-request, current mode: Thread 
xPSR: 0x01000000 pc: 0x0800055c msp: 0x20030000
Info : Unable to match requested speed 8000 kHz, using 4000 kHz
Info : Unable to match requested speed 8000 kHz, using 4000 kHz
** Programming Started **
Info : device id = 0x20036419
Info : flash size = 2048 kbytes
Info : Dual Bank 2048 kiB STM32F42x/43x/469/479 found
Info : Padding image section 0 at 0x08000010 with 496 bytes
** Programming Finished **
** Resetting Target **
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
shutdown command invoked
```

I didn't get this far on my first attempt! This is all uncharted territory for
me now.

OK, first things first, is the echo app still working??

```
kayce@kayce0:~/repos/cube$ bazel run //tools:miniterm -- /dev/ttyACM0 --filter=debug
INFO: Build options --@hal_driver//:hal_config and --copt have changed, discarding analysis cache.
INFO: Analyzed target //tools:miniterm (0 packages loaded, 8946 targets configured).
INFO: Found 1 target...
Target //tools:miniterm up-to-date:
  bazel-bin/tools/miniterm
INFO: Elapsed time: 0.275s, Critical Path: 0.06s
INFO: 4 processes: 4 internal.
INFO: Build completed successfully, 4 total actions
INFO: Running command line: bazel-bin/tools/miniterm /dev/ttyACM0 '--filter=debug'
--- Miniterm on /dev/ttyACM0  115200,8,N,1 ---
--- Quit: Ctrl+] | Menu: Ctrl+T | Help: Ctrl+T followed by Ctrl+H ---
 [TX:'a']  [RX:'a'] a [TX:'b']  [RX:'b'] b [TX:'c']  [RX:'c'] c [TX:'x']  [RX:'x'] x
--- exit ---
```

Woohoo, still good.

Can I call one of the HAL functions???? 

```
#include <cstddef>

#include "pw_sys_io/sys_io.h"
#include "stm32f4xx.h"

int main() {
  HAL_Init();  // new
  while (true) {
    std::byte data;
    pw::sys_io::ReadByte(&data).IgnoreError();
    std::byte c = (std::byte) 'c';  // new
    pw::sys_io::WriteByte(c).IgnoreError();  // new
  }
  return 0;
}
```

(Build and flash commands succeed.)

But now the echo app is now longer echo'ing:

```
kayce@kayce0:~/repos/cube$ bazel run //tools:miniterm -- /dev/ttyACM0 --filter=debug
INFO: Build options --@hal_driver//:hal_config and --copt have changed, discarding analysis cache.
INFO: Analyzed target //tools:miniterm (0 packages loaded, 8946 targets configured).
INFO: Found 1 target...
Target //tools:miniterm up-to-date:
  bazel-bin/tools/miniterm
INFO: Elapsed time: 0.261s, Critical Path: 0.07s
INFO: 4 processes: 4 internal.
INFO: Build completed successfully, 4 total actions
INFO: Running command line: bazel-bin/tools/miniterm /dev/ttyACM0 '--filter=debug'
--- Miniterm on /dev/ttyACM0  115200,8,N,1 ---
--- Quit: Ctrl+] | Menu: Ctrl+T | Help: Ctrl+T followed by Ctrl+H ---
 [TX:'a']  [TX:'g']  [TX:'s'] 
--- exit ---
```

I eventually figure out that I'm probably messing up the `pw_sys_io` init
logic. E.g. `pw_sys_io` inits before my `main()` and then when I call
`HAL_Init()` within `main()` it messes up the UART hardware settings. So I
guess I should recall the `pw_sys_io` init function from within my `main()`?

I have to muck around the `pw_sys_io_baremetal_stm32f429` source code and
eventually figure out what looks like the init function I need:
`pw_sys_io_stm32f429_Init()`

Can I just call that from my app code or do I need to bring in another include?

```
#include <cstddef>

#include "pw_sys_io/sys_io.h"
#include "stm32f4xx.h"

int main() {
  HAL_Init();
  pw_sys_io_stm32f429_Init();  // new
  while (true) {
    std::byte data;
    pw::sys_io::ReadByte(&data).IgnoreError();
    std::byte c = (std::byte) 'c';  // new
    pw::sys_io::WriteByte(c).IgnoreError();  // new
  }
  return 0;
}
```

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash --copt="-w"
INFO: Build options --@hal_driver//:hal_config, --copt, and --platforms have changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
ERROR: /home/kayce/repos/cube/src/BUILD.bazel:18:10: Compiling src/echo.cc failed: (Exit 1): arm-none-eabi-g++ failed: error executing command (from target //src:echo) external/gcc_arm_none_eabi_toolchain/bin/arm-none-eabi-g++ -O2 '-std=c++17' -g -fno-common -fno-exceptions -ffunction-sections -fdata-sections -no-canonical-prefixes -fno-rtti -Wno-register ... (remaining 174 arguments skipped)

Use --sandbox_debug to see verbose messages from the sandbox and retain the sandbox build root for debugging
src/echo.cc: In function 'int main()':
src/echo.cc:22:3: error: 'pw_sys_io_stm32f429_Init' was not declared in this scope
   22 |   pw_sys_io_stm32f429_Init();
      |   ^~~~~~~~~~~~~~~~~~~~~~~~
Target //tools:flash failed to build
Use --verbose_failures to see the command lines of failed build steps.
INFO: Elapsed time: 0.597s, Critical Path: 0.36s
INFO: 2 processes: 2 internal.
FAILED: Build did NOT complete successfully
ERROR: Build failed. Not running target
```

`//targets/BUILD.bazel` says that `@pigweed//pw_sys_io_baremetal_stm32f429:backend`
is already a constraint value so I'm kinda expecting it to already work.

Let me try to guess at the include for this function:

```
#include <cstddef>

#include "pw_sys_io/sys_io.h"
#include "pw_sys_io_baremetal_stm32f429/init.h"
#include "stm32f4xx.h"

int main() {
  HAL_Init();
  pw_sys_io_stm32f429_Init();  // new
  while (true) {
    std::byte data;
    pw::sys_io::ReadByte(&data).IgnoreError();
    std::byte c = (std::byte) 'c';  // new
    pw::sys_io::WriteByte(c).IgnoreError();  // new
  }
  return 0;
}
```

Still builds OK:

```
kayce@kayce0:~/repos/cube$ bazel build --platforms=//targets:stm32 //...
INFO: Build options --@hal_driver//:hal_config, --copt, and --platforms have changed, discarding analysis cache.
INFO: Analyzed 7 targets (0 packages loaded, 11798 targets configured).
INFO: Found 7 targets...
INFO: Elapsed time: 0.194s, Critical Path: 0.00s
INFO: 1 process: 1 internal.
INFO: Build completed successfully, 1 total action
```

Now it flashed OK too:

```
kayce@kayce0:~/repos/cube$ bazel run --config=stm32 //tools:flash --copt="-w"
INFO: Build options --@hal_driver//:hal_config, --copt, and --platforms have changed, discarding analysis cache.
INFO: Analyzed target //tools:flash (0 packages loaded, 13311 targets configured).
INFO: Found 1 target...
INFO: From Linking src/echo:
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-closer.o): in function `_close_r':
closer.c:(.text._close_r+0xc): warning: _close is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-signalr.o): in function `_getpid_r':
signalr.c:(.text._getpid_r+0x0): warning: _getpid is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-signalr.o): in function `_kill_r':
signalr.c:(.text._kill_r+0xe): warning: _kill is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-lseekr.o): in function `_lseek_r':
lseekr.c:(.text._lseek_r+0x10): warning: _lseek is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-readr.o): in function `_read_r':
readr.c:(.text._read_r+0x10): warning: _read is not implemented and will always fail
/home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/bin/ld: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/gcc_arm_none_eabi_toolchain/bin/../lib/gcc/arm-none-eabi/12.2.1/../../../../arm-none-eabi/lib/thumb/v7e-m/nofp/libc_nano.a(libc_a-writer.o): in function `_write_r':
writer.c:(.text._write_r+0x10): warning: _write is not implemented and will always fail
Target //tools:flash up-to-date:
  bazel-bin/tools/flash
INFO: Elapsed time: 0.603s, Critical Path: 0.38s
INFO: 4 processes: 2 internal, 2 linux-sandbox.
INFO: Build completed successfully, 4 total actions
INFO: Running command line: bazel-bin/tools/flash
binary Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/execroot/__main__/bazel-out/k8-fastbuild/bin/src/echo.elf
openocd Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/openocd/bin/openocd
openocd config Rlocation is: /home/kayce/.cache/bazel/_bazel_kayce/12a041d3d86433b9db8348eb84f223b8/external/pigweed/targets/stm32f429i_disc1/py/stm32f429i_disc1_utils/openocd_stm32f4xx.cfg
xPack OpenOCD x86_64 Open On-Chip Debugger 0.11.0+dev (2021-12-07-17:30)
Licensed under GNU GPL v2
For bug reports, read
	http://openocd.org/doc/doxygen/bugs.html
DEPRECATED! use 'adapter driver' not 'interface'
DEPRECATED! use 'adapter serial' not 'hla_serial'
Info : The selected transport took over low-level target control. The results might differ compared to plain JTAG/SWD
srst_only separate srst_nogate srst_open_drain connect_deassert_srst

Info : clock speed 2000 kHz
Info : STLINK V2J36M26 (API v2) VID:PID 0483:374B
Info : Target voltage: 2.866822
Info : stm32f4x.cpu: Cortex-M4 r0p1 processor detected
Info : stm32f4x.cpu: target has 6 breakpoints, 4 watchpoints
Info : gdb port disabled
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
target halted due to debug-request, current mode: Thread 
xPSR: 0x01000000 pc: 0x08000560 msp: 0x20030000
Info : Unable to match requested speed 8000 kHz, using 4000 kHz
Info : Unable to match requested speed 8000 kHz, using 4000 kHz
** Programming Started **
Info : device id = 0x20036419
Info : flash size = 2048 kbytes
Info : Dual Bank 2048 kiB STM32F42x/43x/469/479 found
Info : Padding image section 0 at 0x08000010 with 496 bytes
** Programming Finished **
** Resetting Target **
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
Info : Unable to match requested speed 2000 kHz, using 1800 kHz
shutdown command invoked
```

The echo is still broken though:

```
kayce@kayce0:~/repos/cube$ bazel run //tools:miniterm -- /dev/ttyACM0 --filter=debug
INFO: Build options --@hal_driver//:hal_config and --copt have changed, discarding analysis cache.
INFO: Analyzed target //tools:miniterm (0 packages loaded, 8946 targets configured).
INFO: Found 1 target...
Target //tools:miniterm up-to-date:
  bazel-bin/tools/miniterm
INFO: Elapsed time: 0.241s, Critical Path: 0.06s
INFO: 4 processes: 4 internal.
INFO: Build completed successfully, 4 total actions
INFO: Running command line: bazel-bin/tools/miniterm /dev/ttyACM0 '--filter=debug'
--- Miniterm on /dev/ttyACM0  115200,8,N,1 ---
--- Quit: Ctrl+] | Menu: Ctrl+T | Help: Ctrl+T followed by Ctrl+H ---
 [TX:'a']  [TX:'g'] 
```

At this point it's time to give up on this journey and go home!
