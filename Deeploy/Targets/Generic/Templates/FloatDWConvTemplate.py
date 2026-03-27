# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

from Deeploy.DeeployTypes import NodeTemplate

reference2DTemplate = NodeTemplate("""
<%
batchOffsetIn = ch_im_in * dim_im_in_x * dim_im_in_y
batchOffsetOut = ch_im_out * dim_im_out_x * dim_im_out_y
%>
// 2D FP Depth-wise Conv (Name: ${nodeName}, Op: ${nodeOp})
BEGIN_SINGLE_CORE
    ${data_in_type.typeName} ref_${data_out}_${data_in} = ${data_in};
    ${data_out_type.typeName} ref_${data_out}_${data_out} = ${data_out};
    for (uint32_t n=0; n<${batch}; ++n) {
        DWConv2d_fp${data_in_type.referencedType.typeWidth}_fp${weight_type.referencedType.typeWidth}_fp${data_out_type.referencedType.typeWidth}_NCHW(
            ref_${data_out}_${data_in},
            ${ch_im_in}, ${dim_im_in_x}, ${dim_im_in_y},
            ${weight},
            ${ch_im_out}, ${dim_kernel_x}, ${dim_kernel_y},
            ${stride_x}, ${stride_y},
            ${bias},
            ${has_bias},
            ref_${data_out}_${data_out}
        );
        ref_${data_out}_${data_in} += ${batchOffsetIn};
        ref_${data_out}_${data_out} += ${batchOffsetOut};
    }
END_SINGLE_CORE
""")

reference1DTemplate = NodeTemplate("""
<%
batchOffsetIn = ch_im_in * dim_im_in_y
batchOffsetOut = ch_im_out * dim_im_out_y
chMultiplier = ch_im_out // ch_im_in
%>
// 1D FP Depth-wise Conv (Name: ${nodeName}, Op: ${nodeOp})
BEGIN_SINGLE_CORE
    ${data_in_type.typeName} ref_${data_out}_${data_in} = ${data_in};
    ${data_out_type.typeName} ref_${data_out}_${data_out} = ${data_out};
    for (uint32_t n=0; n<${batch}; ++n) {
        for (uint32_t oc=0; oc<${ch_im_out}; ++oc) {
            uint32_t ic = oc / ${chMultiplier};
            for (uint32_t oy=0; oy<${dim_im_out_y}; ++oy) {
                ${data_out_type.referencedType.typeName} acc = 0;
                if (${has_bias}) {
                    acc = ${bias}[oc];
                }
                for (uint32_t ky=0; ky<${dim_kernel_y}; ++ky) {
                    int32_t iy = (int32_t)oy * ${stride_y} + (int32_t)ky - ${padding_y};
                    if (iy >= 0 && iy < ${dim_im_in_y}) {
                        acc += ref_${data_out}_${data_in}[ic * ${dim_im_in_y} + iy] * ${weight}[oc * ${dim_kernel_y} + ky];
                    }
                }
                ref_${data_out}_${data_out}[oc * ${dim_im_out_y} + oy] = acc;
            }
        }
        ref_${data_out}_${data_in} += ${batchOffsetIn};
        ref_${data_out}_${data_out} += ${batchOffsetOut};
    }
END_SINGLE_CORE
""")