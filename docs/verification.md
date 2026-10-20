# Verification

[Documentation index](README.md) · [Evidence ledger](evidence.md) · [FPGA evidence](fpga.md)

The checks answer different questions: unit tests check local behavior, directed
programs stress interactions, independent references check architectural results,
and post-route simulation checks the implemented FPGA netlist.

## What runs

| Command | What it checks |
|---|---|
| `make check` | Fast units, directed core tests, and SoC integration checks. |
| `make verify` | Complete pinned-container verification profile. |
| `make predictor-test` | Directed suite with gshare, no RAS, and a smaller BTB. |
| `make compliance` | Base RV32I architecture-test signatures against independent golden results. |
| `make lockstep` | Complete retirement streams against pinned Spike: PC, instruction, destination, and written value. |
| `make soak SEEDS=1000` | Random ALU/load/store programs against a Python model, cacheless and cached. |
| `make soak-lockstep SEEDS=200` | Random programs including branches/jumps against Spike at retirement. |
| `make coverage` | Core structural coverage and explicit functional cover points. |
| `make soc-check` | Bus/peripheral units, firmware, UART/LED/interrupt integration, and lint. |

The directed memory matrix includes baseline, slow memory, I-cache, write-through
D-cache, write-back D-cache, and an associative variant. Commands and exact
parameters for recorded measurements are in the [ledger](evidence.md).

## Failure detection

Tests finish with an explicit `tohost` store observed at commit. A repeated PC
is not a completion condition. The harness rejects timeouts, malformed references,
bad completion values, incomplete traces, stale outputs, and simulator failures.

Architecture signatures check final results using independently written tests.
Spike lockstep checks every retirement and reports the first mismatch. Random
programs initialise registers so Spike's boot state cannot create a false divergence.
Both reference sources are pinned in `tools/reference_versions.env`.

Assertions check forwarding, stalls, flushes, traps, caches, and predictor behavior
in simulation. They are not an unbounded formal proof. Coverage is described in
[coverage.md](coverage.md); hitting all declared points does not establish exhaustive
ISA or state-space coverage.

## SoC firmware test

The required UART stream is `rv32i soc ready\nexternal irq\nexternal irq\n`.
The test checks the initial LED, rejects a bouncing button, requires two separate
press/release events, verifies LED changes, and observes progress after `MRET`.
A matching prefix is insufficient. Bus faults, framing errors, duplicate events,
missing output, and deadlines fail the run.

Unit benches cover `core_external`, `csr_external_irq`, `wb_master_adapter`,
`wb_arbiter`, `wb_interconnect`, `wb_memory`, `dcache_counter`, `uart_tx`, `wb_uart`,
`button_debounce`, `wb_gpio_irq`, `reset_controller`, and `soc_smoke`.

## FPGA checks

Vivado synthesizes and routes the board top using the real pin and clock constraints.
XSim post-implementation timing simulation executes the firmware through the
SDF-annotated netlist and checks UART bytes and the boot LED.

This is distinct from the faster RTL SoC test, which also covers two interrupts.
The current post-route bench covers boot only. Details, raw reports, and the latest
run are in [fpga.md](fpga.md). Physical-board operation requires actual programming
and UART/button/LED observations.

## Recorded baseline

<!-- portfolio:summary:start -->
The release gate runs 25 programs across 6 memory configurations and 3 predictor configurations. Pinned architecture signatures and complete Spike traces both pass 38/38; random Spike lockstep passes 200/200; functional coverage is 44/44 (100.0%).
<!-- portfolio:summary:end -->

<!-- portfolio:status:start -->
Historical measurements — validated for RTL d21ecd3fe310bf49c505220c134f8cfd205c90e5; current RTL changes are not yet remeasured.
Historical synthesis — the implementation table was measured for RTL e55cf402670481413c910c2f2a51617ed53342a5; this core configuration matrix has not been rerun for current RTL.
<!-- portfolio:status:end -->

The [evidence ledger](evidence.md) owns the complete result table and revisions.
The [workflow recording](media/portfolio-demo.gif) replays previously validated
results; it is not a fresh run or physical-board footage.

## Remaining gaps

- Random trap, interrupt, and CSR sequences; these are currently directed-test territory.
- Formal verification: no formal proof flow is configured.
- Post-route interrupt/button testing and physical-board validation.
- Performance claims for realistic external memory or an operating system.

<details>
<summary>Machine-checked metadata</summary>

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
