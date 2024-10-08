#!/usr/bin/env python

__description__ = """\
Elo rating system for image sorting.

Open directory with images and press <Left> or <Right> arrow key to vote for a better image. Images will be presented in random order, each vote renames image according to Elo score. Three matching rounds will be performed.

After matching, images could be observed in file manager, as they are named alphanumerically.

    "[{elo_score},{total_matches}] filename".jpg

https://www.coorpacademy.com/en/blog/learning-innovation-en/elo-whos-the-best/
"""

import pathlib
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

__software_name__ = "Picelo"


class MainWindow(tk.Tk):
    """Main window with controller."""

    def __init__(self):
        super().__init__()
        self.title(__software_name__)
        self.geometry("640x240")

        self._fp_list: list = list()
        # Saves current ranking progress, new iteration on StopIteration
        self._fp_list_iter = iter(())
        self._rounds = 0

        menubar = tk.Menu(self)  # Conventional name
        self["menu"] = menubar
        self._menu_file = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=self._menu_file)
        self._menu_file.add_command(
            label="Open directory", command=self.open_directory, accelerator="Ctrl+O"
        )
        self._menu_file.add_command(
            label="Reset score", command=self.reset_score, state=tk.DISABLED
        )
        self._menu_file.add_command(
            label="Exit", command=self.destroy, accelerator="Esc"
        )

        menu_help = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=menu_help)
        menu_help.add_command(
            label="Help...",
            command=lambda: messagebox.showinfo(
                parent=self,
                title="Help",
                message=__software_name__,
                detail=__description__,
            ),
        )

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-o>", self.open_directory)

        self.bind("<Left>", self.arrow_press)
        self.bind("<Right>", self.arrow_press)

        # https://stackoverflow.com/questions/38171036/make-two-frames-occupy-50-of-the-available-width-each
        img_frame = ttk.PanedWindow(orient=tk.HORIZONTAL, style="Black.TPanedwindow")
        self._img_left = ImageView(img_frame)
        self._img_left._lbl["style"] = "Left.TLabel"
        self._img_right = ImageView(img_frame)
        self._img_right._lbl["style"] = "Right.TLabel"

        img_frame.add(self._img_left, weight=1)
        img_frame.add(self._img_right, weight=1)
        img_frame.pack(expand=True, fill=tk.BOTH)

    def open_directory(self, event=None):
        if pic_dir := filedialog.askdirectory(
            parent=self, mustexist=True, title="Choose directory with pictures"
        ):
            # Remove unsupported formats
            pil_file_extensions = Image.registered_extensions().keys() - {".pdf"}

            # Recursive
            self._rounds = 0  # Start scoring again
            self._fp_list = list()
            for p in pathlib.Path(pic_dir).glob("**/*"):
                if p.suffix in pil_file_extensions:
                    self._fp_list.append(RankFileModel(p.resolve()))

            # Limit to 3 match rounds
            # self._fp_list = list(filter(lambda k: k.matches < 3, [RankFileModel(k) for k in self._fp_list]))
            if not self._fp_list:
                messagebox.showerror(message="Images not found")

            print(f"{len(self._fp_list)} images to sort")
            self.load_next()
            self._menu_file.entryconfigure("Reset score", state=tk.NORMAL)

    def reset_score(self):
        resp = messagebox.askyesno(
            title="Reset score",
            message="Restore original file names?",
            detail="Scores for current directory tree will be permanently lost.",
        )
        if resp:
            for p in self._fp_list:
                p.reset_name()

    def arrow_press(self, event=None):
        if event.keysym == "Left" and self._img_left:
            self.title(self._img_left.model.filename())
            self._img_left.model.wins_over(self._img_right.model)
        elif event.keysym == "Right" and self._img_right:
            self.title(self._img_right.model.filename())
            self._img_right.model.wins_over(self._img_left.model)

        if not any((self._img_left, self._img_right)):
            self.title(__software_name__)
        self.load_next()

    def load_next(self):
        """Shuffle images and perform N rounds of matching.

        Use iterator to store position between sequential calls.
        """
        try:
            self._img_left.set_image(next(self._fp_list_iter))
            self._img_right.set_image(next(self._fp_list_iter))
        except StopIteration:
            if self._rounds < 3:
                self._rounds += 1
                print(f"Round {self._rounds}")
                random.shuffle(self._fp_list)
                self._fp_list_iter = iter(self._fp_list)
                self.load_next()
            else:
                self._img_left.unset_image()
                self._img_right.unset_image()


