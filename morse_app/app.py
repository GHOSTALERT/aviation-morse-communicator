"""Aviation Morse Code Communicator: Tkinter GUI.

Four sections, as in the report:
  Learn        reference chart; click a symbol to hear it and see the lamp
  Encode       text -> Morse, play it, save it as a WAV file
  Decode       Morse -> text, or decode a recorded WAV file
  Application  aircraft-to-ATC transmission: approach, transmit, depart
"""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import audio, dsp
from . import morse as m

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

ASSETS = Path(__file__).resolve().parent.parent / "assets"

BG = "#0f1720"
PANEL = "#18222d"
FG = "#e6edf3"
ACCENT = "#f5c542"
MONO = ("DejaVu Sans Mono", 12)

CANVAS_W, CANVAS_H = 800, 400
FPS = 60


class MorseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.anim_running = {"value": False}
        self.stop_event = threading.Event()

        root.title("Aviation Morse Code Communicator")
        root.geometry("900x660")
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 6), font=("DejaVu Sans", 11, "bold"))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("DejaVu Sans", 11))
        style.configure("Title.TLabel", font=("DejaVu Sans", 16, "bold"), foreground=ACCENT)
        style.configure("TButton", font=("DejaVu Sans", 10, "bold"), padding=6)

        ttk.Label(root, text="Aviation Morse Code Communicator", style="Title.TLabel").pack(pady=(10, 4))

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=10, pady=6)
        self._learn_tab(nb)
        self._encode_tab(nb)
        self._decode_tab(nb)
        self._application_tab(nb)

        self.status = tk.StringVar(value=f"Audio backend: {audio.backend()}")
        ttk.Label(root, textvariable=self.status, font=("DejaVu Sans", 9)).pack(anchor="w", padx=12, pady=(0, 6))

    # ------------------------------------------------------------ helpers

    def _text(self, parent, height):
        t = tk.Text(parent, height=height, wrap="word", font=MONO, bg=PANEL, fg=FG,
                    insertbackground=FG, relief="flat", padx=8, pady=6)
        return t

    def _set_text(self, widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def _get_text(self, widget):
        return widget.get("1.0", "end").strip()

    def _lamp(self, parent, size=28):
        c = tk.Canvas(parent, width=size, height=size, bg=BG, highlightthickness=0)
        item = c.create_oval(3, 3, size - 3, size - 3, fill="black", outline="gray", width=2)
        return c, item

    def play(self, morse_code, on, off, done=None):
        """Start threaded playback unless something is already playing."""
        if self.anim_running["value"]:
            return False
        self.anim_running["value"] = True
        self.stop_event.clear()

        def finished():
            self.anim_running["value"] = False
            if done:
                done()
        audio.play_morse_sound_threaded(self.root, morse_code, on, off, finished, self.stop_event)
        return True

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()

    # ------------------------------------------------------------ Learn

    def _learn_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Learn Morse Code")
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=8)
        ttk.Label(top, text="Click any character to hear it. Dot = 150 ms, dash = 450 ms, tone 700 Hz.").pack(side="left", padx=8)
        lamp, item = self._lamp(top)
        lamp.pack(side="right", padx=12)

        grid = ttk.Frame(tab)
        grid.pack(padx=8, pady=4)
        chars = [c for c in m.MORSE_CODE_DICT if c != ' ']
        for i, ch in enumerate(chars):
            code = m.MORSE_CODE_DICT[ch]
            b = tk.Button(grid, text=f"{ch}\n{code}", width=6, height=2, font=("DejaVu Sans Mono", 11, "bold"),
                          bg=PANEL, fg=FG, activebackground="#2b3a4a", activeforeground=ACCENT, relief="flat",
                          command=lambda c=code: self.play(
                              c, lambda: lamp.itemconfig(item, fill="yellow"),
                              lambda: lamp.itemconfig(item, fill="black")))
            b.grid(row=i // 9, column=i % 9, padx=3, pady=3)

        if PIL_AVAILABLE and (ASSETS / "morse_chart.png").exists():
            img = Image.open(ASSETS / "morse_chart.png")
            img.thumbnail((450, 500))
            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(tab, image=img_tk, bg=BG)
            label.image = img_tk  # keep a reference so Tk does not drop it
            label.pack(pady=6)

    # ------------------------------------------------------------ Encode

    def _encode_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Encode Text")
        ttk.Label(tab, text="Text:").pack(anchor="w", padx=10, pady=(10, 2))
        self.enc_in = self._text(tab, 4)
        self.enc_in.pack(fill="x", padx=10)
        self.enc_in.insert("1.0", "MAYDAY MAYDAY MAYDAY")

        row = ttk.Frame(tab)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Button(row, text="Encode", command=self.do_encode).pack(side="left")
        ttk.Button(row, text="Play", command=self.do_play_encoded).pack(side="left", padx=6)
        ttk.Button(row, text="Save WAV...", command=self.do_save_wav).pack(side="left")
        ttk.Button(row, text="Copy", command=self.do_copy).pack(side="left", padx=6)
        lamp, item = self._lamp(row)
        lamp.pack(side="right")
        self.enc_lamp = (lamp, item)

        ttk.Label(tab, text="Morse (letters separated by a space, words by /):").pack(anchor="w", padx=10, pady=(6, 2))
        self.enc_out = self._text(tab, 6)
        self.enc_out.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.enc_info = tk.StringVar()
        ttk.Label(tab, textvariable=self.enc_info).pack(anchor="w", padx=10, pady=(0, 8))

    def do_encode(self):
        text = self._get_text(self.enc_in)
        code = m.encode_to_morse(text)
        self._set_text(self.enc_out, code)
        skipped = sorted({c for c in text.upper() if c not in m.MORSE_CODE_DICT and not c.isspace()})
        info = f"{len(code.split())} symbols, playback {m.duration_ms(code) / 1000:.1f} s"
        if skipped:
            info += f"; skipped characters with no Morse code: {' '.join(skipped)}"
        self.enc_info.set(info)
        return code

    def do_play_encoded(self):
        code = self._get_text(self.enc_out) or self.do_encode()
        lamp, item = self.enc_lamp
        self.play(code, lambda: lamp.itemconfig(item, fill="yellow"),
                  lambda: lamp.itemconfig(item, fill="black"))

    def do_save_wav(self):
        code = self._get_text(self.enc_out) or self.do_encode()
        if not code:
            return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV audio", "*.wav")])
        if path:
            dsp.write_wav(path, dsp.synthesize(code))
            self.status.set(f"Saved {path}")

    def do_copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self._get_text(self.enc_out))
        self.status.set("Morse copied to clipboard")

    # ------------------------------------------------------------ Decode

    def _decode_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Decode Morse")
        ttk.Label(tab, text="Morse code:").pack(anchor="w", padx=10, pady=(10, 2))
        self.dec_in = self._text(tab, 4)
        self.dec_in.pack(fill="x", padx=10)
        self.dec_in.insert("1.0", "... --- ...")

        row = ttk.Frame(tab)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Button(row, text="Decode", command=self.do_decode).pack(side="left")
        ttk.Button(row, text="Decode WAV file...", command=self.do_decode_wav).pack(side="left", padx=6)

        ttk.Label(tab, text="Text:").pack(anchor="w", padx=10, pady=(6, 2))
        self.dec_out = self._text(tab, 4)
        self.dec_out.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.dec_info = tk.StringVar()
        ttk.Label(tab, textvariable=self.dec_info).pack(anchor="w", padx=10, pady=(0, 8))

    def do_decode(self):
        code = self._get_text(self.dec_in)
        if not m.is_valid_morse(code):
            messagebox.showwarning("Decode", "Use only '.', '-', spaces and '/'.")
            return
        self._set_text(self.dec_out, m.decode_from_morse(code))
        self.dec_info.set("")

    def do_decode_wav(self):
        path = filedialog.askopenfilename(filetypes=[("WAV audio", "*.wav")])
        if not path:
            return
        x, fs = dsp.read_wav(path)
        a = dsp.analyse(x, fs)
        self._set_text(self.dec_in, a.morse)
        self._set_text(self.dec_out, a.text)
        self.dec_info.set(f"Tone {a.tone_hz:.0f} Hz, dot length {a.unit_s * 1000:.0f} ms, "
                          f"{len(a.tones)} elements detected")

    # ------------------------------------------------------------ Application

    def _application_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Application")

        row = ttk.Frame(tab)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Label(row, text="Message:").pack(side="left")
        self.app_msg = tk.StringVar(value="MAYDAY MAYDAY MAYDAY")
        ttk.Entry(row, textvariable=self.app_msg, width=30, font=MONO).pack(side="left", padx=6)
        ttk.Button(row, text="Transmit", command=self.do_transmit).pack(side="left")

        presets = ttk.Frame(tab)
        presets.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(presets, text="Presets:").pack(side="left")
        for name, msg in m.PRESETS.items():
            ttk.Button(presets, text=name, command=lambda s=msg: (self.app_msg.set(s), self.do_transmit())
                       ).pack(side="left", padx=3)

        self.canvas = tk.Canvas(tab, width=CANVAS_W, height=CANVAS_H, bg="#7fb2e5", highlightthickness=0)
        self.canvas.pack(padx=10, pady=(0, 10))
        self._draw_scene()

    def _draw_scene(self):
        c = self.canvas
        c.create_rectangle(0, 300, CANVAS_W, CANVAS_H, fill="#5d8a4e", outline="")
        c.create_rectangle(0, 330, CANVAS_W, 350, fill="#444", outline="")
        for x in range(10, CANVAS_W, 60):
            c.create_rectangle(x, 338, x + 30, 342, fill="white", outline="")
        # Control tower
        c.create_rectangle(640, 170, 670, 300, fill="#c9c9c9", outline="#666")
        c.create_polygon(620, 150, 690, 150, 680, 175, 630, 175, fill="#9fd3f5", outline="#666")
        c.create_rectangle(615, 140, 695, 150, fill="#666", outline="")

        # ATC panel
        self.atc_x, self.atc_y, atc_w, atc_h = 300, 160, 180, 110
        c.create_rectangle(self.atc_x, self.atc_y, self.atc_x + atc_w, self.atc_y + atc_h,
                           fill="#222", outline="#444", width=2)
        c.create_text(self.atc_x + 10, self.atc_y + 12, text="ATC RECEIVER", anchor="w",
                      fill="#8fa3b5", font=("DejaVu Sans Mono", 9, "bold"))
        self.atc_text = c.create_text(self.atc_x + 10, self.atc_y + 34, text="", anchor="nw",
                                      width=atc_w - 20, fill="#7CFC00", font=("DejaVu Sans Mono", 10))

        # Signal lamp
        r = 12
        lx, ly = self.atc_x + atc_w - 20, self.atc_y + 20
        self.light_item = c.create_oval(lx - r, ly - r, lx + r, ly + r, fill="black", outline="gray", width=2)

        # Aircraft: image if provided, otherwise a vector silhouette
        self.plane_y = 90
        self.plane_img = None
        if PIL_AVAILABLE and (ASSETS / "airplane.png").exists():
            img = Image.open(ASSETS / "airplane.png").convert("RGBA")
            img.thumbnail((110, 60))
            self.plane_img = ImageTk.PhotoImage(img)
            self.plane_item = c.create_image(-60, self.plane_y, image=self.plane_img)
        else:
            self.plane_item = c.create_polygon(self._plane_points(-60, self.plane_y),
                                               fill="white", outline="#333", width=1)
        self.plane_x = -60

    @staticmethod
    def _plane_points(x, y):
        """Side view, nose to the right, centred on (x, y)."""
        pts = [(48, 0), (38, -6), (-30, -6), (-44, -22), (-50, -22), (-42, -6), (-48, -6),
               (-48, 4), (-6, 6), (-20, 26), (-10, 26), (14, 6), (38, 6)]
        return [v for px, py in pts for v in (x + px, y + py)]

    def _move_plane(self, x):
        self.plane_x = x
        if self.plane_img is not None:
            self.canvas.coords(self.plane_item, x, self.plane_y)
        else:
            self.canvas.coords(self.plane_item, *self._plane_points(x, self.plane_y))

    def _slide(self, start_x, end_x, duration_ms, then):
        """Move the aircraft with root.after so the Tk main loop never blocks."""
        steps = max(1, int(duration_ms * FPS / 1000))
        delay = int(1000 / FPS)

        def step(i):
            self._move_plane(start_x + (end_x - start_x) * i / steps)
            if i < steps:
                self.root.after(delay, step, i + 1)
            else:
                then()
        step(1)

    def light_on(self):
        self.canvas.itemconfig(self.light_item, fill="yellow")

    def light_off(self):
        self.canvas.itemconfig(self.light_item, fill="black")

    def do_transmit(self):
        if self.anim_running["value"]:
            self.status.set("Transmission in progress")
            return
        code = m.encode_to_morse(self.app_msg.get())
        if not code:
            messagebox.showinfo("Transmit", "Enter a message with letters or digits.")
            return
        self.anim_running["value"] = True
        self.canvas.itemconfig(self.atc_text, text="")
        end_x = self.atc_x - 40
        self.status.set("Phase 1: approach")

        def transmit():
            self.status.set(f"Phase 2: transmitting {self.app_msg.get().upper()}")
            self.canvas.itemconfig(self.atc_text, text=code)
            self.anim_running["value"] = False   # let play() take the lock
            self.play(code, self.light_on, self.light_off, done=depart)

        def depart():
            self.anim_running["value"] = True
            self.status.set("Phase 3: departure")
            self._slide(end_x, CANVAS_W + 60, 1000, finish)

        def finish():
            self._move_plane(-60)
            self.anim_running["value"] = False
            self.status.set(f"Received: {m.decode_from_morse(code)}   (audio backend: {audio.backend()})")

        self._slide(-60, end_x, 1000, transmit)


def main():
    root = tk.Tk()
    MorseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
