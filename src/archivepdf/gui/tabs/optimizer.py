"""Tab 2 -- Optimitzador: compressed PDFs with an automatic recommendation."""

from __future__ import annotations

import itertools
import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...config import DPI_OPTIONS, QUALITY_PRESETS, SCALE_OPTIONS, ConversionConfig
from ...core.compression import recommend_settings
from ...core.conversion import process_tree
from ...core.discovery import find_all_images, scan_folder
from ..theme import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_BLUE_HOVER,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_PRIMARY_HOVER,
    COLOR_BG_HOVER,
    COLOR_BG_PANEL,
    COLOR_BG_PANEL_ALT,
    COLOR_BG_PRIMARY,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_TEXT_FAINT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)

logger = logging.getLogger(__name__)


class OptimizerTabMixin:
    """Widgets and behaviour of the compression tab."""

    def setup_tab_optimitzador(self):
        self.tab_optimitzador.grid_rowconfigure(0, weight=1)
        self.tab_optimitzador.grid_columnconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(
            self.tab_optimitzador,
            fg_color=COLOR_BG_PRIMARY,
            corner_radius=0
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        main_panel = ctk.CTkFrame(
            scroll_frame,
            fg_color=COLOR_BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER
        )
        main_panel.pack(fill="x", pady=10)
        main_panel.grid_columnconfigure(1, weight=1)
        
        # --- Selecció de carpeta d'imatges ---
        folder_title = ctk.CTkLabel(
            main_panel,
            text="Selecció de carpeta (imatges)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        folder_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(18, 5))
        
        folder_desc = ctk.CTkLabel(
            main_panel,
            text="Selecciona carpeta amb imatges per generar un PDF optimitzat",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        folder_desc.grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 12))
        
        carpeta_frame = ctk.CTkFrame(main_panel, fg_color="transparent")
        carpeta_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))
        carpeta_frame.grid_columnconfigure(0, weight=1)
        
        self.opt_carpeta_entry = ctk.CTkEntry(
            carpeta_frame,
            textvariable=self.opt_carpeta_var,
            placeholder_text="Cap carpeta seleccionada",
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_BG_PANEL_ALT,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_FAINT,
            border_color=COLOR_BORDER_STRONG,
            border_width=1,
            corner_radius=8,
            state="readonly"
        )
        self.opt_carpeta_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        opt_sel_btn = ctk.CTkButton(
            carpeta_frame,
            text="Triar carpeta",
            width=140,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="white",
            corner_radius=8,
            border_width=0,
            command=self.triar_carpeta_opt
        )
        opt_sel_btn.grid(row=0, column=1)

        # --- Panell d'informació i recomanació ---
        info_frame = ctk.CTkFrame(
            main_panel,
            fg_color=COLOR_BG_PANEL_ALT,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        info_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))

        self.opt_info_label = ctk.CTkLabel(
            info_frame,
            text="Selecciona una carpeta per veure informació i recomanació.",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_PRIMARY,
            justify="left",
            anchor="w",
            wraplength=900
        )
        self.opt_info_label.pack(padx=16, pady=11, fill="x")

        rec_btn = ctk.CTkButton(
            main_panel,
            text="✨  Aplicar recomanació automàtica",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            hover_color=COLOR_BG_HOVER,
            text_color=COLOR_ACCENT_BLUE,
            border_width=1,
            border_color=COLOR_ACCENT_BLUE,
            corner_radius=8,
            command=self._aplicar_recomanacio
        )
        rec_btn.grid(row=4, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 16))

        sep1 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep1.grid(row=5, column=0, columnspan=2, sticky="ew", padx=24)

        # --- Paràmetres de compressió ---
        params_title = ctk.CTkLabel(
            main_panel,
            text="Paràmetres de compressió",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        params_title.grid(row=6, column=0, columnspan=2, sticky="w", padx=24, pady=(16, 10))

        params_grid = ctk.CTkFrame(main_panel, fg_color="transparent")
        params_grid.grid(row=7, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 16))

        # DPI
        ctk.CTkLabel(
            params_grid, text="PPP (DPI)",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED,
                     ).grid(row=0, column=0, padx=(0, 8), pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(
            params_grid, values=DPI_OPTIONS, variable=self.opt_dpi_var, width=110, height=34,
            fg_color=COLOR_BG_PANEL_ALT, button_color=COLOR_ACCENT_BLUE,
            button_hover_color=COLOR_ACCENT_BLUE_HOVER,
            dropdown_fg_color=COLOR_BG_PANEL_ALT, dropdown_text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8
        ).grid(row=1, column=0, padx=(0, 25), pady=(0, 5), sticky="w")

        # Qualitat
        ctk.CTkLabel(
            params_grid, text="Qualitat JPEG",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED,
                     ).grid(row=0, column=1, padx=(0, 8), pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(
            params_grid, values=list(QUALITY_PRESETS.keys()),
            variable=self.opt_quality_var, width=180, height=34,
            fg_color=COLOR_BG_PANEL_ALT, button_color=COLOR_ACCENT_BLUE,
            button_hover_color=COLOR_ACCENT_BLUE_HOVER,
            dropdown_fg_color=COLOR_BG_PANEL_ALT, dropdown_text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8
        ).grid(row=1, column=1, padx=(0, 25), pady=(0, 5), sticky="w")

        # Escala
        ctk.CTkLabel(
            params_grid, text="Escala imatge",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED,
                     ).grid(row=0, column=2, padx=(0, 8), pady=(0, 4), sticky="w")
        ctk.CTkOptionMenu(
            params_grid, values=SCALE_OPTIONS, variable=self.opt_scale_var, width=110, height=34,
            fg_color=COLOR_BG_PANEL_ALT, button_color=COLOR_ACCENT_BLUE,
            button_hover_color=COLOR_ACCENT_BLUE_HOVER,
            dropdown_fg_color=COLOR_BG_PANEL_ALT, dropdown_text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8
        ).grid(row=1, column=2, padx=0, pady=(0, 5), sticky="w")

        sep2 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep2.grid(row=8, column=0, columnspan=2, sticky="ew", padx=24)

        # --- Progrés ---
        progress_label = ctk.CTkLabel(
            main_panel,
            text="Progrés",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        progress_label.grid(row=9, column=0, columnspan=2, sticky="w", padx=24, pady=(16, 8))

        self.opt_progress = ctk.CTkProgressBar(
            main_panel,
            height=10,
            corner_radius=5,
            fg_color=COLOR_BG_PANEL_ALT,
            progress_color=COLOR_ACCENT_BLUE,
            border_width=1,
            border_color=COLOR_BORDER_STRONG
        )
        self.opt_progress.grid(row=10, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 6))
        self.opt_progress.set(0)

        self.opt_status = ctk.CTkLabel(
            main_panel,
            text="Esperant accions...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.opt_status.grid(row=11, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 16))

        sep3 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep3.grid(row=12, column=0, columnspan=2, sticky="ew", padx=24)

        # Botó inici
        opt_start_btn = ctk.CTkButton(
            main_panel,
            text="🗜️  Crear PDF Comprimit",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_PRIMARY_HOVER,
            text_color="white",
            corner_radius=10,
            border_width=0,
            command=self.iniciar_optimitzacio
        )
        opt_start_btn.grid(row=13, column=0, columnspan=2, sticky="ew", padx=24, pady=(16, 20))

    # ── LÒGICA ───────────────────────────────────────────────────────

    def triar_carpeta_opt(self):
        carpeta = filedialog.askdirectory(title="Selecciona carpeta amb imatges")
        if carpeta:
            self.opt_carpeta_var.set(carpeta)
            self.opt_carpeta_entry.configure(state="normal")
            self.opt_carpeta_entry.delete(0, "end")
            self.opt_carpeta_entry.insert(0, carpeta)
            self.opt_carpeta_entry.configure(state="readonly")
            self._analitzar_carpeta_opt(Path(carpeta))

    def _analitzar_carpeta_opt(self, ruta: Path) -> None:
        """Escaneja la carpeta en segon pla i mostra la recomanació."""
        self._last_recommendation = None
        self.opt_info_label.configure(text="⏳  Escanejant carpeta…")

        def _worker() -> None:
            try:
                stats = scan_folder(ruta)
                recommendation = recommend_settings(stats.total_mb, stats.image_count)
            except Exception as exc:
                logger.exception("Error escaneando %s", ruta)
                self.after(
                    0,
                    lambda e=exc: self.opt_info_label.configure(
                        text=f"⚠️  No s'ha pogut analitzar la carpeta: {e}"
                    ),
                )
                return

            self._last_recommendation = recommendation
            self.after(
                0,
                lambda r=recommendation: self.opt_info_label.configure(text=r.info),
            )

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_recomanacio(self) -> None:
        if self._last_recommendation is None:
            messagebox.showwarning("Atenció", "Primer selecciona una carpeta.")
            return
        self.opt_dpi_var.set(self._last_recommendation.dpi)
        self.opt_quality_var.set(self._last_recommendation.quality)
        self.opt_scale_var.set(self._last_recommendation.scale)

    def _llegir_parametres_opt(self) -> ConversionConfig:
        """Tradueix els controls de la interfície a un perfil de conversió."""
        try:
            dpi = int(self.opt_dpi_var.get())
        except ValueError:
            dpi = 150

        quality = QUALITY_PRESETS.get(self.opt_quality_var.get(), 65)

        try:
            scale = int(self.opt_scale_var.get().replace("%", ""))
        except ValueError:
            scale = 100

        return ConversionConfig.compressed(dpi=dpi, quality=quality, scale_percent=scale)

    def iniciar_optimitzacio(self):
        ruta = Path(self.opt_carpeta_var.get()).expanduser().resolve()
        if not ruta.is_dir():
            messagebox.showerror("Error", "Has d'escollir una carpeta vàlida.")
            return

        self.opt_progress.set(0)
        self.opt_status.configure(text="Iniciant PDF comprimit…")

        threading.Thread(
            target=self._pdf_comprimit_thread,
            args=(ruta, self._llegir_parametres_opt()),
            daemon=True,
        ).start()

    def _pdf_comprimit_thread(self, ruta: Path, config: ConversionConfig) -> None:
        errors: list[str] = []
        total_images = len(find_all_images(ruta))

        if total_images == 0:
            self.after(
                0,
                lambda: messagebox.showwarning(
                    "Atenció", "No s'han trobat imatges a la carpeta seleccionada."
                ),
            )
            return

        # El nucli informa del progrés per carpeta; aquí es converteix en un
        # percentatge global sobre totes les imatges de l'arbre.
        processed = itertools.count(1)

        def progress_cb(_actual: int, _folder_total: int) -> None:
            done = next(processed)
            percent = min(done / total_images, 1.0)
            self.after(0, lambda p=percent: self.opt_progress.set(p))
            self.after(
                0,
                lambda c=done, t=total_images: self.opt_status.configure(
                    text=f"Imatge {c} / {t}"
                ),
            )

        try:
            process_tree(ruta, config, errors, progress_callback=progress_cb)
        except Exception as exc:
            logger.exception("Error fatal durante la compresión")
            self.after(0, lambda e=exc: messagebox.showerror("Error fatal", str(e)))
            return

        self.after(0, lambda: self.opt_progress.set(1.0))

        if errors:
            self.after(
                0,
                lambda: self.opt_status.configure(text="⚠️  Procés acabat amb alguns errors."),
            )
            missatge = "No s'han pogut generar:\n\n" + "\n".join(errors)
            self.after(0, lambda m=missatge: messagebox.showwarning("Errors detectats", m))
        else:
            self.after(
                0,
                lambda: self.opt_status.configure(text="✅  PDFs comprimits creats correctament!"),
            )
            self.after(
                0,
                lambda: messagebox.showinfo("Èxit", "PDFs comprimits generats amb èxit."),
            )
