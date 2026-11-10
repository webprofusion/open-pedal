"""Regenerate the KiCad project from design.py and layout.json, check it, export previews.

Run with the Python that ships with KiCad 10 (it provides the pcbnew module):

    "<KiCad>/bin/python" hardware/kicad/scripts/build.py

Steps: schematic -> ERC -> netlist compared with design.py -> board -> DRC -> exports.
"""
import collections
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJECT, PROJECT_DIR, kicad_root   # noqa: E402
import check_netlist                                  # noqa: E402
import gen_pcb                                        # noqa: E402
import gen_sch                                        # noqa: E402

CLI = os.path.join(kicad_root(), "bin", "kicad-cli" + (".exe" if os.name == "nt" else ""))
SCH = os.path.join(PROJECT_DIR, PROJECT + ".kicad_sch")
PCB = os.path.join(PROJECT_DIR, PROJECT + ".kicad_pcb")
EXPORTS = os.path.join(PROJECT_DIR, "exports")
# Expected on a board that is placed but not routed.
DRC_EXPECTED = {"unconnected_items", "silk_overlap", "silk_over_copper", "silk_edge_clearance"}


def cli(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode not in (0, 5):          # 5 = violations found, reported below
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed:\n{r.stdout}{r.stderr}")


def violations(report):
    text = open(report, encoding="utf8").read()
    return collections.Counter(re.findall(r"^\[([a-z_]+)\]", text, re.M))


def main():
    os.makedirs(EXPORTS, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="open-pedal-")
    ok = True

    gen_sch.main()
    erc = os.path.join(tmp, "erc.rpt")
    cli("sch", "erc", "--severity-all", "--format", "report", "-o", erc, SCH)
    found = violations(erc)
    print("ERC:", dict(found) or "clean")
    ok &= not found

    net = os.path.join(tmp, "netlist.net")
    cli("sch", "export", "netlist", "-o", net, SCH)
    ok &= check_netlist.main(net) == 0

    gen_pcb.main()
    drc = os.path.join(tmp, "drc.rpt")
    cli("pcb", "drc", "--severity-all", "--format", "report", "-o", drc, PCB)
    found = violations(drc)
    print("DRC:", dict(found))
    unexpected = set(found) - DRC_EXPECTED
    if unexpected:
        print("DRC: unexpected violation types:", sorted(unexpected))
        ok = False

    cli("sch", "export", "pdf", "-o", os.path.join(EXPORTS, PROJECT + "-schematic.pdf"), SCH)
    cli("pcb", "export", "glb", "--user-origin", "50x50mm", "--subst-models", "--include-pads",
        "--include-silkscreen", "--include-soldermask", "--force",
        "-o", os.path.join(EXPORTS, PROJECT + "-board.glb"), PCB)
    cli("pcb", "render", "--side", "top", "--rotate", "-35,0,0", "--zoom", "1.2", "-w", "1800", "-h", "1000",
        "--quality", "high", "-o", os.path.join(EXPORTS, PROJECT + "-board.png"), PCB)
    print("exports written to", EXPORTS)
    print("OK" if ok else "FAILED: see messages above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
