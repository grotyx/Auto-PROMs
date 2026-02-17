"""
Auto Spine Survey v2.1 - Main Window
CustomTkinter-based modern GUI with dark/light mode support.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import threading
import queue
from datetime import datetime

from core.config import ConfigManager

from .widgets import DropZone, FileCard, LogPanel, FONT_FAMILY


class MainWindow:
    def __init__(self):
        # Appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Root window
        self.root = ctk.CTk()
        self.root.title("Auto Spine Survey v2.1")
        self.root.geometry("800x900")
        self.root.minsize(700, 750)

        # File tracking
        self.pdf_files = []
        self.file_status = {}
        self.file_cards = {}
        self.processed_files = set()

        # Queue and threading
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_processing = False
        self.current_thread = None

        # Ensure output and log folders exist
        self._ensure_folders()

        # Build UI
        self._create_widgets()
        self._center_window()

    # ------------------------------------------------------------------
    # Folder setup
    # ------------------------------------------------------------------

    def _ensure_folders(self):
        try:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for name in ("output_csv", "logs"):
                folder = os.path.join(base_dir, name)
                os.makedirs(folder, exist_ok=True)
        except Exception as e:
            print(f"Error creating folders: {e}")

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------

    def _create_widgets(self):
        # Main scrollable container
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        self._create_header()
        self._create_drop_zone()
        self._create_file_list()
        self._create_controls()
        self._create_progress_section()
        self._create_log_panel()
        self._create_status_bar()

    # -- Header ---------------------------------------------------------

    def _create_header(self):
        header = ctk.CTkFrame(self.main_frame, corner_radius=10)
        header.pack(fill="x", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        # Left: title + subtitle
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=16, pady=12)

        ctk.CTkLabel(
            left, text="Auto Spine Survey v2.1",
            font=(FONT_FAMILY, 22, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            left, text="AI \uae30\ubc18 \uc124\ubb38\uc9c0 \ub370\uc774\ud130 \uc790\ub3d9 \ucd94\ucd9c",
            font=(FONT_FAMILY, 12),
            text_color="gray50",
        ).pack(anchor="w", pady=(2, 0))

        # Right: theme toggle + settings + provider
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=16, pady=12)

        # Theme toggle
        self._is_dark = ctk.get_appearance_mode() == "Dark"
        self.theme_btn = ctk.CTkButton(
            right, text="\U0001f319" if self._is_dark else "\u2600\ufe0f",
            width=32, height=32, corner_radius=6,
            fg_color="transparent", hover_color=("gray85", "gray25"),
            text_color=("gray20", "gray80"),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="left", padx=(0, 6))

        # Settings button
        self.settings_header_btn = ctk.CTkButton(
            right, text="\u2699\ufe0f", width=32, height=32, corner_radius=6,
            fg_color="transparent", hover_color=("gray85", "gray25"),
            text_color=("gray20", "gray80"),
            command=self.open_settings,
        )
        self.settings_header_btn.pack(side="left", padx=(0, 12))

        # Provider badge
        config = ConfigManager()
        provider = config.get_provider()
        model_name = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"

        provider_frame = ctk.CTkFrame(right, fg_color="transparent")
        provider_frame.pack(side="left")
        ctk.CTkLabel(
            provider_frame, text="AI Provider",
            font=(FONT_FAMILY, 10), text_color="gray50",
        ).pack(anchor="e")
        self.provider_value = ctk.CTkLabel(
            provider_frame, text=model_name,
            font=(FONT_FAMILY, 14, "bold"),
        )
        self.provider_value.pack(anchor="e")

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        mode = "dark" if self._is_dark else "light"
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(text="\U0001f319" if self._is_dark else "\u2600\ufe0f")

    # -- Drop Zone ------------------------------------------------------

    def _create_drop_zone(self):
        self.drop_zone = DropZone(self.main_frame, on_files_dropped=self.add_files)
        self.drop_zone.pack(fill="x", pady=(0, 12))

    # -- File List ------------------------------------------------------

    def _create_file_list(self):
        list_header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        list_header.pack(fill="x")

        self.file_count_label = ctk.CTkLabel(
            list_header,
            text="\U0001f4cb \ud30c\uc77c \ubaa9\ub85d (0\uac1c)",
            font=(FONT_FAMILY, 13, "bold"),
        )
        self.file_count_label.pack(side="left", padx=4)

        # Scrollable file list
        self.file_list_frame = ctk.CTkScrollableFrame(
            self.main_frame, height=160, corner_radius=8,
        )
        self.file_list_frame.pack(fill="both", expand=True, pady=(4, 12))
        self.file_list_frame.grid_columnconfigure(0, weight=1)

        # Right-click context menu (using tk.Menu - CTk has no native menu)
        import tkinter as tk
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label="\uc120\ud0dd \ud56d\ubaa9 \uc81c\uac70",
            command=self.remove_selected_files,
        )
        self.context_menu.add_command(
            label="\ubaa8\ub4e0 \ud56d\ubaa9 \uc81c\uac70",
            command=self.clear_all_files,
        )

    # -- Controls -------------------------------------------------------

    def _create_controls(self):
        ctrl = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 12))

        left = ctk.CTkFrame(ctrl, fg_color="transparent")
        left.pack(side="left")

        self.start_button = ctk.CTkButton(
            left, text="\u25b6  \ucc98\ub9ac \uc2dc\uc791",
            font=(FONT_FAMILY, 13, "bold"), height=38, width=140,
            command=self.start_processing,
        )
        self.start_button.pack(side="left", padx=(0, 8))

        self.stop_button = ctk.CTkButton(
            left, text="\u23f9  \uc911\uc9c0",
            font=(FONT_FAMILY, 13), height=38, width=100,
            fg_color="#D9534F", hover_color="#C9302C",
            state="disabled",
            command=self.stop_processing,
        )
        self.stop_button.pack(side="left")

        right = ctk.CTkFrame(ctrl, fg_color="transparent")
        right.pack(side="right")

        self.folder_button = ctk.CTkButton(
            right, text="\U0001f4c1 \uacb0\uacfc \ud3f4\ub354",
            font=(FONT_FAMILY, 12), height=38, width=130,
            fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray90"),
            command=self.open_output_folder,
        )
        self.folder_button.pack(side="left", padx=(0, 8))

        self.settings_button = ctk.CTkButton(
            right, text="\u2699 \uc124\uc815",
            font=(FONT_FAMILY, 12), height=38, width=80,
            fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray90"),
            command=self.open_settings,
        )
        self.settings_button.pack(side="left")

    # -- Progress -------------------------------------------------------

    def _create_progress_section(self):
        pf = ctk.CTkFrame(self.main_frame, corner_radius=8)
        pf.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(pf, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        self.current_file_label = ctk.CTkLabel(
            inner,
            text="\u23f3 \ub300\uae30 \uc911...",
            font=(FONT_FAMILY, 12),
        )
        self.current_file_label.pack(anchor="w", pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(inner, height=14, corner_radius=7)
        self.progress_bar.pack(fill="x", pady=(0, 6))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            inner,
            text="0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc",
            font=(FONT_FAMILY, 11), text_color="gray50",
        )
        self.progress_label.pack(anchor="w")

    # -- Log Panel ------------------------------------------------------

    def _create_log_panel(self):
        self.log_panel = LogPanel(self.main_frame)
        self.log_panel.pack(fill="x", pady=(0, 8))

    # -- Status Bar -----------------------------------------------------

    def _create_status_bar(self):
        bar = ctk.CTkFrame(self.root, height=32, corner_radius=0)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            bar, text="\u2705 \uc900\ube44\ub428",
            font=(FONT_FAMILY, 11),
        )
        self.status_label.pack(side="left", padx=12)

        ctk.CTkLabel(
            bar, text="v2.1",
            font=(FONT_FAMILY, 10, "bold"), text_color="gray50",
        ).pack(side="left", padx=(0, 12))

        config = ConfigManager()
        provider = config.get_provider()
        model_text = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"
        self.model_status_label = ctk.CTkLabel(
            bar, text=model_text,
            font=(FONT_FAMILY, 10), text_color="gray50",
        )
        self.model_status_label.pack(side="left")

        self.time_label = ctk.CTkLabel(
            bar, text="", font=(FONT_FAMILY, 10), text_color="gray50",
        )
        self.time_label.pack(side="right", padx=12)
        self._update_time()

    def _update_time(self):
        self.time_label.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._update_time)

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def add_files(self, files):
        added = 0
        for f in files:
            if f not in self.pdf_files:
                self.pdf_files.append(f)
                self.file_status[f] = "waiting"
                card = FileCard(
                    self.file_list_frame,
                    filename=os.path.basename(f),
                    status="waiting",
                )
                card.pack(fill="x", pady=2)
                card.bind("<Button-3>", lambda e, fp=f: self._show_context_menu(e, fp))
                self.file_cards[f] = card
                added += 1

        self._update_file_count()
        if added > 0:
            self.status_label.configure(text=f"\u2705 {added}\uac1c \ud30c\uc77c \ucd94\uac00\ub428")

    def _show_context_menu(self, event, file_path):
        self._selected_file_for_menu = file_path
        self.context_menu.post(event.x_root, event.y_root)

    def remove_selected_files(self):
        fp = getattr(self, "_selected_file_for_menu", None)
        if fp and fp in self.pdf_files:
            self._remove_file(fp)

    def clear_all_files(self):
        for fp in list(self.pdf_files):
            self._remove_file(fp)
        if not self.is_processing:
            self._reset_progress()

    def _remove_file(self, file_path):
        if file_path in self.file_cards:
            self.file_cards[file_path].destroy()
            del self.file_cards[file_path]
        if file_path in self.file_status:
            del self.file_status[file_path]
        if file_path in self.pdf_files:
            self.pdf_files.remove(file_path)
        self._update_file_count()

    def _update_file_count(self):
        count = len(self.pdf_files)
        self.file_count_label.configure(
            text=f"\U0001f4cb \ud30c\uc77c \ubaa9\ub85d ({count}\uac1c)"
        )
        state = "normal" if count > 0 else "disabled"
        self.start_button.configure(state=state)

    def update_file_status(self, file_path, status, detail=""):
        if file_path in self.file_cards:
            self.file_cards[file_path].set_status(status, detail)
        if file_path in self.file_status:
            self.file_status[file_path] = status

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def start_processing(self):
        if not self.pdf_files:
            messagebox.showwarning("\u26a0\ufe0f \uacbd\uace0", "\ucc98\ub9ac\ud560 PDF \ud30c\uc77c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
            return

        self.is_processing = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.processed_files.clear()

        self.progress_bar.set(0)
        self.progress_label.configure(text="0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc")
        self.current_file_label.configure(text="\U0001f680 \ucc98\ub9ac \uc2dc\uc791 \uc911...")
        self.status_label.configure(text="\U0001f504 \ucc98\ub9ac \uc911...")
        self.log_panel.append_log(f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc2dc\uc791")

        self.current_thread = threading.Thread(target=self.process_files, daemon=True)
        self.current_thread.start()
        self.check_queue()

    def stop_processing(self):
        self.is_processing = False
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="\u26d4 \ucc98\ub9ac \uc911\uc9c0\ub428")
        self.current_file_label.configure(text="\u23f9\ufe0f \uc911\uc9c0\ub428")
        self.log_panel.append_log(f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc911\uc9c0")

    def process_files(self):
        """Background thread - processes PDF files through AI pipeline."""
        from core.pdf_processor import PDFProcessor
        from core.claude_processor import ClaudeProcessor
        from core.openai_processor import OpenAIProcessor
        from core.csv_generator import CSVGenerator
        from core.config import load_config
        import shutil
        import logging

        log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(
            logs_dir, f"spine_survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_formatter)

        loggers = [
            logging.getLogger("PDFProcessor"),
            logging.getLogger("ClaudeProcessor"),
            logging.getLogger("CSVGenerator"),
            logging.getLogger(),
        ]
        for logger in loggers:
            logger.setLevel(logging.INFO)
            logger.addHandler(file_handler)

        try:
            config_manager = load_config()
            api_key = config_manager.get_api_key()
            folders = config_manager.get_folders()

            output_folder = folders["output_folder"]
            os.makedirs(output_folder, exist_ok=True)

            logging.info(f"\ucc98\ub9ac \uc2dc\uc791 - \ucd1d {len(self.pdf_files)}\uac1c \ud30c\uc77c")

            all_survey_data = []
            total_pages = 0
            file_page_counts = []

            for pdf_path in self.pdf_files:
                try:
                    pdf_processor = PDFProcessor(pdf_path, folders["temp_folder"])
                    page_count = pdf_processor.get_page_count()
                    file_page_counts.append((pdf_path, page_count))
                    total_pages += page_count
                except Exception:
                    file_page_counts.append((pdf_path, 0))

            processed_pages = 0

            def progress_callback(page_idx, total_pages_in_file):
                nonlocal processed_pages
                processed_pages += 1
                progress_percent = (processed_pages / total_pages) * 100
                self.result_queue.put({
                    "type": "page_progress",
                    "current_page": processed_pages,
                    "total_pages": total_pages,
                    "progress_percent": progress_percent,
                    "current_file": os.path.basename(pdf_path),
                    "page_in_file": page_idx + 1,
                    "pages_in_current_file": total_pages_in_file,
                })

            for idx, (pdf_path, page_count) in enumerate(file_page_counts):
                if not self.is_processing:
                    break

                self.result_queue.put({
                    "type": "file_start",
                    "current_file": os.path.basename(pdf_path),
                    "file_path": pdf_path,
                    "file_idx": idx + 1,
                    "total_files": len(self.pdf_files),
                })

                try:
                    logging.info(f"\ud30c\uc77c \ucc98\ub9ac \uc2dc\uc791: {os.path.basename(pdf_path)}")

                    pdf_processor = PDFProcessor(pdf_path, folders["temp_folder"])
                    processed_images = pdf_processor.process_pdf()
                    logging.info(f"PDF \ubcc0\ud658 \uc644\ub8cc: {len(processed_images)}\uac1c \ud398\uc774\uc9c0")

                    provider = config_manager.get_provider()
                    if provider == "openai":
                        ai_processor = OpenAIProcessor(api_key)
                        logging.info(f"OpenAI \ud504\ub85c\uc138\uc11c \uc0ac\uc6a9: {config_manager.get_model()}")
                    else:
                        ai_processor = ClaudeProcessor(api_key)
                        logging.info(f"Claude \ud504\ub85c\uc138\uc11c \uc0ac\uc6a9: {config_manager.get_model()}")

                    self.result_queue.put({
                        "type": "api_start",
                        "current_file": os.path.basename(pdf_path),
                        "pages_to_process": len(processed_images),
                    })

                    survey_data = ai_processor.process_images(
                        processed_images, progress_callback=progress_callback
                    )

                    if survey_data:
                        all_survey_data.extend(survey_data)
                        self.processed_files.add(pdf_path)
                        logging.info(
                            f"\ud30c\uc77c \ucc98\ub9ac \uc644\ub8cc: {os.path.basename(pdf_path)} "
                            f"- {len(survey_data)}\uac1c \ub370\uc774\ud130 \ucd94\ucd9c"
                        )
                        self.result_queue.put({
                            "type": "remove_file",
                            "file_path": pdf_path,
                            "file_index": idx,
                        })

                except Exception as e:
                    error_msg = f"\uc624\ub958 \ubc1c\uc0dd ({os.path.basename(pdf_path)}): {str(e)}"
                    logging.error(error_msg, exc_info=True)
                    self.result_queue.put({"type": "error", "message": error_msg})

                finally:
                    if os.path.exists(folders["temp_folder"]):
                        try:
                            shutil.rmtree(folders["temp_folder"])
                            os.makedirs(folders["temp_folder"])
                        except PermissionError:
                            logging.warning(f"\uc784\uc2dc \ud3f4\ub354 \uc0ad\uc81c \uc2e4\ud328: {folders['temp_folder']}")
                            try:
                                for file in os.listdir(folders["temp_folder"]):
                                    fp = os.path.join(folders["temp_folder"], file)
                                    if os.path.isfile(fp):
                                        try:
                                            os.remove(fp)
                                        except Exception:
                                            pass
                            except Exception as e2:
                                logging.warning(f"\uc784\uc2dc \ud30c\uc77c \uc815\ub9ac \uc2e4\ud328: {str(e2)}")

            # CSV generation
            if all_survey_data and self.is_processing:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_config = config_manager.get_output_config()
                filename = f"{timestamp}_{output_config['csv_filename']}"

                output_dir = os.path.join(base_dir, "output_csv")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)

                csv_generator = CSVGenerator(output_path)
                df = csv_generator.generate_csv(all_survey_data)

                if df is not None:
                    logging.info(f"CSV \ud30c\uc77c \uc0dd\uc131 \uc644\ub8cc: {output_path}")
                    logging.info(f"\ucd1d {len(self.processed_files)}\uac1c \ud30c\uc77c \ucc98\ub9ac \uc644\ub8cc")
                    self.result_queue.put({
                        "type": "complete",
                        "output_file": output_path,
                        "processed_count": len(self.processed_files),
                    })

        except Exception as e:
            logging.error(f"\uce58\uba85\uc801 \uc624\ub958 \ubc1c\uc0dd: {str(e)}", exc_info=True)
            self.result_queue.put({"type": "error", "message": f"\uce58\uba85\uc801 \uc624\ub958: {str(e)}"})

        finally:
            self.is_processing = False
            for logger in loggers:
                logger.removeHandler(file_handler)
            file_handler.close()
            logging.info(f"\ub85c\uadf8 \ud30c\uc77c \uc800\uc7a5\ub428: {log_file}")

    # ------------------------------------------------------------------
    # Queue polling
    # ------------------------------------------------------------------

    def check_queue(self):
        try:
            while True:
                item = self.result_queue.get_nowait()

                if item["type"] == "file_start":
                    fp = item.get("file_path")
                    if fp:
                        self.update_file_status(fp, "processing")
                    self.current_file_label.configure(
                        text=f"\U0001f504 PDF \ubcc0\ud658 \uc911: {item['current_file']} "
                             f"({item['file_idx']}/{item['total_files']} \ud30c\uc77c)"
                    )
                    self.log_panel.append_log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] \ud30c\uc77c \uc2dc\uc791: {item['current_file']}"
                    )

                elif item["type"] == "api_start":
                    self.current_file_label.configure(
                        text=f"\U0001f916 AI \ucc98\ub9ac \uc911: {item['current_file']} "
                             f"({item['pages_to_process']}\ud398\uc774\uc9c0)"
                    )

                elif item["type"] == "page_progress":
                    pct = item["progress_percent"]
                    self.progress_bar.set(pct / 100.0)
                    self.current_file_label.configure(
                        text=f"\U0001f916 AI \ucc98\ub9ac \uc911: {item['current_file']} - "
                             f"{item['page_in_file']}/{item['pages_in_current_file']} \ud398\uc774\uc9c0"
                    )
                    self.progress_label.configure(
                        text=f"{item['current_page']} / {item['total_pages']} "
                             f"\ud398\uc774\uc9c0 \uc644\ub8cc ({pct:.1f}%)"
                    )

                elif item["type"] == "remove_file":
                    fp = item["file_path"]
                    if fp in self.pdf_files:
                        self.update_file_status(fp, "complete")
                        self.root.update()
                        self._remove_file(fp)
                        self.status_label.configure(
                            text=f"\u2705 \uc644\ub8cc: {os.path.basename(fp)}"
                        )
                        self.log_panel.append_log(
                            f"[{datetime.now().strftime('%H:%M:%S')}] \uc644\ub8cc: {os.path.basename(fp)}"
                        )

                elif item["type"] == "error":
                    messagebox.showerror("\uc624\ub958", item["message"])
                    self.log_panel.append_log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {item['message']}"
                    )

                elif item["type"] == "complete":
                    self._complete_processing(item["output_file"], item["processed_count"])
                    return

        except queue.Empty:
            pass

        if self.is_processing:
            self.root.after(100, self.check_queue)

    # ------------------------------------------------------------------
    # Processing completion
    # ------------------------------------------------------------------

    def _complete_processing(self, output_file, processed_count):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.current_file_label.configure(text="\U0001f389 \ucc98\ub9ac \uc644\ub8cc!")
        self.status_label.configure(text=f"\u2705 \uc644\ub8cc: {processed_count}\uac1c \ud30c\uc77c \ucc98\ub9ac\ub428")
        self.log_panel.append_log(
            f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc644\ub8cc: {processed_count}\uac1c \ud30c\uc77c"
        )

        response = messagebox.askyesno(
            "\U0001f389 \ucc98\ub9ac \uc644\ub8cc",
            f"{processed_count}\uac1c \ud30c\uc77c\uc774 \uc131\uacf5\uc801\uc73c\ub85c \ucc98\ub9ac\ub418\uc5c8\uc2b5\ub2c8\ub2e4.\n"
            f"\uacb0\uacfc \ud30c\uc77c\uc744 \uc5f4\uc5b4\ubcf4\uc2dc\uaca0\uc2b5\ub2c8\uae4c?",
        )
        if response:
            if os.name == "nt":
                os.startfile(output_file)
            else:
                os.system(f'open "{output_file}"')

        self.processed_files.clear()
        self.pdf_files.clear()
        self.file_status.clear()
        for card in self.file_cards.values():
            card.destroy()
        self.file_cards.clear()
        self._update_file_count()

        self.root.after(2000, self._reset_progress)

    def _reset_progress(self):
        self.progress_bar.set(0)
        self.progress_label.configure(text="0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc")
        self.current_file_label.configure(text="\u23f3 \ub300\uae30 \uc911...")
        self.status_label.configure(text="\u2705 \uc900\ube44\ub428")

    # ------------------------------------------------------------------
    # Settings / Folder
    # ------------------------------------------------------------------

    def open_output_folder(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        output_folder = os.path.join(base_dir, "output_csv")
        os.makedirs(output_folder, exist_ok=True)

        if os.name == "nt":
            os.startfile(output_folder)
        elif sys.platform == "darwin":
            os.system(f'open "{output_folder}"')
        else:
            os.system(f'xdg-open "{output_folder}"')

    def open_settings(self):
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.root)
        self.root.wait_window(dialog.dialog)
        self._update_provider_display()

    def _update_provider_display(self):
        config = ConfigManager()
        provider = config.get_provider()
        model_name = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"
        self.provider_value.configure(text=model_name)
        self.model_status_label.configure(text=model_name)

    # ------------------------------------------------------------------
    # Window helpers
    # ------------------------------------------------------------------

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def run(self):
        self.root.mainloop()
