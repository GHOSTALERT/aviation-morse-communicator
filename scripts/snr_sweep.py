"""Recognition accuracy vs. noise, sample WAVs and an analysis figure.

    .venv/bin/python scripts/snr_sweep.py

Writes results/snr_sweep.csv, results/figures/*.png and samples/*.wav.
"""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from morse_app import dsp  # noqa: E402
from morse_app import morse as m  # noqa: E402

MESSAGES = ["SOS", "MAYDAY MAYDAY MAYDAY", "HELLO WORLD", "CQ DE VTZ 123", "PAN PAN PAN"]
SNRS = [10, 5, 0, -3, -5, -6, -7, -8, -9, -10, -12, -15]
SEEDS = range(20)


def sweep():
    rows = []
    for snr in SNRS:
        cer, exact = [], []
        for text in MESSAGES:
            code = m.encode_to_morse(text)
            for seed in SEEDS:
                out = dsp.decode_audio(dsp.synthesize(code, snr_db=snr, seed=seed))
                cer.append(dsp.char_error_rate(text, out))
                exact.append(out == text)
        rows.append({"snr_db": snr, "trials": len(cer), "char_error_rate": float(np.mean(cer)),
                     "message_accuracy": float(np.mean(exact))})
        print(f"SNR {snr:4d} dB  CER {np.mean(cer):.3f}  exact {np.mean(exact):.2f}")
    return rows


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    res = ROOT / "results"
    fig_dir = res / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "samples").mkdir(exist_ok=True)

    rows = sweep()
    with (res / "snr_sweep.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

    fig, ax = plt.subplots(figsize=(7, 4))
    snr = [r["snr_db"] for r in rows]
    ax.plot(snr, [100 * r["message_accuracy"] for r in rows], "o-", lw=2, label="messages decoded exactly")
    ax.plot(snr, [100 * (1 - min(1, r["char_error_rate"])) for r in rows], "s--", lw=2, label="1 - character error rate")
    ax.set(xlabel="SNR (dB, full band 0-4 kHz)", ylabel="%", ylim=(-5, 105),
           title=f"Morse recognition from audio ({len(MESSAGES)} messages x {len(SEEDS)} noise seeds)")
    ax.invert_xaxis()
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "snr_sweep.png", dpi=130)
    plt.close(fig)

    # Pipeline figure for one noisy MAYDAY
    code = m.encode_to_morse("MAYDAY")
    x = dsp.synthesize(code, snr_db=-3, seed=3)
    a = dsp.analyse(x)
    t = np.arange(x.size) / dsp.FS
    _, _, freqs, spec = dsp.stft_band_energy(x, dsp.FS, a.tone_hz)
    fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    axs[0].plot(t, x, lw=0.4)
    axs[0].set(ylabel="amplitude", title="MAYDAY, 700 Hz, SNR -3 dB: time signal")
    axs[1].imshow(10 * np.log10(spec.T + 1e-9), aspect="auto", origin="lower", cmap="magma",
                  extent=[a.times[0], a.times[-1], freqs[0], freqs[-1]])
    axs[1].set(ylabel="Hz", ylim=(0, 2000), title="Spectrogram (20 ms Hann window, 5 ms hop)")
    axs[2].plot(a.times, a.envelope, lw=1, label="band envelope (700 ± 60 Hz)")
    axs[2].axhline(a.threshold, color="r", ls="--", lw=1, label="threshold")
    axs[2].fill_between(a.times, 0, a.keyed * a.envelope.max(), color="tab:green", alpha=0.2, label="keyed")
    for start, dur, s in a.tones:
        axs[2].text(start + dur / 2, a.envelope.max() * 1.03, "•" if s == "." else "—", ha="center", fontsize=16)
    axs[2].set(xlabel="time (s)", ylabel="envelope",
               title=f"Detected: {a.morse}  ->  {a.text}")
    axs[2].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_dir / "pipeline_mayday.png", dpi=130)
    plt.close(fig)

    dsp.write_wav(ROOT / "samples" / "sos_clean.wav", dsp.synthesize(m.encode_to_morse("SOS")))
    dsp.write_wav(ROOT / "samples" / "mayday_snr0.wav",
                  dsp.synthesize(m.encode_to_morse("MAYDAY MAYDAY MAYDAY"), snr_db=0, seed=7))
    dsp.write_wav(ROOT / "samples" / "vor_ident_vtz.wav", dsp.synthesize(m.encode_to_morse("VTZ")))
    print("wrote results/snr_sweep.csv, results/figures/, samples/")


if __name__ == "__main__":
    main()
