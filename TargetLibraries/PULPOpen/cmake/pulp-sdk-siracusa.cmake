# SPDX-FileCopyrightText: 2024 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

include(cmake/pulp-sdk-base.cmake)

set(PULP_SDK_HOME $ENV{PULP_SDK_HOME})

set(SIRACUSA_COMPILE_FLAGS
  -include ${PULP_SDK_HOME}/rtos/pulpos/pulp/include/pos/chips/siracusa/config.h
  -DCONFIG_SIRACUSA
  -DCONFIG_BOARD_VERSION_SIRACUSA
  -DCONFIG_PROFILE_SIRACUSA
  -DSKIP_PLL_INIT
  -DUSE_HYPERFLASH
  -DUSE_HYPERRAM
  -DPULP_CHIP_STR=siracusa
)

set(SIRACUSA_INCLUDES
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/include/pos/chips/siracusa
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/drivers/i3c/include
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/drivers/siracusa_padmux/include
)

set(PULP_SDK_SIRACUSA_C_SOURCE
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/kernel/chips/siracusa/pll.c
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/kernel/chips/siracusa/soc.c
  ${PULP_SDK_HOME}/rtos/pulpos/pulp/drivers/siracusa_padmux/src/siracusa_padctrl.c
)

set_source_files_properties(${PULP_SDK_SIRACUSA_ASM_SOURCE} PROPERTIES COMPILE_FLAGS -DLANGUAGE_ASSEMBLY)
add_library(pulp-sdk OBJECT ${PULP_SDK_BASE_C_SOURCE} ${PULP_SDK_BASE_ASM_SOURCE} ${PULP_SDK_SIRACUSA_C_SOURCE} ${PULP_SDK_SIRACUSA_ASM_SOURCE})

set(PULP_SDK_COMPILE_FLAGS ${SIRACUSA_COMPILE_FLAGS} ${PULP_SDK_BASE_COMPILE_FLAGS})
set(PULP_SDK_INCLUDES ${SIRACUSA_INCLUDES} ${PULP_SDK_BASE_INCLUDE})

target_include_directories(pulp-sdk SYSTEM PUBLIC ${PULP_SDK_INCLUDES})
target_compile_options(pulp-sdk PUBLIC ${PULP_SDK_COMPILE_FLAGS})
target_compile_options(pulp-sdk PRIVATE
  -Wno-sign-conversion
  -Wno-unused-function
  -Wno-unused-parameter
  -Wno-conversion
  -Wno-sign-conversion
  -Wno-unused-variable
  -Wno-sign-compare
  -Wno-return-type
  -fno-inline-functions
)
target_compile_options(pulp-sdk INTERFACE
  -Wno-unused-function
)


# Work around L1 pi_malloc section-table overflows on large/generated workloads.
# These symbols are consumed by Siracusa linker scripts in some PULP-SDK versions.
# Keep them configurable to avoid hard-coding platform assumptions.
set(siracusa_l1_section_table_size 0x1000 CACHE STRING "Override Siracusa L1 section-table size used by linker script")
set(siracusa_link_script ${CMAKE_CURRENT_LIST_DIR}/../linker/chips/siracusa/link.ld CACHE STRING "Siracusa linker script path")

set(SIRACUSA_LINK_SYMBOL_OVERRIDES
  -Wl,--defsym=__l1_section_table_size=${siracusa_l1_section_table_size}
)

set(SIRACUSA_LINK_OPTIONS
  -Wl,--gc-sections
  -L${PULP_SDK_HOME}/rtos/pulpos/pulp/kernel
  -T${siracusa_link_script}
  ${SIRACUSA_LINK_SYMBOL_OVERRIDES}
)

target_link_libraries(pulp-sdk PUBLIC
  ${SIRACUSA_LINK_OPTIONS}
)
