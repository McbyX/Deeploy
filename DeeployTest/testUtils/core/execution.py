# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
#
# SPDX-License-Identifier: Apache-2.0

import os
import selectors
import shutil
import subprocess
import sys
import time
from pathlib import Path

from Deeploy.Logging import DEFAULT_LOGGER as log

from .config import DeeployTestConfig
from .output_parser import TestResult, parse_test_output

def _resolve_pc_symbol(config: DeeployTestConfig, pc: str) -> str:
    binary_path = Path(config.build_dir) / "bin" / config.test_name
    if not binary_path.exists():
        return "binary not found"

    candidates = []
    if config.toolchain_install_dir:
        candidates.append(Path(config.toolchain_install_dir) / "bin" / "llvm-addr2line")
        candidates.append(Path(config.toolchain_install_dir) / "bin" / "addr2line")
    candidates.extend(["llvm-addr2line", "addr2line"])

    for tool in candidates:
        tool_path = str(tool)
        if not shutil.which(tool_path):
            continue
        try:
            result = subprocess.run([tool_path, "-f", "-C", "-e", str(binary_path), pc],
                                    capture_output = True,
                                    text = True,
                                    check = False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            continue

    return "addr2line unavailable"

def generate_network(config: DeeployTestConfig, skip: bool = False) -> None:
    """
    Generate network code from ONNX model.
        
    Raises:
        RuntimeError: If network generation fails
    """
    if skip:
        log.info(f"Skipping network generation for {config.test_name}")
        return

    script_dir = Path(__file__).parent.parent.parent

    if config.tiling:
        generation_script = script_dir / "testMVP.py"
    else:
        generation_script = script_dir / "generateNetwork.py"

    cmd = [
        "python",
        str(generation_script),
        "-d",
        config.gen_dir,
        "-t",
        config.test_dir,
        "-p",
        config.platform,
    ]

    # Add verbosity flags
    if config.verbose > 0:
        cmd.append("-" + "v" * config.verbose)

    # Add debug flag
    if config.debug:
        cmd.append("--debug")

    # Add additional generation arguments
    cmd.extend(config.gen_args)

    log.debug(f"[Execution] Generation command: {' '.join(cmd)}")

    result = subprocess.run(cmd, check = False)

    if result.returncode != 0:
        log.error(f"Network generation failed with return code {result.returncode}")
        raise RuntimeError(f"Network generation failed for {config.test_name}")


def configure_cmake(config: DeeployTestConfig) -> None:

    assert config.toolchain_install_dir is not None, \
        "LLVM_INSTALL_DIR environment variable not set"

    cmake_cmd = os.environ.get("CMAKE", "cmake")
    if cmake_cmd == "cmake" and shutil.which("cmake") is None:
        raise RuntimeError("CMake not found. Please install CMake or set CMAKE environment variable")

    # Build CMake command
    cmd = [
        cmake_cmd,
        f"-DTOOLCHAIN={config.toolchain}",
        f"-DTOOLCHAIN_INSTALL_DIR={config.toolchain_install_dir}",
        f"-DGENERATED_SOURCE={config.gen_dir}",
        f"-Dplatform={config.platform}",
        f"-DTESTNAME={config.test_name}",
        f"-B{config.build_dir}",
    ]

    for arg in config.cmake_args:
        if not arg.startswith("-D"):
            arg = "-D" + arg
        cmd.append(arg)

    if config.simulator == 'banshee':
        cmd.append("-Dbanshee_simulation=ON")
    else:
        cmd.append("-Dbanshee_simulation=OFF")

    if config.simulator == 'gvsoc':
        cmd.append("-Dgvsoc_simulation=ON")
    else:
        cmd.append("-Dgvsoc_simulation=OFF")

    # Last argument is the source directory
    script_dir = Path(__file__).parent.parent.parent
    cmd.append(str(script_dir.parent))

    env = os.environ.copy()
    if config.verbose >= 3:
        env["VERBOSE"] = "1"

    log.debug(f"[Execution] CMake command: {' '.join(cmd)}")

    result = subprocess.run(cmd, check = False, env = env)

    if result.returncode != 0:
        log.error(f"CMake configuration failed with return code {result.returncode}")
        raise RuntimeError(f"CMake configuration failed for {config.test_name}")


def build_binary(config: DeeployTestConfig) -> None:

    cmake_cmd = os.environ.get("CMAKE", "cmake")

    cmd = [
        cmake_cmd,
        "--build",
        config.build_dir,
        "--target",
        config.test_name,
    ]

    env = os.environ.copy()
    if config.verbose >= 3:
        env["VERBOSE"] = "1"

    log.debug(f"[Execution] Build command: {' '.join(cmd)}")

    result = subprocess.run(cmd, check = False, env = env)

    if result.returncode != 0:
        log.error(f"Build failed with return code {result.returncode}")
        raise RuntimeError(f"Build failed for {config.test_name}")


def run_simulation(config: DeeployTestConfig, skip: bool = False) -> TestResult:
    """
    Run simulation and parse output.
        
    Raises:
        RuntimeError: If simulation cannot be executed
    """
    if skip:
        log.info(f"Skipping simulation for {config.test_name}")
        return TestResult(success = True, error_count = 0, total_count = 0, stdout = "Skipped")

    if config.simulator == 'none':
        raise RuntimeError("No simulator specified!")

    if config.simulator == 'host':
        # Run binary directly
        binary_path = Path(config.build_dir) / "bin" / config.test_name
        cmd = [str(binary_path)]
    else:
        # Run via CMake target
        cmake_cmd = os.environ.get("CMAKE", "cmake")
        cmd = [
            cmake_cmd,
            "--build",
            config.build_dir,
            "--target",
            f"{config.simulator}_{config.test_name}",
        ]

    env = os.environ.copy()
    if config.verbose >= 3:
        env["VERBOSE"] = "1"

    if config.simulator == 'banshee':
        if config.verbose == 1:
            env["BANSHEE_LOG"] = "warn"
        elif config.verbose == 2:
            env["BANSHEE_LOG"] = "info"
        elif config.verbose >= 3:
            env["BANSHEE_LOG"] = "debug"

    log.debug(f"[Execution] Simulation command: {' '.join(cmd)}")

    timeout_s = int(os.environ.get("DEEPLOY_SIM_TIMEOUT_S", "0"))
    if timeout_s > 0:
        log.info(f"[Execution] Simulation timeout enabled: {timeout_s}s")

    stdout_chunks = []

    with subprocess.Popen(cmd,
                          stdout = subprocess.PIPE,
                          stderr = subprocess.STDOUT,
                          text = True,
                          env = env,
                          bufsize = 1) as proc:
        assert proc.stdout is not None

        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        start_time = time.monotonic()

        try:
            while True:
                if timeout_s > 0 and (time.monotonic() - start_time) > timeout_s:
                    proc.kill()
                    raise RuntimeError(f"Simulation timed out after {timeout_s}s for {config.test_name}")

                events = sel.select(timeout = 0.5)
                if events:
                    chunk = proc.stdout.read(1)
                    if chunk:
                        stdout_chunks.append(chunk)
                        print(chunk, end = '')

                if proc.poll() is not None:
                    remaining = proc.stdout.read()
                    if remaining:
                        stdout_chunks.append(remaining)
                        print(remaining, end = '')
                    break
        finally:
            sel.close()

    stdout_text = ''.join(stdout_chunks)
    stderr_text = ''

    # Parse output for error count and cycles
    test_result = parse_test_output(stdout_text, stderr_text)

    if not test_result.success and test_result.error_count == -1:
        log.warning(f"Could not parse error count from output")
        if test_result.crash_pc is not None:
            log.warning(
                f"Detected invalid memory access at pc={test_result.crash_pc}, offset={test_result.crash_offset}, "
                f"size={test_result.crash_size}, source={test_result.crash_path}")
            symbol_info = _resolve_pc_symbol(config, test_result.crash_pc)
            log.warning(f"addr2line({test_result.crash_pc}) -> {symbol_info}")

    return test_result


def run_complete_test(config: DeeployTestConfig, skipgen: bool = False, skipsim: bool = False) -> TestResult:
    """
    Run a complete test: generate, configure, build, and simulate.
    """
    log.info(f"################## Testing {config.test_name} on {config.platform} Platform ##################")

    # Step 1: Generate network
    generate_network(config, skip = skipgen)

    # Step 2: Configure CMake
    configure_cmake(config)

    # Step 3: Build binary
    build_binary(config)

    # Step 4: Run simulation
    result = run_simulation(config, skip = skipsim)

    return result
