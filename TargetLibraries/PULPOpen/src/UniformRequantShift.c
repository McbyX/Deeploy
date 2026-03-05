/*
 * SPDX-FileCopyrightText: 2024 ETH Zurich and University of Bologna
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "DeeployPULPMath.h"
#include "pmsis.h"

#define DEFINE_UNIFORM_RQS(IN_T, IN_TAG, OUT_T, OUT_TAG)                               \
  void UniformRequantShift_##IN_TAG##_##OUT_TAG(                                        \
      IN_T *data_in, int32_t size, int32_t mul, int32_t add, OUT_T *data_out,          \
      int32_t log2D, int32_t HW, int32_t input_offset, int32_t output_offset,          \
      OUT_T output_min, OUT_T output_max, bool rounding) {                             \
                                                                                         \
    int8_t core_id = pi_core_id();                                                      \
    int8_t log2Core = LOG2(NUM_CORES);                                                  \
    int16_t chunk = (size >> log2Core) + ((size & (NUM_CORES - 1)) != 0);              \
    int16_t chunk_start = MIN(chunk * core_id, size);                                   \
    int16_t chunk_stop = MIN(chunk_start + chunk, size + 1);                            \
                                                                                         \
    /* JUNGVI: Compiler magic, don't remove the volatile keyword below */               \
    int32_t volatile halfChunkSize = chunk >> 1;                                        \
    int32_t intermediate;                                                                \
    OUT_T out;                                                                           \
    IN_T reg_data_in_A;                                                                  \
    IN_T reg_data_in_B;                                                                  \
                                                                                         \
    /* Load step 0 */                                                                    \
    reg_data_in_A = data_in[chunk_start];                                               \
                                                                                         \
    for (int i = chunk_start; i < chunk_start + halfChunkSize; i++) {                   \
                                                                                         \
      /* Load step halfChunkSize + i */                                                 \
      reg_data_in_B = data_in[halfChunkSize + i];                                       \
                                                                                         \
      /* Compute i */                                                                    \
      intermediate = (reg_data_in_A + input_offset) * mul + add;                        \
      intermediate =                                                                     \
          ((intermediate + ((1 << (log2D - 1))) * rounding) >> log2D) + output_offset; \
      out = (OUT_T)CLAMP(intermediate, output_min, output_max);                         \
      data_out[i] = out;                                                                 \
                                                                                         \
      /* Load step i + 1 */                                                             \
      reg_data_in_A = data_in[i + 1];                                                   \
                                                                                         \
      /* Compute step halfChunkSize + i */                                              \
      intermediate = (reg_data_in_B + input_offset) * mul + add;                        \
      intermediate =                                                                     \
          ((intermediate + ((1 << (log2D - 1))) * rounding) >> log2D) + output_offset; \
      out = (OUT_T)CLAMP(intermediate, output_min, output_max);                         \
      data_out[halfChunkSize + i] = out;                                                 \
    }                                                                                    \
                                                                                         \
    /* Leftover computation */                                                           \
    if ((chunk_stop - chunk_start) % 2) {                                               \
                                                                                         \
      reg_data_in_B = data_in[chunk_stop - 1];                                          \
      reg_data_in_A = data_in[chunk_stop];                                              \
                                                                                         \
      intermediate = (reg_data_in_B + input_offset) * mul + add;                        \
      intermediate =                                                                     \
          ((intermediate + ((1 << (log2D - 1))) * rounding) >> log2D) + output_offset; \
      out = (OUT_T)CLAMP(intermediate, output_min, output_max);                         \
      data_out[chunk_stop - 1] = out;                                                   \
                                                                                         \
      intermediate = (reg_data_in_A + input_offset) * mul + add;                        \
      intermediate =                                                                     \
          ((intermediate + ((1 << (log2D - 1))) * rounding) >> log2D) + output_offset; \
      out = (OUT_T)CLAMP(intermediate, output_min, output_max);                         \
      data_out[chunk_stop] = out;                                                       \
    }                                                                                    \
  }

DEFINE_UNIFORM_RQS(int8_t, s8, int8_t, s8)
DEFINE_UNIFORM_RQS(uint8_t, u8, int8_t, s8)
DEFINE_UNIFORM_RQS(int16_t, s16, int8_t, s8)
DEFINE_UNIFORM_RQS(int32_t, s32, int8_t, s8)
DEFINE_UNIFORM_RQS(int8_t, s8, uint8_t, u8)
DEFINE_UNIFORM_RQS(uint8_t, u8, uint8_t, u8)
DEFINE_UNIFORM_RQS(int16_t, s16, uint8_t, u8)
DEFINE_UNIFORM_RQS(int32_t, s32, uint8_t, u8)

#undef DEFINE_UNIFORM_RQS
