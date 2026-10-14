"""Optional isolated route for the retained sharp-family vector figure.

Adapted from paper/figures/draw_frontier_width.py, preserving its PGF geometry.
Requires an existing Matplotlib and pdflatex installation. No experiment runs.
The optional TeX font root selects installed fonts; no binaries are bundled.
"""
from pathlib import Path
import argparse
import csv
import os
import subprocess
import tempfile

ARTIFACT = Path(__file__).resolve().parents[1]


def read_data(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        data = [(int(r["round"]), int(r["width"])) for r in csv.DictReader(stream)]
    if data != [(k, k + 1) for k in range(1, 13)]:
        raise ValueError("Expected all twelve retained sharp-family depths")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ARTIFACT / "results/figure-sources/widths.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tex-font-root", type=Path)
    parser.add_argument("--tex-font-map-dir", type=Path)
    parser.add_argument("--tex-bin-dir", type=Path)
    args = parser.parse_args()
    data = read_data(args.input)
    HERE = args.output_dir.resolve()
    paper = (ARTIFACT.parent / "paper").resolve()
    retained = (ARTIFACT / "results").resolve()
    if HERE == args.input.resolve().parent or HERE == paper or paper in HERE.parents or HERE == retained or retained in HERE.parents:
        raise ValueError("Output must be separate from retained inputs and paper")
    CACHE = HERE / ".render-cache"
    CACHE.mkdir(parents=True, exist_ok=True)
    for name in ("MPLCONFIGDIR", "TMP", "TEMP"):
        os.environ[name] = str(CACHE)
    tempfile.tempdir = str(CACHE)
    if args.tex_font_root is not None:
        if not args.tex_font_root.is_dir():
            raise FileNotFoundError(args.tex_font_root)
        os.environ["TEXFONTS"] = args.tex_font_root.resolve().as_posix() + "//"
    if args.tex_font_map_dir is not None:
        if not (args.tex_font_map_dir / "pdftex.map").is_file():
            raise FileNotFoundError("pdftex.map in --tex-font-map-dir")
        os.environ["TEXFONTMAPS"] = args.tex_font_map_dir.resolve().as_posix() + os.pathsep
    # Missing installed vector fonts are errors, not automatic bitmap fallback.
    os.environ["MKTEXPK"] = "0"
    os.environ["MKTEXMF"] = "0"
    if args.tex_bin_dir is not None:
        if not (args.tex_bin_dir / "pdflatex.exe").is_file() and not (args.tex_bin_dir / "pdflatex").is_file():
            raise FileNotFoundError("pdflatex in --tex-bin-dir")
        os.environ["PATH"] = str(args.tex_bin_dir.resolve()) + os.pathsep + os.environ.get("PATH", "")
    for name in ("cmr8.pfb", "cmmi8.pfb", "utmr8a.pfb"):
        found = subprocess.run(["kpsewhich", name], capture_output=True, text=True, check=True)
        if not found.stdout.strip() or not Path(found.stdout.strip()).is_file():
            raise FileNotFoundError(f"Installed vector font required: {name}")
    import matplotlib
    matplotlib.use("pgf")
    import matplotlib.pyplot as plt
    rounds, checked_widths = zip(*data)
    matplotlib.rcParams.update({
        "pgf.texsystem": "pdflatex", "pgf.rcfonts": False,
        "pgf.preamble": r"\usepackage[T1]{fontenc}\usepackage{times}\pagestyle{empty}",
        "font.family": "serif", "font.size": 8.5,
        "axes.labelsize": 8.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "axes.linewidth": 0.55,
    })
    # Match the original printed float rather than PGF's nominal axis height.
    # Label sizes remain native and unchanged after the pagination comparison.
    fig = plt.figure(figsize=(3.5, 4.21 / 2.54))
    ax = fig.add_axes([0.14, 0.30, 0.83, 0.65])
    ink = "#243952"
    ax.plot(rounds, [k + 1 for k in rounds], color=ink, linewidth=0.7,
            label="Proved bound $k+1$")
    ax.plot(rounds, checked_widths, linestyle="none", color=ink, marker="o",
            markerfacecolor="white", markersize=4, markeredgewidth=0.7,
            label="Sharp-family checks")
    ax.plot([1, 12], [2, 2], color="0.35", linestyle="--", linewidth=0.7,
            label="Reset bound")
    ax.set(xlim=(0.8, 12.2), ylim=(0, 14), xlabel="Round $k$",
           ylabel="Frontier states")
    ax.set_xticks([1, 3, 5, 7, 9, 12])
    ax.set_yticks([0, 2, 5, 9, 13])
    ax.tick_params(length=3, width=0.55)
    ax.legend(loc="upper left", frameon=False, fontsize=8,
              handlelength=2, borderaxespad=0.35, labelspacing=0.3)
    fig.savefig(HERE / "frontier-width.pdf")
    plt.close(fig)
    print(f"Retained sharp-family checks={data}; vector PDF generated.")


if __name__ == "__main__":
    main()
