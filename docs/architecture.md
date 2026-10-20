# Architecture

[Documentation index](README.md) · [Design decisions](decisions.md) · [SoC guide](soc.md)

The core implements `RV32I_Zicsr_Zifencei`: a five-stage, single-issue, in-order
pipeline with machine-mode CSRs and traps. M/A/C extensions and S/U privilege
modes are outside the implementation.

![Pipeline datapath](images/datapath.svg)

## Pipeline

| Stage | Work |
|---|---|
| IF | Select the PC, look up the branch predictor, fetch through the optional I-cache. |
| ID | Decode, read registers with same-cycle write bypass, detect load-use hazards. |
| EX | Forward operands, execute the ALU, resolve branches, detect exceptions. |
| MEM | Complete the LSU/D-cache access; commit traps, CSR writes, `MRET`, and `FENCE.I`. |
| WB | Select the result and write the register file. |

Each pipeline register carries `valid`. Flushed slots cannot write architectural
state or appear as retired instructions. EX/MEM and MEM/WB forwarding resolve
short register dependencies; a dependent load inserts one bubble when memory is ready.

A memory wait freezes the whole pipeline. Redirect priority is:

```text
freeze > trap/MRET > mispredict > load-use stall > prediction > PC+4
```

Branches resolve in EX. Misprediction recovery invalidates IF/ID and ID/EX.
Exceptions detected in EX reach the MEM commit point, where `mepc`, `mcause`, and
`mtval` are recorded before redirecting to the handler. `MRET` restores interrupt state.

See the [native GTKWave captures](portfolio/README.md) for load-use, branch,
and illegal-instruction behavior.

## Prediction

The default predictor has a 64-entry BTB, two-bit direction counters, and an
8-entry return-address stack. Optional gshare indexes direction counters with
`PC XOR global_history`; the prediction history travels with the instruction
so updates use the original index.

The RAS changes only on an accepted fetch. A fetch in an EX-flush or trap-redirect
cycle cannot push or pop it. Earlier speculative updates are not rolled back,
so wrong-path calls can still affect prediction quality.

## Memory

![Memory hierarchy](images/mem_hierarchy.svg)

I-cache and D-cache capacity, block size, and associativity are build parameters.
The D-cache supports write-through and write-back. Both caches are blocking and
use FIFO victim selection. The LSU implements byte, halfword, and word accesses.

`FENCE.I` invalidates the I-cache and redirects to `pc+4` at the commit point,
discarding already-fetched younger instructions. Both current integrations
reject writes to instruction memory, so self-modifying code is not demonstrated.

The legacy memory model discounts sequential refill words. The SoC performs
separate Wishbone word transfers; benchmark latency results from the legacy
wrapper must not be presented as board throughput.

## Integration boundaries

| Module | Responsibility |
|---|---|
| `rv32i_core` | Pipeline, caches, CSRs, predictor; external instruction/data clients. |
| `cpu` | Core plus internal memory models for core verification and synthesis studies. |
| `rv32i_soc` | Core plus Wishbone adapters, arbitration, BRAM, UART, GPIO, and interrupt input. |
| `arty_a7_35t_top` | Arty clock generation, reset, pins, and SoC instance. |

The SoC caches only the data-BRAM address range. MMIO bypasses the D-cache.
Bus errors become a sticky integration fault, not architectural access-fault traps.
The exact memory map is owned by the [SoC guide](soc.md).

## Limits

There is no fetch queue, store buffer, nonblocking cache, or out-of-order execution.
The SoC has no external-memory controller or operating system. The reasons and
costs of these choices are in [decisions.md](decisions.md); performance measurements
are in [studies.md](studies.md) and the [evidence ledger](evidence.md).

<details>
<summary>Measurement status and machine-checked metadata</summary>

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
