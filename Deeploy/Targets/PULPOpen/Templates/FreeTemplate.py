from Deeploy.DeeployTypes import NodeTemplate


pulpL2LocalTemplate = NodeTemplate("""
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L2] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
pi_l2_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
""")
pulpL2GlobalTemplate = NodeTemplate("""
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L2] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
pi_l2_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
""")
pulpL1FreeTemplate = NodeTemplate("""
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L1] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
pmsis_l1_malloc_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
""")
pulpL1GlobalFreeTemplate = NodeTemplate("")

pulpGenericFree = NodeTemplate("""
% if _memoryLevel == "L1":
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L1] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
pmsis_l1_malloc_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
% elif _memoryLevel == "L2" or _memoryLevel is None:
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L2] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
pi_l2_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
% elif _memoryLevel == "L3":
#ifdef DEEPLOY_TRACE_FREE
printf("[Deeploy][FREE][L3] %s ptr=%p size=%u\\n", "${name}", ${name},
       (unsigned)(sizeof(${type.referencedType.typeName}) * ${size}));
#endif
cl_ram_free(${name}, sizeof(${type.referencedType.typeName}) * ${size});
% else:
//COMPILER BLOCK - MEMORYLEVEL ${_memoryLevel} NOT FOUND \n
% endif
""")