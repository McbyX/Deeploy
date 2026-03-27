# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestResult:
    success: bool
    error_count: int
    total_count: int
    stdout: str
    stderr: str = ""
    runtime_cycles: Optional[int] = None
    crash_pc: Optional[str] = None
    crash_offset: Optional[str] = None
    crash_size: Optional[str] = None
    crash_path: Optional[str] = None


def parse_test_output(stdout: str, stderr: str = "") -> TestResult:

    output = stdout + stderr

    # Look for "Errors: X out of Y" pattern
    error_match = re.search(r'Errors:\s*(\d+)\s*out\s*of\s*(\d+)', output)

    if error_match:
        error_count = int(error_match.group(1))
        total_count = int(error_match.group(2))
        success = (error_count == 0)
    else:
        # Could not parse output - treat as failure
        error_count = -1
        total_count = -1
        success = False

    runtime_cycles = None
    cycle_match = re.search(r'Runtime:\s*(\d+)\s*cycles', output)
    if cycle_match:
        runtime_cycles = int(cycle_match.group(1))

    crash_pc = None
    crash_offset = None
    crash_size = None
    crash_path = None
    crash_match = re.search(r'Invalid access \(pc:\s*(0x[0-9a-fA-F]+),\s*offset:\s*(0x[0-9a-fA-F]+),\s*size:\s*(0x[0-9a-fA-F]+)',
                            output)
    if crash_match:
        crash_pc = crash_match.group(1)
        crash_offset = crash_match.group(2)
        crash_size = crash_match.group(3)
        path_match = re.search(r'\[\s*([^\]]+)\s*\]\s*Invalid access', output)
        if path_match:
            crash_path = path_match.group(1)

    return TestResult(
        success = success,
        error_count = error_count,
        total_count = total_count,
        stdout = stdout,
        stderr = stderr,
        runtime_cycles = runtime_cycles,
        crash_pc = crash_pc,
        crash_offset = crash_offset,
        crash_size = crash_size,
        crash_path = crash_path,
    )
