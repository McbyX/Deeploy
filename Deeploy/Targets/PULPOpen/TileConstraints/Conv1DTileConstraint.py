# SPDX-FileCopyrightText: 2026 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

from typing import Dict, List, Tuple

from Deeploy.DeeployTypes import NetworkContext, OperatorRepresentation
from Deeploy.TilingExtension.MemoryConstraints import NodeMemoryConstraint
from Deeploy.TilingExtension.TileConstraint import TileConstraint
from Deeploy.TilingExtension.TilerModel import TilerModel
from Deeploy.TilingExtension.TilingCodegen import AbsoluteHyperRectangle, HyperRectangle, TilingSchedule, \
    VariableReplacementScheme


class RQConv1DTileConstraint(TileConstraint):

    @staticmethod
    def constructSymbolicNodeRep(tilerModel: TilerModel, parseDict: Dict, ctxt: NetworkContext) -> Dict:
        _ = tilerModel
        _ = ctxt
        # 1D conv transient-buffer sizing depends on parser attributes (e.g. pads, dim_kernel_y).
        return parseDict

    @staticmethod
    def addGeometricalConstraint(tilerModel: TilerModel, parseDict: Dict, ctxt: NetworkContext) -> TilerModel:
        # Keep 1D RQ conv untiled for now: enforce full-tensor cubes for all tensors used by the kernel.
        for tensorKey in ['data_in', 'weight', 'mul', 'add', 'data_out']:
            tensorName = parseDict[tensorKey]
            buffer = ctxt.lookup(tensorName)
            tilerModel.addTensorDimToModel(ctxt, tensorName)
            for dimIdx, dimSize in enumerate(buffer.shape):
                dimVar = tilerModel.getTensorDimVar(tensorName = tensorName, dimIdx = dimIdx)
                tilerModel.addConstraint(dimVar == dimSize)

        return tilerModel

    @classmethod
    def serializeTilingSolution(
            cls, tilingSolution: NodeMemoryConstraint, absoluteOutputCubes: List[AbsoluteHyperRectangle],
            targetMemLevel: str, ctxt: NetworkContext,
            operatorRepresentation: OperatorRepresentation) -> Tuple[VariableReplacementScheme, TilingSchedule]:

        outputCubes = [cube.rectangle for cube in absoluteOutputCubes]

        addrNames = ['data_in', 'weight', 'mul', 'add', 'data_out']
        inputBaseOffsets, outputBaseOffsets = cls.extractBaseAddr(tilingSolution, targetMemLevel, operatorRepresentation,
                                                                  addrNames)

        dataInShape = tuple(ctxt.lookup(operatorRepresentation['data_in']).shape)
        weightShape = tuple(ctxt.lookup(operatorRepresentation['weight']).shape)
        mulShape = tuple(ctxt.lookup(operatorRepresentation['mul']).shape)
        addShape = tuple(ctxt.lookup(operatorRepresentation['add']).shape)

        fullDataInCube = HyperRectangle((0,) * len(dataInShape), dataInShape)
        fullWeightCube = HyperRectangle((0,) * len(weightShape), weightShape)
        fullMulCube = HyperRectangle((0,) * len(mulShape), mulShape)
        fullAddCube = HyperRectangle((0,) * len(addShape), addShape)

        inputLoadSchedule = []
        outputLoadSchedule = []

        for out in outputCubes:
            inputLoadSchedule.append({
                "data_in": fullDataInCube,
                "weight": fullWeightCube,
                "mul": fullMulCube,
                "add": fullAddCube,
            })
            outputLoadSchedule.append({"data_out": out})

        tilingSchedule = TilingSchedule(inputBaseOffsets, outputBaseOffsets, inputLoadSchedule, outputLoadSchedule)
        variableReplacement = VariableReplacementScheme({}, {})

        return variableReplacement, tilingSchedule


class RQDWConv1DTileConstraint(RQConv1DTileConstraint):
    pass
