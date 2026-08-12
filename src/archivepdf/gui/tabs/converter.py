"""Tab 1 -- Convertidor: whole folder trees to standard PDF."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...config import ConversionConfig
from ...core.conversion import process_tree
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
    COLOR_SELECTOR_TRACK,
    COLOR_TEXT_FAINT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)

logger = logging.getLogger(__name__)


class ConverterTabMixin:
    """Widgets and behaviour of the standard conversion tab."""

    def setup_tab_convertidor(self):
        self.tab_convertidor.grid_rowconfigure(0, weight=1)
        self.tab_convertidor.grid_columnconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(
            self.tab_convertidor,
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
        
        folder_title = ctk.CTkLabel(
            main_panel,
            text="Selecció de carpeta",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        folder_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(22, 5))
        
        folder_desc = ctk.CTkLabel(
            main_panel,
            text="Selecciona la carpeta base amb imatges",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        folder_desc.grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 15))
        
        carpeta_frame = ctk.CTkFrame(main_panel, fg_color="transparent")
        carpeta_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 22))
        carpeta_frame.grid_columnconfigure(0, weight=1)
        
        self.carpeta_entry = ctk.CTkEntry(
            carpeta_frame,
            textvariable=self.carpeta_var,
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
        self.carpeta_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        sel_btn = ctk.CTkButton(
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
            command=self.triar_carpeta
        )
        sel_btn.grid(row=0, column=1)
        
        sep1 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep1.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24)
        
        res_label = ctk.CTkLabel(
            main_panel,
            text="Resolució de les imatges",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        res_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=24, pady=(22, 10))

        # Carril del selector: un únic fons continu perquè l'opció NO
        # seleccionada es vegi com a part del mateix control (no com un
        # botó separat "apagat" amb vora pròpia).
        res_track = ctk.CTkFrame(
            main_panel,
            fg_color=COLOR_SELECTOR_TRACK,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        res_track.grid(row=5, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 22))
        res_track.grid_columnconfigure(0, weight=1)

        self.resolucio_segmented = ctk.CTkSegmentedButton(
            res_track,
            values=["Alta resolució", "Usuari (50%)"],
            command=lambda v: self.canviar_resolucio_segmented(v),
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_SELECTOR_TRACK,
            selected_color=COLOR_ACCENT_BLUE,
            selected_hover_color=COLOR_ACCENT_BLUE_HOVER,
            unselected_color=COLOR_SELECTOR_TRACK,
            unselected_hover_color=COLOR_BG_HOVER,
            text_color=COLOR_TEXT_MUTED,
            corner_radius=8,
            border_width=0
        )
        self.resolucio_segmented.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.resolucio_segmented.set("Alta resolució")
        self._estilitzar_segmented_text(
            self.resolucio_segmented, "#ffffff", COLOR_TEXT_MUTED, "Alta resolució"
        )
        
        sep2 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep2.grid(row=6, column=0, columnspan=2, sticky="ew", padx=24)
        
        progress_label = ctk.CTkLabel(
            main_panel,
            text="Progrés",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        progress_label.grid(row=7, column=0, columnspan=2, sticky="w", padx=24, pady=(22, 10))
        
        self.progress = ctk.CTkProgressBar(
            main_panel,
            height=10,
            corner_radius=5,
            fg_color=COLOR_BG_PANEL_ALT,
            progress_color=COLOR_ACCENT_BLUE,
            border_width=1,
            border_color=COLOR_BORDER_STRONG
        )
        self.progress.grid(row=8, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 6))
        self.progress.set(0)
        
        self.status_label = ctk.CTkLabel(
            main_panel,
            text="Esperant accions...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.status_label.grid(row=9, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 22))
        
        sep3 = ctk.CTkFrame(main_panel, height=1, fg_color=COLOR_BORDER)
        sep3.grid(row=10, column=0, columnspan=2, sticky="ew", padx=24)
        
        start_btn = ctk.CTkButton(
            main_panel,
            text="Iniciar conversió",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_PRIMARY_HOVER,
            text_color="white",
            corner_radius=10,
            border_width=0,
            command=self.iniciar_conversion
        )
        start_btn.grid(row=11, column=0, columnspan=2, sticky="ew", padx=24, pady=(22, 26))

    # ── LÒGICA ───────────────────────────────────────────────────────

    def canviar_resolucio_segmented(self, value):
        self._estilitzar_segmented_text(
            self.resolucio_segmented, "#ffffff", COLOR_TEXT_MUTED, value
        )
        self.resolucio_var.set("Alta" if value == "Alta resolució" else "usuaris")

    def triar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta base")
        if carpeta:
            self.carpeta_var.set(carpeta)
            self.carpeta_entry.configure(state="normal")
            self.carpeta_entry.delete(0, "end")
            self.carpeta_entry.insert(0, carpeta)
            self.carpeta_entry.configure(state="readonly")

    def actualitzar_progress(self, actual, total):
        """Callback del nucli. S'executa al fil de treball, així que tota
        actualització de widgets es delega al fil de la interfície."""
        if total <= 0:
            return
        percent = actual / total
        self.after(0, lambda p=percent: self.progress.set(p))
        self.after(
            0,
            lambda a=actual, t=total: self.status_label.configure(
                text=f"Processant imatge {a}/{t}..."
            ),
        )

    def iniciar_conversion(self):
        ruta = Path(self.carpeta_var.get()).expanduser().resolve()
        if not ruta.exists() or not ruta.is_dir():
            messagebox.showerror("Error", "Has de triar una carpeta vàlida.")
            return

        self.status_label.configure(text="Iniciant conversió...")
        self.progress.set(0)

        config = ConversionConfig.standard(
            halve_resolution=self.resolucio_var.get() == "usuaris"
        )
        threading.Thread(
            target=self.convertir_thread,
            args=(ruta, config),
            daemon=True,
        ).start()

    def convertir_thread(self, ruta: Path, config: ConversionConfig):
        """Fil de treball: el nucli llança excepcions, la interfície decideix
        com informar-ne."""
        errors: list[str] = []
        try:
            process_tree(
                ruta,
                config,
                errors,
                progress_callback=self.actualitzar_progress,
            )
        except Exception as exc:
            logger.exception("Error fatal durante la conversión estándar")
            self.after(0, lambda e=exc: messagebox.showerror("Error fatal", str(e)))
            return

        if errors:
            self.after(
                0,
                lambda: self.status_label.configure(text="Procés acabat amb alguns errors."),
            )
            missatge = "No s'han pogut generar:\n\n" + "\n".join(errors)
            self.after(0, lambda m=missatge: messagebox.showwarning("Errors detectats", m))
        else:
            self.after(0, lambda: self.status_label.configure(text="Conversió completada."))
            self.after(
                0,
                lambda: messagebox.showinfo("Èxit", "Conversió finalitzada correctament."),
            )
