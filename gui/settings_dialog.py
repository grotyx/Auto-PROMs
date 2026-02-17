"""
Auto Spine Survey v2.1 - Settings Dialog
CustomTkinter-based settings with CTkTabview.
Preserves Phase 1 .env read/write logic for API keys.
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .widgets import FONT_FAMILY
from core import PROJECT_ROOT

_SCRIPT_DIR = PROJECT_ROOT

_ENV_PATH = _SCRIPT_DIR / ".env"
_CONFIG_PATH = _SCRIPT_DIR / "config.json"


def _load_env_key(key: str) -> str:
    """Load an API key from .env (re-read file each time)."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    return os.getenv(key, "")


def _save_env_keys(claude_key: str, openai_key: str):
    """Save API keys to .env file."""
    lines = []
    if claude_key:
        lines.append(f"CLAUDE_API_KEY={claude_key}")
    if openai_key:
        lines.append(f"OPENAI_API_KEY={openai_key}")

    with open(_ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    if claude_key:
        os.environ["CLAUDE_API_KEY"] = claude_key
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key


class SettingsDialog:
    def __init__(self, parent):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("\uc124\uc815")
        self.dialog.geometry("620x620")
        self.dialog.resizable(False, False)

        # Modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Load config
        self._load_config()

        # Build UI
        self._create_widgets()

        # Center
        self._center_window()

    # ------------------------------------------------------------------
    # Config I/O
    # ------------------------------------------------------------------

    def _load_config(self):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            messagebox.showerror("\uc624\ub958", f"\uc124\uc815 \ud30c\uc77c\uc744 \ub85c\ub4dc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: {str(e)}")
            self.config = {}

        self.claude_api_key = _load_env_key("CLAUDE_API_KEY")
        self.openai_api_key = _load_env_key("OPENAI_API_KEY")

    def _save_config_json(self) -> bool:
        try:
            with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("\uc624\ub958", f"\uc124\uc815 \ud30c\uc77c\uc744 \uc800\uc7a5\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _create_widgets(self):
        # Tabview
        self.tabview = ctk.CTkTabview(self.dialog, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(14, 8))

        self.tabview.add("API \uc124\uc815")
        self.tabview.add("\ud3f4\ub354 \uc124\uc815")
        self.tabview.add("\ucc98\ub9ac \uc124\uc815")
        self.tabview.add("\ucd9c\ub825 \uc124\uc815")

        self._create_api_tab(self.tabview.tab("API \uc124\uc815"))
        self._create_folder_tab(self.tabview.tab("\ud3f4\ub354 \uc124\uc815"))
        self._create_processing_tab(self.tabview.tab("\ucc98\ub9ac \uc124\uc815"))
        self._create_output_tab(self.tabview.tab("\ucd9c\ub825 \uc124\uc815"))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(
            btn_frame, text="\ucde8\uc18c", width=80, height=34,
            fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray90"),
            command=self.dialog.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="\uc800\uc7a5", width=80, height=34,
            command=self._save_settings,
        ).pack(side="right")

        # Copyright
        ctk.CTkLabel(
            self.dialog,
            text=(
                "\u00a9 2025 Seoul National University College of Medicine, "
                "Department of Orthopaedic Surgery\n"
                "Developed by Sang-Min Park | All rights reserved"
            ),
            font=("Arial", 9), text_color="gray50", justify="center",
        ).pack(pady=(2, 10))

    # -- API tab --------------------------------------------------------

    def _create_api_tab(self, tab):
        # Provider selection
        provider_label = ctk.CTkLabel(tab, text="AI \ud504\ub85c\ubc14\uc774\ub354", font=(FONT_FAMILY, 13, "bold"))
        provider_label.pack(anchor="w", padx=10, pady=(10, 6))

        self.provider_var = ctk.StringVar(
            value=self.config.get("api_settings", {}).get("provider", "claude")
        )
        radio_frame = ctk.CTkFrame(tab, fg_color="transparent")
        radio_frame.pack(anchor="w", padx=20)

        ctk.CTkRadioButton(
            radio_frame, text="Claude (\uae30\ubcf8)", font=(FONT_FAMILY, 12),
            variable=self.provider_var, value="claude",
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            radio_frame, text="OpenAI GPT-4", font=(FONT_FAMILY, 12),
            variable=self.provider_var, value="openai",
        ).pack(side="left")

        # Claude section
        ctk.CTkLabel(tab, text="Claude \uc124\uc815", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(16, 6)
        )
        claude_frame = ctk.CTkFrame(tab, fg_color="transparent")
        claude_frame.pack(fill="x", padx=20)
        claude_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(claude_frame, text="API Key:", font=(FONT_FAMILY, 12)).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.claude_key_var = ctk.StringVar(value=self.claude_api_key)
        ctk.CTkEntry(claude_frame, textvariable=self.claude_key_var, show="*").grid(
            row=0, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        ctk.CTkLabel(claude_frame, text="\ubaa8\ub378:", font=(FONT_FAMILY, 12)).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.claude_model_var = ctk.StringVar(
            value=self.config.get("api_settings", {}).get("claude_model", "claude-haiku-4-5-20251001")
        )
        ctk.CTkEntry(claude_frame, textvariable=self.claude_model_var).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        # OpenAI section
        ctk.CTkLabel(tab, text="OpenAI \uc124\uc815", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(16, 6)
        )
        openai_frame = ctk.CTkFrame(tab, fg_color="transparent")
        openai_frame.pack(fill="x", padx=20)
        openai_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(openai_frame, text="API Key:", font=(FONT_FAMILY, 12)).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.openai_key_var = ctk.StringVar(value=self.openai_api_key)
        ctk.CTkEntry(openai_frame, textvariable=self.openai_key_var, show="*").grid(
            row=0, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        ctk.CTkLabel(openai_frame, text="\ubaa8\ub378:", font=(FONT_FAMILY, 12)).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.openai_model_var = ctk.StringVar(
            value=self.config.get("api_settings", {}).get("openai_model", "gpt-5-mini")
        )
        ctk.CTkEntry(openai_frame, textvariable=self.openai_model_var).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=4
        )

    # -- Folder tab -----------------------------------------------------

    def _create_folder_tab(self, tab):
        folders = self.config.get("folders", {})
        self.folder_vars = {}

        folder_items = [
            ("input_folder", "\uc785\ub825 \ud3f4\ub354:"),
            ("output_folder", "\ucd9c\ub825 \ud3f4\ub354:"),
            ("temp_folder", "\uc784\uc2dc \ud3f4\ub354:"),
            ("logs_folder", "\ub85c\uadf8 \ud3f4\ub354:"),
        ]

        for row, (key, label) in enumerate(folder_items):
            ctk.CTkLabel(tab, text=label, font=(FONT_FAMILY, 12)).grid(
                row=row, column=0, sticky="w", padx=10, pady=8
            )
            self.folder_vars[key] = ctk.StringVar(value=folders.get(key, ""))
            ctk.CTkEntry(tab, textvariable=self.folder_vars[key], width=340).grid(
                row=row, column=1, padx=6, pady=8
            )
            ctk.CTkButton(
                tab, text="\ucc3e\uae30", width=60, height=28,
                command=lambda k=key: self._browse_folder(k),
            ).grid(row=row, column=2, padx=(0, 10), pady=8)

        tab.grid_columnconfigure(1, weight=1)

    # -- Processing tab -------------------------------------------------

    def _create_processing_tab(self, tab):
        processing = self.config.get("processing", {})

        # Pages per survey
        ctk.CTkLabel(tab, text="\ud398\uc774\uc9c0 \uc124\uc815", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        page_frame = ctk.CTkFrame(tab, fg_color="transparent")
        page_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(page_frame, text="\uc124\ubb38\ub2f9 \ud398\uc774\uc9c0 \uc218:", font=(FONT_FAMILY, 12)).pack(
            side="left"
        )
        self.pages_var = ctk.IntVar(value=processing.get("pages_per_survey", 6))
        ctk.CTkEntry(page_frame, textvariable=self.pages_var, width=80).pack(
            side="left", padx=(8, 0)
        )

        # AI settings
        ctk.CTkLabel(tab, text="AI \uc124\uc815", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        ai_frame = ctk.CTkFrame(tab, fg_color="transparent")
        ai_frame.pack(fill="x", padx=20, pady=(0, 10))
        ai_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ai_frame, text="\ucd5c\ub300 \ud1a0\ud070:", font=(FONT_FAMILY, 12)).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.tokens_var = ctk.IntVar(value=processing.get("max_tokens", 2000))
        ctk.CTkEntry(ai_frame, textvariable=self.tokens_var, width=100).grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=4
        )

        ctk.CTkLabel(ai_frame, text="Temperature:", font=(FONT_FAMILY, 12)).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.temp_var = ctk.DoubleVar(value=processing.get("temperature", 0))
        self.temp_slider = ctk.CTkSlider(
            ai_frame, from_=0, to=1, number_of_steps=10,
            variable=self.temp_var, width=200,
        )
        self.temp_slider.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)
        self.temp_value_label = ctk.CTkLabel(
            ai_frame, text=f"{self.temp_var.get():.1f}", font=(FONT_FAMILY, 11),
        )
        self.temp_value_label.grid(row=1, column=2, padx=6, pady=4)
        self.temp_var.trace_add("write", self._on_temp_change)

        # Concurrency
        ctk.CTkLabel(tab, text="\ub3d9\uc2dc \ucc98\ub9ac", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        conc_frame = ctk.CTkFrame(tab, fg_color="transparent")
        conc_frame.pack(fill="x", padx=20)

        self.concurrent_var = ctk.BooleanVar(
            value=self.config.get("processing", {}).get("concurrent_enabled", False)
        )
        ctk.CTkSwitch(
            conc_frame, text="\ub3d9\uc2dc \ucc98\ub9ac \ud65c\uc131\ud654",
            font=(FONT_FAMILY, 12), variable=self.concurrent_var,
        ).pack(side="left")

        ctk.CTkLabel(conc_frame, text="\ucd5c\ub300 \uc694\uccad:", font=(FONT_FAMILY, 12)).pack(
            side="left", padx=(20, 4)
        )
        self.max_conc_var = ctk.IntVar(
            value=self.config.get("processing", {}).get("max_concurrent_requests", 3)
        )
        ctk.CTkEntry(conc_frame, textvariable=self.max_conc_var, width=60).pack(side="left")

    def _on_temp_change(self, *_args):
        try:
            self.temp_value_label.configure(text=f"{self.temp_var.get():.1f}")
        except Exception:
            pass

    # -- Output tab -----------------------------------------------------

    def _create_output_tab(self, tab):
        output = self.config.get("output", {})

        ctk.CTkLabel(tab, text="\ud30c\uc77c\uba85 \uc124\uc815", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        fn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        fn_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(fn_frame, text="\uae30\ubcf8 \ud30c\uc77c\uba85:", font=(FONT_FAMILY, 12)).pack(
            side="left"
        )
        self.filename_var = ctk.StringVar(
            value=output.get("csv_filename", "spine_survey_results.csv")
        )
        ctk.CTkEntry(fn_frame, textvariable=self.filename_var, width=280).pack(
            side="left", padx=(8, 0)
        )

        ctk.CTkLabel(tab, text="\ucd9c\ub825 \uc635\uc158", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        opt_frame = ctk.CTkFrame(tab, fg_color="transparent")
        opt_frame.pack(fill="x", padx=20)

        self.timestamp_var = ctk.BooleanVar(value=output.get("include_timestamps", True))
        ctk.CTkSwitch(
            opt_frame, text="\ud30c\uc77c\uba85\uc5d0 \ud0c0\uc784\uc2a4\ud0ec\ud504 \ud3ec\ud568",
            font=(FONT_FAMILY, 12), variable=self.timestamp_var,
        ).pack(anchor="w", pady=4)

        self.backup_var = ctk.BooleanVar(value=output.get("backup_results", True))
        ctk.CTkSwitch(
            opt_frame, text="\ubc31\uc5c5 \ud30c\uc77c \uc0dd\uc131",
            font=(FONT_FAMILY, 12), variable=self.backup_var,
        ).pack(anchor="w", pady=4)

        # Theme selection
        ctk.CTkLabel(tab, text="\ud14c\ub9c8", font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", padx=10, pady=(16, 6)
        )
        theme_frame = ctk.CTkFrame(tab, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20)

        self.theme_var = ctk.StringVar(value=ctk.get_appearance_mode().lower())
        for mode_val, mode_label in [("system", "System"), ("light", "Light"), ("dark", "Dark")]:
            ctk.CTkRadioButton(
                theme_frame, text=mode_label, font=(FONT_FAMILY, 12),
                variable=self.theme_var, value=mode_val,
            ).pack(side="left", padx=(0, 14))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_folder(self, key):
        folder = filedialog.askdirectory(initialdir=self.folder_vars[key].get())
        if folder:
            self.folder_vars[key].set(folder)

    def _save_settings(self):
        try:
            # API settings (provider + models go to config.json)
            self.config.setdefault("api_settings", {})
            self.config["api_settings"]["provider"] = self.provider_var.get()
            self.config["api_settings"]["claude_model"] = self.claude_model_var.get()
            self.config["api_settings"]["openai_model"] = self.openai_model_var.get()

            # Folders
            self.config.setdefault("folders", {})
            for key, var in self.folder_vars.items():
                self.config["folders"][key] = var.get()

            # Processing
            self.config.setdefault("processing", {})
            self.config["processing"]["pages_per_survey"] = self.pages_var.get()
            self.config["processing"]["max_tokens"] = self.tokens_var.get()
            self.config["processing"]["temperature"] = self.temp_var.get()
            self.config["processing"]["concurrent_enabled"] = self.concurrent_var.get()
            self.config["processing"]["max_concurrent_requests"] = self.max_conc_var.get()

            # Output
            self.config.setdefault("output", {})
            self.config["output"]["csv_filename"] = self.filename_var.get()
            self.config["output"]["include_timestamps"] = self.timestamp_var.get()
            self.config["output"]["backup_results"] = self.backup_var.get()

            # API keys -> .env (Phase 1 logic preserved)
            _save_env_keys(
                claude_key=self.claude_key_var.get(),
                openai_key=self.openai_key_var.get(),
            )

            # Apply theme
            ctk.set_appearance_mode(self.theme_var.get())

            # Save config.json (no API keys)
            if self._save_config_json():
                messagebox.showinfo("\uc131\uacf5", "\uc124\uc815\uc774 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.")
                self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("\uc624\ub958", f"\uc124\uc815 \uc800\uc7a5 \uc911 \uc624\ub958 \ubc1c\uc0dd: {str(e)}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")
