#!/usr/bin/env python3
"""Capture native GTKWave windows and package original project visuals."""

import ctypes as c
from ctypes.util import find_library
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/portfolio"
WORK = ROOT / "build/portfolio-capture/native"
TESTS = [
    ("t07_load_use", "load-use", "Load-use hazard", 4, 26, 10),
    ("t04_branch", "branch-recovery", "Branch recovery", 4, 26, 10),
    ("t09_trap_illegal", "trap-recovery", "Illegal-instruction trap", 10, 32, 16),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def screenshot(window_id, destination):
    """Save the X11 application window directly, without changing its pixels."""
    gtk = c.CDLL(find_library("gtk-x11-2.0"))
    gdk = c.CDLL(find_library("gdk-x11-2.0"))
    pix = c.CDLL(find_library("gdk_pixbuf-2.0"))
    obj = c.CDLL(find_library("gobject-2.0"))
    gtk.gtk_init(None, None)
    gdk.gdk_window_foreign_new.argtypes = [c.c_ulong]
    gdk.gdk_window_foreign_new.restype = c.c_void_p
    window = gdk.gdk_window_foreign_new(window_id)
    gdk.gdk_drawable_get_size.argtypes = [c.c_void_p, c.POINTER(c.c_int), c.POINTER(c.c_int)]
    width, height = c.c_int(), c.c_int()
    gdk.gdk_drawable_get_size(window, c.byref(width), c.byref(height))
    gdk.gdk_drawable_get_colormap.argtypes = [c.c_void_p]
    gdk.gdk_drawable_get_colormap.restype = c.c_void_p
    colormap = gdk.gdk_drawable_get_colormap(window)
    gdk.gdk_pixbuf_get_from_drawable.argtypes = [c.c_void_p]*3 + [c.c_int]*6
    gdk.gdk_pixbuf_get_from_drawable.restype = c.c_void_p
    buf = gdk.gdk_pixbuf_get_from_drawable(
        None, window, colormap, 0, 0, 0, 0, width.value, height.value)
    if not buf:
        raise RuntimeError("Cannot read GTKWave window pixels")
    pix.gdk_pixbuf_save.argtypes = [c.c_void_p, c.c_char_p, c.c_char_p, c.c_void_p, c.c_void_p]
    if not pix.gdk_pixbuf_save(buf, os.fsencode(destination), b"png", None, None):
        raise RuntimeError("Cannot save GTKWave screenshot")
    obj.g_object_unref.argtypes = [c.c_void_p]
    obj.g_object_unref(buf)
    obj.g_object_unref(window)


def capture(test, name, start, end, marker):
    evidence = OUT / "evidence"
    script = evidence / f"{test}-view.tcl"
    script.write_text(f"gtkwave::setZoomRangeTimes {start} {end}\n"
                      f"gtkwave::setMarker {marker}\n")
    command = ["gtkwave", str(evidence / f"{test}.vcd"),
               str(evidence / f"{test}.gtkw"), "-r", str(evidence / "gtkwaverc"),
               "-S", str(script)]
    with (WORK / f"{test}.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, "GSETTINGS_BACKEND": "memory"})
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError(f"GTKWave exited; see {log.name}")
                tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
                match = re.search(r'(0x[0-9a-f]+) "GTKWave - [^"]*'
                                  + re.escape(test) + r'\.vcd"', tree)
                if match:
                    time.sleep(1)
                    screenshot(int(match[1], 16), OUT / f"{name}.png")
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError(f"GTKWave window not found for {test}")
        finally:
            process.terminate()
            process.wait(timeout=10)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    evidence = OUT / "evidence"
    manifest = json.loads((evidence / "manifest.json").read_text())
    for test, record in manifest["tests"].items():
        if sha(evidence / f"{test}.vcd") != record["vcd_sha256"]:
            raise ValueError(f"VCD differs from recorded simulation: {test}")
    (evidence / "gtkwaverc").write_text(
        "initial_window_x 1600\ninitial_window_y 470\nhide_sst on\n"
        "fontname_signals Monospace 11\nfontname_waves Monospace 11\n"
        "hier_max_level 2\nuse_pango_fonts on\n")
    for test, name, _, start, end, marker in TESTS:
        capture(test, name, start, end, marker)
    reference = OUT / "reference"
    reference.mkdir(exist_ok=True)
    for name in ("datapath.svg", "soc-vivado-device.png", "soc-vivado-device.json"):
        shutil.copyfile(ROOT / "docs/images" / name, reference / name)
    fpga = ROOT / "docs/evidence/fpga-2026-10-20"
    for name in ("timing-boot.png", "simulate.log", "manifest.json"):
        shutil.copyfile(fpga / name, reference / ("fpga-" + name))
    original = json.loads((reference / "soc-vivado-device.json").read_text())
    if sha(reference / "soc-vivado-device.png") != original["capture"]["image_sha256"]:
        raise ValueError("Original Vivado screenshot hash mismatch")
    figures = [
        ("Original project datapath", "reference/datapath.svg",
         "Existing architecture diagram from the repository."),
        ("FPGA firmware boot — XSim post-route timing simulation", "reference/fpga-timing-boot.png",
         "2026-10-20: SDF-annotated FPGA netlist, 50 MHz SoC constraint, +1.847 ns setup slack. UART boot and LED checks passed; DRC warnings remain in the FPGA report."),
        *[(title, f"{name}.png", f"GTKWave screenshot of {test}.vcd; directed test passed.")
          for test, name, title, *_ in TESTS],
        ("Original Vivado Device view", "reference/soc-vivado-device.png",
         "Historical routed SoC: 50 MHz constraint, +2.009 ns WNS. RTL d21ecd3fe310. No physical-board claim."),
    ]
    intro = ("Native GTKWave captures and the original Vivado screenshot. "
             "Core waveforms use Verilator testbench time; the FPGA boot trace uses XSim timing simulation.")
    intro += (" The FPGA boot transcript and source manifest are retained in reference/fpga-simulate.log "
              "and reference/fpga-manifest.json.")
    body = ['<!doctype html><html lang="en"><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>VeriCore project visuals</title>',
            '<style>body{font:16px/1.5 sans-serif;max-width:1500px;margin:24px auto;padding:0 16px}'
            'h1{font-size:26px}h2{font-size:20px}img{width:100%;height:auto}'
            'figure{margin:32px 0}figcaption{margin:8px 0;color:#444}'
            '@page{size:A4 landscape;margin:12mm}'
            '@media print{header{display:none}figure{break-after:page;margin:0}'
            'figure:last-child{break-after:auto}img{max-height:155mm;object-fit:contain}'
            'h2{margin:0 0 8px}figcaption{font-size:12px}}</style>',
            f'<header><h1>VeriCore project visuals</h1><p>{intro}</p>'
            '<p><a href="portfolio.pdf">PDF</a> · <a href="README.md">Files and sources</a></p></header>']
    readme = ["# VeriCore project visuals", "", intro, "",
              "[PDF](portfolio.pdf) · [HTML gallery](index.html)", ""]
    for title, path, caption in figures:
        body.append(f'<figure><h2>{title}</h2><a href="{path}">'
                    f'<img src="{path}" alt="{title}"></a><figcaption>{caption}</figcaption></figure>')
        readme += [f"## {title}", "", f"![{title}]({path})", "", caption, ""]
    body.append("</html>")
    (OUT / "index.html").write_text("\n".join(body))
    readme += ["## Reproduce", "",
               "The screenshots are unedited captures of GTKWave's application window.",
               "No waveform has been redrawn. The original datapath is a conceptual diagram.",
               "Raw VCDs, simulator logs, signal selections and source hashes are in `evidence/`.",
               "The Vivado image and its metadata are copied byte-for-byte from `docs/images/`.",
               "", "Open a trace with the same view:", "", "```bash",
               "cd docs/portfolio/evidence",
               "gtkwave t07_load_use.vcd t07_load_use.gtkw -r gtkwaverc -S t07_load_use-view.tcl",
               "```", "", "Recapture all three GTKWave windows on Linux with an X11 display:",
               "", "```bash", "python3 tools/capture_portfolio.py", "```", "",
               "The script uses GTKWave, xwininfo and the GTK2 libraries; Chromium exports the PDF.",
               "These three directed runs are not a new full-suite or synthesis validation."]
    (OUT / "README.md").write_text("\n".join(readme) + "\n")
    browser = shutil.which("chromium") or shutil.which("google-chrome")
    if not browser:
        browser = next(iter(sorted(Path.home().glob(
            ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"))), None)
    if not browser:
        raise RuntimeError("Chromium is required for the PDF; screenshots and gallery are ready.")
    with (WORK / "pdf.log").open("w") as log:
        subprocess.run([str(browser), "--headless", "--no-sandbox", "--disable-gpu",
                        "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
                        "--disable-background-networking", "--disable-sync",
                        "--no-pdf-header-footer", "--timeout=10000",
                        f"--print-to-pdf={OUT / 'portfolio.pdf'}",
                        (OUT / "index.html").as_uri()],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    (OUT / "artifacts.json").write_text(json.dumps({
        "method": "Native GTKWave application-window screenshots; unchanged original Vivado screenshot",
        "gtkwave": subprocess.check_output(["gtkwave", "--version"], text=True).strip(),
        "renderer_sha256": sha(Path(__file__)),
        "files": {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*"))
                  if p.is_file() and p.name != "artifacts.json"},
    }, indent=2) + "\n")
    archive = WORK.parent / "vericore-portfolio.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                z.write(path, Path("vericore-portfolio") / path.relative_to(OUT))
    print(f"Native screenshots, gallery and PDF: {OUT}")
    print(f"Bundle: {archive}")


if __name__ == "__main__":
    main()
