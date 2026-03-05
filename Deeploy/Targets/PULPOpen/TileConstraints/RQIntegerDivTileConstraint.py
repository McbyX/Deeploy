# SPDX-FileCopyrightText: 2026 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

from typing import Dict, List, Tuple

import numpy as np

from Deeploy.AbstractDataTypes import PointerClass
from Deeploy.CommonExtensions.DataTypes import uint16_t
from Deeploy.DeeployTypes import NetworkContext, OperatorRepresentation
from Deeploy.TilingExtension.MemoryConstraints import NodeMemoryConstraint
from Deeploy.TilingExtension.TileConstraint import TileConstraint
from Deeploy.TilingExtension.TilerModel import TilerModel
from Deeploy.TilingExtension.TilingCodegen import AbsoluteHyperRectangle, HyperRectangle, TilingSchedule, \
    VariableReplacementScheme


class RQIntegerDivTileConstraint(TileConstraint):

    @staticmethod
    def addGeometricalConstraint(tilerModel: TilerModel, parseDict: Dict, ctxt: NetworkContext) -> TilerModel:
        inputA = parseDict['A']
        inputB = parseDict['B']
        requantMul = parseDict['requant_mul']
        requantAdd = parseDict['requant_add']
        requantDiv = parseDict['requant_div']
        outputC = parseDict['C']

        for bufferName in [inputA, inputB, requantMul, requantAdd, requantDiv, outputC]:
            tilerModel.addTensorDimToModel(ctxt, bufferName)

        aShape = ctxt.lookup(inputA).shape
        for dimIdx in range(len(aShape)):
            aVar = tilerModel.getTensorDimVar(inputA, dimIdx)
            bVar = tilerModel.getTensorDimVar(inputB, dimIdx)
            cVar = tilerModel.getTensorDimVar(outputC, dimIdx)
            tilerModel.addConstraint(aVar == bVar)
            tilerModel.addConstraint(aVar == cVar)

        # Keep requant tensors untiled (typically scalar/per-channel constants)
        for bufferName in [requantMul, requantAdd, requantDiv]:
            shape = ctxt.lookup(bufferName).shape
            for dimIdx, dimSize in enumerate(shape):
                dimVar = tilerModel.getTensorDimVar(bufferName, dimIdx)
                tilerModel.addConstraint(dimVar == dimSize)

        return tilerModel

    @classmethod
    def serializeTilingSolution(
            cls, tilingSolution: NodeMemoryConstraint, absoluteOutputCubes: List[AbsoluteHyperRectangle],
            targetMemLevel: str, ctxt: NetworkContext,
            operatorRepresentation: OperatorRepresentation) -> Tuple[VariableReplacementScheme, TilingSchedule]:
        outputCubes = [cube.rectangle for cube in absoluteOutputCubes]

        addrNames = ['A', 'B', 'requant_mul', 'requant_add', 'requant_div', 'C']
        inputBaseOffsets, outputBaseOffsets = cls.extractBaseAddr(tilingSolution, targetMemLevel, operatorRepresentation,
                                                                  addrNames)

        mulShape = tuple(ctxt.lookup(operatorRepresentation['requant_mul']).shape)
        addShape = tuple(ctxt.lookup(operatorRepresentation['requant_add']).shape)
        divShape = tuple(ctxt.lookup(operatorRepresentation['requant_div']).shape)

        mulCube = HyperRectangle((0,) * len(mulShape), mulShape)
        addCube = HyperRectangle((0,) * len(addShape), addShape)
        divCube = HyperRectangle((0,) * len(divShape), divShape)

        replacements = {"size": []}
        replacementTypes = {"size": PointerClass(uint16_t)}

        inputLoadSchedule = []
        outputLoadSchedule = []

        for cube in outputCubes:
            replacements['size'].append(np.prod(cube.dims))
            inputLoadSchedule.append({
                'A': cube,
                'B': cube,
                'requant_mul': mulCube,
                'requant_add': addCube,
                'requant_div': divCube,
            })
            outputLoadSchedule.append({'C': cube})

        tilingSchedule = TilingSchedule(inputBaseOffsets, outputBaseOffsets, inputLoadSchedule, outputLoadSchedule)
        variableReplacement = VariableReplacementScheme(replacements, replacementTypes)
        return variableReplacement, tilingSchedule