class ImageView(ttk.Frame):
    """Tkinter image viewer.

    PIL.ImageTk.PhotoImage doesn't have `.blank()` method, but tk.PhotoImage does.
    """

    def __init__(self, master=None):
        super().__init__(master)
        self.model: RankFileModel = None
        self._img: Image | None  # Cached image for resize
        self._img_tk: ImageTk.PhotoImage  # Keep reference for GC
        self._lbl = ttk.Label(self, compound=tk.BOTTOM, anchor=tk.CENTER)
        self._lbl.pack(expand=True, fill=tk.BOTH)
        self._lbl.bind("<Configure>", self._render)

        # Zoom controls
        # self.btn_zoom_m = ttk.Button(self, text="🔍−")
        # self.btn_zoom_m.pack(side=tk.LEFT)
        # self.btn_zoom_p = ttk.Button(self, text="🔍+")
        # self.btn_zoom_p.pack(side=tk.LEFT)
        # self.btn_zoom_p = ttk.Button(self, text="🔍 1:1")
        # self.btn_zoom_p.pack(side=tk.LEFT)
        # self.btn_zoom_p = ttk.Button(self, text="↷")
        # self.btn_zoom_p.pack(side=tk.LEFT)
        # self.btn_zoom_p = ttk.Button(self, text="↶")
        # self.btn_zoom_p.pack(side=tk.LEFT)
        self.unset_image()

    def _render(self, event=None):
        if self:
            # Keep aspect ratio
            image_ar = self._img.width / self._img.height
            widget_ar = self._lbl.winfo_width() / self._lbl.winfo_height()
            if widget_ar > image_ar:  # Height is limiting viewport
                scale = self._lbl.winfo_height() / self._img.height
            else:
                scale = self._lbl.winfo_width() / self._img.width

            preview = self._img.resize(
                (int(self._img.width * scale), int(self._img.height * scale))
            )
            self._img_tk = ImageTk.PhotoImage(preview)
            self._lbl["image"] = self._img_tk

    def set_image(self, rf):
        self.model = rf
        self._lbl["text"] = self.model.filename()
        self._img = Image.open(self.model.get_fp())
        self._render()

    def unset_image(self):
        self.model = None
        self._lbl["text"] = "No image"
        self._img = None
        self._lbl["image"] = ""

    def __bool__(self):
        return self.model is not None

    # def zoom(self, event=None):
    #     if self._img:
    #         self._img_tk = ImageTk.PhotoImage(self._img)
    #         self._lbl["image"] = self._img_tk.subsample(2)
    #     # self._img = self._img_tk.zoom(2)


class RankFileModel:
    """Image data model (image path, Elo score).

    Defaults are magic numbers, I didn't validate it.
    3 rounds of mathing are expected.

    Args:
        fp: File path
        score: Default Elo score for new unrated image
        k: Default max gain/loose per match

    References:
        [1] https://github.com/iain/elo?tab=readme-ov-file#label-About+the+K-factor
    """

    def __init__(
        self,
        fp: pathlib.Path,
        score: float = 1400,
        k: float = 32,
    ):
        self._fp = fp
        self._fp_clean_name: str = self._fp.name  # File name without leading ratings
        self._k = k
        self.matches = 0

        # Parse rating from file name
        if self._fp.stem.startswith("[") and "] " in self._fp.name:
            ratings, _, self._fp_clean_name = self._fp.name[1:].partition("] ")
            score, matches = (int(r) for r in ratings.split(","))
            self.matches = matches

        self.score = score

    def filename(self) -> str:
        """Name with elo score prefix."""
        return f"[{self.score:04.0f},{self.matches:.0f}] {self._fp_clean_name}"

    def update_name(self):
        """Rename file according to current rating."""
        self._fp = self._fp.rename(self._fp.parent / self.filename())

    def reset_name(self):
        """Restore original file name without Elo prefix."""
        self._fp = self._fp.rename(self._fp.parent / self._fp_clean_name)

    def get_fp(self) -> pathlib.Path:
        return self._fp

    def wins_over(self, looser):
        """Recalculate rationgs and rename both images."""
        # Current ratings
        R_a = self.score
        R_b = looser.score

        # Expectation
        E_a = 1 / (1 + 10 ** ((R_a - R_b) / 400))
        E_b = 1 / (1 + 10 ** ((R_b - R_a) / 400))

        # New ratings
        self.score = R_a + self._k * (1 - E_a)
        looser.score = R_b + self._k * (0 - E_b)

        self.matches += 1
        looser.matches += 1
        self.update_name()
        looser.update_name()


def main():
    root = MainWindow()
    ss = ttk.Style()
    ss.configure("Black.TPanedwindow", background="black")
    ss.configure("Left.TLabel", background="blue")
    ss.configure("Right.TLabel", background="red")
    root.mainloop()


if __name__ == "__main__":
    main()
