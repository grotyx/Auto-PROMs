"""
Custom reusable widgets for Auto Spine Survey v2.1
FileCard, LogPanel, DropZone - built on CustomTkinter
"""

import customtkinter as ctk
import platform
from tkinter import filedialog


def get_platform_font():
    """Return platform-appropriate Korean font family."""
    system = platform.system()
    if system == "Windows":
        return "맑은 고딕"
    elif system == "Darwin":
        return "AppleSDGothicNeo-Regular"
    return "Noto Sans CJK KR"


FONT_FAMILY = get_platform_font()

STATUS_ICONS = {
    "waiting": "\u23f3",
    "processing": "\U0001f504",
    "complete": "\u2705",
    "error": "\u274c",
}


class FileCard(ctk.CTkFrame):
    """A single file entry card with status icon and filename."""

    def __init__(self, master, filename: str, status: str = "waiting", **kwargs):
        super().__init__(master, corner_radius=6, height=36, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_propagate(False)

        self._filename = filename
        self._status = status

        self.status_label = ctk.CTkLabel(
            self, text=STATUS_ICONS.get(status, ""),
            font=(FONT_FAMILY, 14), width=30,
        )
        self.status_label.grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")

        self.name_label = ctk.CTkLabel(
            self, text=filename,
            font=(FONT_FAMILY, 12), anchor="w",
        )
        self.name_label.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.detail_label = ctk.CTkLabel(
            self, text="",
            font=(FONT_FAMILY, 10), text_color="gray60", anchor="e",
        )
        self.detail_label.grid(row=0, column=2, padx=(4, 10), pady=4, sticky="e")

    @property
    def filename(self) -> str:
        return self._filename

    def set_status(self, status: str, detail_text: str = ""):
        """Update card status icon and optional detail text."""
        self._status = status
        self.status_label.configure(text=STATUS_ICONS.get(status, ""))
        if detail_text:
            self.detail_label.configure(text=detail_text)

    def get_status(self) -> str:
        return self._status


class LogPanel(ctk.CTkFrame):
    """Collapsible log viewer panel."""

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=8, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._expanded = False

        # Toggle button row
        self.toggle_btn = ctk.CTkButton(
            self, text="\u25bc \ub85c\uadf8",
            font=(FONT_FAMILY, 12), height=30,
            fg_color="transparent", text_color=("gray30", "gray70"),
            hover_color=("gray85", "gray25"),
            command=self.toggle,
        )
        self.toggle_btn.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))

        # Textbox (hidden initially)
        self.textbox = ctk.CTkTextbox(
            self, font=("Courier", 11), height=140,
            state="disabled", wrap="word",
        )

    def toggle(self):
        """Toggle log panel visibility."""
        if self._expanded:
            self.textbox.grid_forget()
            self.toggle_btn.configure(text="\u25bc \ub85c\uadf8")
            self._expanded = False
        else:
            self.textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
            self.grid_rowconfigure(1, weight=1)
            self.toggle_btn.configure(text="\u25b2 \ub85c\uadf8")
            self._expanded = True

    def append_log(self, message: str):
        """Append a log message."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        """Clear all log messages."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class DropZone(ctk.CTkFrame):
    """Drag-and-drop area with visual feedback and click-to-browse."""

    def __init__(self, master, on_files_dropped=None, **kwargs):
        super().__init__(master, corner_radius=10, height=160, border_width=2,
                         border_color=("gray70", "gray40"), **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_propagate(False)

        self._on_files_dropped = on_files_dropped
        self._has_dnd = False

        # Content container
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        self.icon_label = ctk.CTkLabel(
            content, text="\U0001f4c1",
            font=(FONT_FAMILY, 48),
        )
        self.icon_label.pack(pady=(0, 8))

        self.main_label = ctk.CTkLabel(
            content, text="PDF \ud30c\uc77c\uc744 \ub4dc\ub798\uadf8\ud558\uc138\uc694",
            font=(FONT_FAMILY, 14, "bold"),
        )
        self.main_label.pack(pady=(0, 4))

        self.sub_label = ctk.CTkLabel(
            content, text="\ub610\ub294 \ud074\ub9ad\ud558\uc5ec \uc120\ud0dd",
            font=(FONT_FAMILY, 11),
            text_color="gray50",
        )
        self.sub_label.pack()

        # Click to browse - bind to all child widgets
        for widget in [self, content, self.icon_label, self.main_label, self.sub_label]:
            widget.bind("<Button-1>", lambda e: self._browse_files())

        # Hover feedback
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Attempt DnD setup (Windows with tkinterdnd2)
        self._setup_dnd()

    def _setup_dnd(self):
        """Try to register drag-and-drop on Windows."""
        if platform.system() != "Windows":
            self.sub_label.configure(
                text="\ud074\ub9ad\ud558\uc5ec \ud30c\uc77c \uc120\ud0dd"
            )
            return
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            self._has_dnd = True
        except Exception:
            self.sub_label.configure(
                text="\ud074\ub9ad\ud558\uc5ec \ud30c\uc77c \uc120\ud0dd"
            )

    def _browse_files(self):
        files = filedialog.askopenfilenames(
            title="PDF \ud30c\uc77c \uc120\ud0dd",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if files and self._on_files_dropped:
            self._on_files_dropped(list(files))

    def _on_drop(self, event):
        files = self.tk.splitlist(event.data)
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        if pdf_files and self._on_files_dropped:
            self._on_files_dropped(pdf_files)
        self._reset_style()
        return event.action

    def _on_drag_enter(self, event):
        self.configure(border_color=("#3B8ED0", "#3B8ED0"))
        self.configure(fg_color=("gray90", "gray20"))
        return event.action

    def _on_drag_leave(self, event):
        self._reset_style()

    def _on_enter(self, event):
        self.configure(fg_color=("gray92", "gray22"))

    def _on_leave(self, event):
        self._reset_style()

    def _reset_style(self):
        self.configure(
            border_color=("gray70", "gray40"),
            fg_color=("gray95", "gray17"),
        )
