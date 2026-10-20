"""Reject incomplete or mismatched external-tool evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from synthesis.soc.run_snapshot import collect


class SnapshotCollectionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.stage = root / "stage"
        self.output = root / "output"
        self.stage.mkdir()
        self.output.mkdir()
        self.source = self.stage / "source.sv"
        self.source.write_text("module fixture; endmodule\n")
        self.manifest = {
            "status": "running", "stage": str(self.stage),
            "source_sha256": {"source.sv": hashlib.sha256(self.source.read_bytes()).hexdigest()},
        }
        (self.output / "manifest.json").write_text(json.dumps(self.manifest))

    def test_changed_staged_source_is_rejected(self):
        self.source.write_text("module changed; endmodule\n")
        with self.assertRaisesRegex(ValueError, "Staged source changed"):
            collect(self.output)

    def test_running_tool_is_not_accepted_as_complete(self):
        (self.stage / "vivado.log").write_text("route_design started\n")
        with self.assertRaisesRegex(ValueError, "has not exited"):
            collect(self.output)
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["status"], "running")

    def test_vivado_exit_without_successful_xsim_is_rejected(self):
        (self.stage / "vivado.log").write_text("Exiting Vivado\n")
        transcript = self.stage / "timing-out/project/post_route_sim.sim/sim_1/impl/timing/xsim/simulate.log"
        transcript.parent.mkdir(parents=True)
        transcript.write_text("UART mismatch at byte 2\n")
        with self.assertRaisesRegex(ValueError, "no successful boot check"):
            collect(self.output)


if __name__ == "__main__":
    unittest.main()
