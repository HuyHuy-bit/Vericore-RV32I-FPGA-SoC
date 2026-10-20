# Design decisions

[Documentation index](README.md) · [Architecture](architecture.md) · [Measured studies](studies.md)

These are the choices implemented in this project. Historical comparisons are
kept in the studies; an unbuilt alternative is a trade-off, not a measured result.

| Decision | Reason | Cost / limit | Implementation or evidence |
|---|---|---|---|
| Five-stage, single-issue, in-order pipeline | Keep dependencies and precise state changes tractable while implementing a complete CPU. | Limited instruction-level parallelism. | [Core](../rtl/core/rv32i_core.sv) |
| Forward from EX/MEM and MEM/WB; stall only real load-use dependencies | Keep dependent ALU instructions moving and avoid false hazards on unused instruction fields. | A dependent load still needs a bubble. | [Forwarding](../rtl/core/forwarding_unit.sv), [hazards](../rtl/core/hazard_detect.sv), [waveforms](portfolio/README.md) |
| Resolve branches in EX | Reuse execution operands and forwarding. | Two younger stages need recovery; ID resolution was not built or measured. | [Backend](../rtl/core/backend.sv) |
| Commit traps and CSR effects in MEM; carry valid bits | Give exceptions one ordered decision point and prevent squashed instructions from changing state. | Redirects are later than EX detection. | [Backend](../rtl/core/backend.sv), [CSR](../rtl/core/csr.sv) |
| Freeze the whole pipeline on memory waits | Keep memory completion, redirects, counters, and retirement consistent. | A data miss also stalls fetch; no decoupled front end. | [Core stall control](../rtl/core/rv32i_core.sv) |
| Blocking, configurable caches with both write policies | Compare geometry and policy using the same core. | No outstanding-miss overlap; write-through has no store buffer. | [Cache study](studies.md#getting-the-caches-into-block-ram) |
| Per-way cache arrays, registered reads, and a unified write port | Express storage in a form that Vivado can infer as block RAM. | Adds pipeline/control requirements around the registered read. | [Measured inference steps](studies.md#getting-the-caches-into-block-ram) |
| BTB + two-bit counters; optional gshare and an eight-entry RAS | Keep a simple default while testing correlated branches and returns. | First taken branches miss the BTB; the RAS is speculative without rollback. | [Prediction studies](studies.md#branch-prediction) |
| Invalidate and redirect for FENCE.I | Discard both cached instructions and younger instructions already fetched. | Instruction memory is read-only, so self-modifying code is not exercised. | [FENCE.I study](studies.md#fencei) |
| Memory-independent core plus a separate compatibility wrapper | Reuse the core for the existing verification harness and the FPGA SoC. | Two integration environments need separate evidence. | [Integration boundaries](architecture.md#integration-boundaries) |
| Wishbone Classic, on-chip BRAM, transmit-only UART, simple GPIO IRQ | Make the FPGA integration small enough to verify end to end. | No DDR, DMA, UART RX, PLIC, or OS. | [SoC contract](soc.md) |
| Bypass the D-cache for MMIO | Peripheral reads/writes must reach the device without cache allocation or deferred dirty eviction. | Only the data-BRAM range is cacheable. | [Cacheability](soc.md#cacheability-and-interrupts) |
| Explicit tohost completion and pinned independent references | Distinguish completion from a stuck PC and make reference results reproducible. | The harness and reference setup need their own negative tests. | [Verification](verification.md#failure-detection) |

## Current predictor changes

The working tree includes two further choices:

- Reset BTB valid bits but not its tag/target arrays. Valid bits qualify hits, so
  clearing every payload entry is unnecessary. Removing bulk reset allows more
  storage implementation options; an area improvement requires a measured comparison.
- Suppress RAS push/pop on flush and trap-redirect cycles. That fetch is being
  discarded and must not update the stack. This prevents a known wrong-path
  update; it does not implement rollback of earlier speculative updates.

The [FPGA snapshot](fpga.md) identifies the exact files used, including these edits.
The old predictor results in [studies.md](studies.md) have not been remeasured for
them and should not be presented as their measured improvement.

## Deliberate remaining work

A fetch queue, store buffer, nonblocking cache, or earlier branch resolution would
change the stall/flush contract. Each needs a separate experiment and regression
before a speedup can be claimed. Random privilege-state testing, formal proof,
and physical-board validation remain separate verification tasks.
