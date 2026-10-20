#!/usr/bin/env python3
"""Run Vivado on a hashed working-tree snapshot, separate from release evidence."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from synthesis.run_synth import discover_tool, git_output, sha256
from synthesis.soc.run_board import (
    create_board_stage, read_timing_sim_metadata, validate_firmware_image,
    validate_timing_constraints, TIMING_SIM_MARKER, TIMING_SIM_PASS,
)

ROOT = Path(__file__).resolve().parents[2]


def run(output, timeout):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    imem = ROOT / "build/soc/firmware-imem.hex"
    dmem = ROOT / "build/soc/firmware-dmem.hex"
    for path in (imem, dmem):
        validate_firmware_image(path)
    tool, parent = discover_tool(dict(os.environ))
    with create_board_stage(ROOT, parent, imem, dmem, timing_sim=True) as temporary:
        # Retain the project even after a failed run for EDA inspection.
        stage = Path(tempfile.mkdtemp(prefix="rv32i-evidence-", dir=parent))
        shutil.copytree(temporary, stage, dirs_exist_ok=True)
    sources = {str(p.relative_to(stage)): sha256(p)
               for p in sorted(stage.rglob("*")) if p.is_file()}
    manifest = {
        "schema": 1, "status": "running", "evidence_kind": "working-tree FPGA implementation",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": git_output(ROOT, "rev-parse", "HEAD"),
        "source_sha256": sources, "stage": str(stage),
        "vivado": {"version": tool.version, "build": tool.build},
        "physical_board_tested": False,
    }
    (output / "source-changes.patch").write_text(
        git_output(ROOT, "diff", "--binary", "HEAD", "--", "rtl", "sim/arty_post_route_tb.sv",
                   "synthesis/soc/post_route_sim.tcl") + "\n")
    metadata = output / "manifest.json"
    metadata.write_text(json.dumps(manifest, indent=2) + "\n")
    arguments = ("-mode", "batch", "-source", "synthesis/soc/post_route_sim.tcl",
                 "-tclargs", "timing-out", "firmware-imem.hex", "firmware-dmem.hex")
    command = tool.command(arguments)
    manifest["command"] = command
    metadata.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Vivado stage: {stage}", flush=True)
    print(f"Console: {output / 'vivado.log'}", flush=True)
    try:
        with (output / "vivado.log").open("w") as log:
            subprocess.run(command, cwd=stage, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=timeout)
        collect(output)
    except Exception as exc:
        manifest.update(status="failed", error=str(exc))
        metadata.write_text(json.dumps(manifest, indent=2) + "\n")
        raise


def collect(output):
    output = output.resolve()
    metadata = output / "manifest.json"
    manifest = json.loads(metadata.read_text())
    stage = Path(manifest["stage"])
    for relative, digest in manifest["source_sha256"].items():
        if sha256(stage / relative) != digest:
            raise ValueError(f"Staged source changed: {relative}")
    console = (stage / "vivado.log").read_text(errors="replace")
    if "Exiting Vivado" not in console:
        raise ValueError("Vivado has not exited")
    shutil.copy2(stage / "vivado.log", output / "vivado.log")
    simulate = stage / "timing-out/project/post_route_sim.sim/sim_1/impl/timing/xsim/simulate.log"
    if not simulate.is_file() or TIMING_SIM_PASS not in simulate.read_text(errors="replace"):
        raise ValueError("XSim transcript has no successful boot check")
    shutil.copy2(simulate, output / "simulate.log")
    routed = stage / "timing-out"
    if TIMING_SIM_PASS not in console or TIMING_SIM_MARKER not in console:
        raise ValueError("Vivado timing simulation did not report complete success")
    info = read_timing_sim_metadata(routed / "post_route_sim_meta.txt")
    validate_timing_constraints((routed / "timing_summary.rpt").read_text())
    netlist = routed / "arty_a7_35t_top_timesim.v"
    if "$sdf_annotate" not in netlist.read_text():
        raise ValueError("Timing netlist lacks SDF annotation")
    expected = ("timing_summary.rpt", "utilization.rpt", "drc.rpt", "clocks.rpt",
                "post_route_sim_meta.txt", "timing-boot.vcd",
                "rv32i-soc-arty-a7-35t.bit", "routed.dcp",
                "arty_a7_35t_top_timesim.v", "arty_a7_35t_top.sdf")
    for name in expected:
        source = routed / name
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing EDA artifact: {name}")
        started = datetime.fromisoformat(manifest["started_at"]).timestamp()
        if source.stat().st_mtime < started - 1:
            raise ValueError(f"Stale EDA artifact: {name}")
        shutil.copy2(source, output / name)
    manifest.update(status="complete", implementation=info,
                    uart="rv32i soc ready\n", led=1)
    manifest["collected_at"] = datetime.now(timezone.utc).isoformat()
    manifest["finished_at"] = datetime.fromtimestamp((stage / "vivado.log").stat().st_mtime, timezone.utc).isoformat()
    manifest["collector_sha256"] = sha256(Path(__file__))
    manifest["artifacts_sha256"] = {
        p.name: sha256(p) for p in sorted(output.iterdir())
        if p.is_file() and p.name != "manifest.json"}
    metadata.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS: routed FPGA timing simulation; evidence in {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=14400)
    parser.add_argument("--collect-existing", action="store_true",
                        help="Validate and collect an already completed staged run")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.collect_existing:
        collect(args.output)
    else:
        run(args.output, args.timeout)
