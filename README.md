# VeriCore — RISC-V CPU and FPGA SoC

A five-stage RV32I CPU written in SystemVerilog, with forwarding, branch prediction,
precise machine-mode traps, configurable caches, and a Wishbone-connected FPGA SoC.

[![RTL Tests](https://github.com/HuyHuy-bit/vericore-verified-rv32i-fpga-soc/actions/workflows/rtl-tests.yml/badge.svg)](https://github.com/HuyHuy-bit/vericore-verified-rv32i-fpga-soc/actions/workflows/rtl-tests.yml)
[![Spike Lockstep](https://github.com/HuyHuy-bit/vericore-verified-rv32i-fpga-soc/actions/workflows/lockstep.yml/badge.svg)](https://github.com/HuyHuy-bit/vericore-verified-rv32i-fpga-soc/actions/workflows/lockstep.yml)

## Evidence

**Routed for the Arty A7-35T at 50 MHz; firmware boot verified in XSim post-route
timing simulation.** The 2026-10-20 run used 9,935 LUTs, 10,910 registers, and
20 BRAM tiles, with **+1.847 ns setup slack**. The SDF-annotated netlist transmitted
`rv32i soc ready` and set the boot LED. [Original reports and remaining DRC warnings](docs/fpga.md).

![Original XSim timing trace displayed in GTKWave](docs/evidence/fpga-2026-10-20/timing-boot.png)

<!-- portfolio:highlights:start -->
Recorded verification baseline: **2026-09-20**. Full results and source revisions are in the [evidence ledger](docs/evidence.md).

| Evidence | Result |
|---|---:|
| RISC-V architecture signatures | 38/38 |
| Architecture tests compared against Spike at retirement | 38/38 |
| Random programs compared against Spike at retirement | 200/200 |
| Directed runs across 6 memory configurations | 150/150 |
| Functional cover points exercised | 44/44 |
<!-- portfolio:highlights:end -->

The [current SoC regression](docs/evidence/fpga-2026-10-20/soc-check.log) also passes: UART boot, rejection of
button bounce, two external interrupts, LED updates, and execution after `MRET`.
The [FPGA report](docs/fpga.md) records the separate Vivado implementation and
post-route timing-simulation run, including its exact source snapshot.

<!-- portfolio:soc:start -->
Physical-board evidence: not published
<!-- portfolio:soc:end -->

![Five-stage datapath](docs/images/datapath.svg)

## Engineering decisions

- **Forwarding and operand-aware stalls:** resolve register dependencies while
  avoiding stalls on instruction fields that are not read operands.
- **One trap/CSR commit point:** discard younger instructions before they can
  change architectural state.
- **FPGA-oriented cache storage:** per-way arrays and a unified write port enable
  BRAM inference. Both write-through and write-back policies are implemented.
- **Measured prediction trade-offs:** a 64-entry BTB, two-bit counters, an eight-entry
  return stack, and optional gshare; the studies compare enabled and disabled builds.

The [decision record](docs/decisions.md) explains the reasons, costs, and remaining
limits. The [studies](docs/studies.md) retain the measured before/after comparisons.

## Run it

Docker is the host requirement for the pinned verification environment.

```bash
git clone https://github.com/HuyHuy-bit/vericore-verified-rv32i-fpga-soc.git
cd vericore-verified-rv32i-fpga-soc
make verify
```

With the native toolchain installed, `make soc-check` runs the firmware demo in
simulation. `make soc-bitstream` builds the Arty A7-35T image with Vivado 2025.2;
see the [Board-ready SoC](docs/soc.md) guide for prerequisites and programming.

## Explore

| Read | What it answers |
|---|---|
| [Architecture](docs/architecture.md) | How do the pipeline, caches, and traps work? |
| [Design decisions](docs/decisions.md) | Why were these approaches chosen? |
| [Verification](docs/verification.md) | What is tested, and how are failures detected? |
| [FPGA evidence](docs/fpga.md) | What did Vivado and post-route simulation demonstrate? |
| [SoC guide](docs/soc.md) | How do I build, simulate, and use the board peripherals? |
| [Original EDA screenshots](docs/portfolio/README.md) | What do the actual signals and implementation look like? |
| [Evidence ledger](docs/evidence.md) | Which revision and reports support each number? |

<details>
<summary>Recorded verification workflow</summary>

This is a verification workflow recording, not FPGA board footage. Its source
revision is recorded in [the media manifest](docs/media/portfolio-demo.json).

![Portfolio verification demo](docs/media/portfolio-demo.gif)

</details>

<details>
<summary>Baseline scope and machine-checked metadata</summary>

The table above is the recorded full-suite baseline. Fresh working-tree runs are
listed separately in the FPGA report; they do not replace that baseline.

<!-- portfolio:status:start -->
Historical measurements — validated for RTL d21ecd3fe310bf49c505220c134f8cfd205c90e5; current RTL changes are not yet remeasured.
Historical synthesis — the implementation table was measured for RTL e55cf402670481413c910c2f2a51617ed53342a5; this core configuration matrix has not been rerun for current RTL.
<!-- portfolio:status:end -->

<!-- portfolio:facts:start -->
<!-- evidence-facts:begin -->
EVIDENCE_FACT ISA=RV32I_Zicsr_Zifencei
EVIDENCE_FACT DIRECTED_TESTS=25
EVIDENCE_FACT ASSERTIONS_TOTAL=66
EVIDENCE_FACT ASSERTIONS_CONCURRENT=63
EVIDENCE_FACT ASSERTIONS_IMMEDIATE=3
EVIDENCE_FACT SOURCE_COVER_POINTS=44
EVIDENCE_FACT TRACKED_COVERAGE_HIT=44
EVIDENCE_FACT TRACKED_COVERAGE_TOTAL=44
EVIDENCE_FACT TRACKED_COVERAGE_STATUS=historical
EVIDENCE_FACT EVIDENCE_STATUS=historical
EVIDENCE_FACT SYNTHESIS_STATUS=historical
EVIDENCE_FACT CI_CONFIGS=6
EVIDENCE_FACT CI_MATRIX=baseline,slow-mem,icache-only,wt,wb,assoc
EVIDENCE_FACT ARCH_TEST_SHA=6f7f47bdc61c0c51c0cbf75789678a1235eeefc2
EVIDENCE_FACT ARCH_TEST_EXPECTED=38
EVIDENCE_FACT SPIKE_SHA=55b4658dbf574ba0b714083ec436ce2cb5be1998
EVIDENCE_FACT SPIKE_RANDOM_SEEDS=200
<!-- evidence-facts:end -->
<!-- portfolio:facts:end -->

</details>

[Documentation index](docs/README.md) · [MIT license](LICENSE)
