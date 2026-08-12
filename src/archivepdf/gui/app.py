"""The application window: layout, navigation and shared state.

Each tab lives in its own module as a mixin. The window composes them, which
keeps this file about *the shell* -- header, navigation, footer -- and leaves
each tab's widgets next to the code that drives them.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from ..core.compression import Recommendation
from ..core.resources import current_usage
from ..core.rotation import PdfRotationSession
from ..paths import resource_path
from .assets import load_logo_with_transparency
from .tabs.converter import ConverterTabMixin
from .tabs.optimizer import OptimizerTabMixin
from .tabs.rotate import RotateTabMixin
from .theme import (
    APPEARANCE_MODE,
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_WIDTH,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_RED,
    COLOR_BG_HOVER,
    COLOR_BG_PANEL,
    COLOR_BG_PANEL_ALT,
    COLOR_BG_PRIMARY,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_NAV_ACTIVE,
    COLOR_NAV_BG,
    COLOR_NAV_HOVER,
    COLOR_NAV_TEXT_ACTIVE,
    COLOR_NAV_TEXT_INACTIVE,
    COLOR_TEXT_FAINT,
    COLOR_TEXT_PRIMARY,
    DEFAULT_COLOR_THEME,
    ICON_PATH,
    LOGO_DISPLAY_HEIGHT,
    LOGO_PATH,
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    RESIZE_DEBOUNCE_MS,
    SCALE_CHANGE_THRESHOLD,
    SYSTEM_INFO_REFRESH_MS,
    WINDOW_TITLE,
)

logger = logging.getLogger(__name__)

ctk.set_appearance_mode(APPEARANCE_MODE)
ctk.set_default_color_theme(DEFAULT_COLOR_THEME)

TAB_NAMES = ["Convertidor", "Optimitzador", "Rotar"]


class App(ctk.CTk, ConverterTabMixin, OptimizerTabMixin, RotateTabMixin):
    """Main window. Behaviour for each tab comes from its mixin."""

    def __init__(self):
        super().__init__()

        # Configuració bàsica i mida mínima garantida per a tots els elements
        self.title(WINDOW_TITLE)
        self.geometry(f"{BASE_WINDOW_WIDTH}x{BASE_WINDOW_HEIGHT}")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.configure(fg_color=COLOR_BG_PRIMARY)

        # Escalat responsiu: la interfície s'ajusta a la mida de la finestra
        # entre un mínim i un màxim, perquè cap contingut quedi tallat en
        # finestres petites ni desproporcionadament gran en finestres grans.
        self._current_ui_scale = 1.0
        self._resize_after_id = None
        self.bind("<Configure>", self._on_root_configure)

        # Variables Tab Convertidor
        self.carpeta_var = ctk.StringVar()
        self.resolucio_var = ctk.StringVar(value="Alta")

        # Variables Tab Optimitzador
        self.opt_carpeta_var = ctk.StringVar()
        self.opt_dpi_var = ctk.StringVar(value="150")
        self.opt_quality_var = ctk.StringVar(value="Mitjana (65%)")
        self.opt_scale_var = ctk.StringVar(value="100%")
        self._last_recommendation: Recommendation | None = None

        # Variables Tab Rotar
        self.rotar_carpeta_var = ctk.StringVar()
        self.active_tab = "Convertidor"
        self.rotation_session: PdfRotationSession | None = None
        self.gradient_img = None
        self.icon_ctk = None
        self.rotar_photo = None

        self.set_app_icon()
        self.crear_ui()

        # Cap document obert ha de quedar bloquejat en tancar la finestra.
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self) -> None:
        """Allibera el PDF obert al rotador abans de tancar."""
        if self.rotation_session is not None:
            self.rotation_session.close()
            self.rotation_session = None
        self.destroy()

    def set_app_icon(self):
        """Estableix la icona de la finestra, cercant-la sempre a la carpeta
        on es troba aquest fitxer .py (o la carpeta de l'executable si està
        empaquetat amb PyInstaller), independentment del directori de
        treball des d'on s'hagi llançat el programa."""
        try:
            icon = resource_path(ICON_PATH)
            if icon.exists():
                self.iconbitmap(str(icon))
        except Exception:
            pass

    def _on_root_configure(self, event):
        """Cada cop que la finestra canvia de mida, reprograma (amb debounce)
        el recàlcul de l'escalat de la interfície."""
        if event.widget is not self:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(RESIZE_DEBOUNCE_MS, self._aplicar_escalat_finestra)

    def _aplicar_escalat_finestra(self):
        """Calcula un factor d'escala en funció de la mida actual de la
        finestra respecte a la mida de referència, limitat entre
        MIN_UI_SCALE i MAX_UI_SCALE, i l'aplica a tota la interfície."""
        self._resize_after_id = None
        ample = self.winfo_width()
        alt = self.winfo_height()
        if ample < 50 or alt < 50:
            return

        factor = min(ample / BASE_WINDOW_WIDTH, alt / BASE_WINDOW_HEIGHT)
        factor = max(MIN_UI_SCALE, min(MAX_UI_SCALE, factor))

        if abs(factor - self._current_ui_scale) < SCALE_CHANGE_THRESHOLD:
            return

        self._current_ui_scale = factor
        try:
            ctk.set_widget_scaling(factor)
        except Exception:
            pass


    def crear_ui(self):
        """Crea la interfície completa"""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        main_container = ctk.CTkFrame(self, fg_color=COLOR_BG_PRIMARY)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Barra superior unificada: logo (meitat esquerra) + navegació
        # (centrada a la meitat dreta) + Ajuda (extrem dret)
        self.crear_header(main_container)
        
        # Contenidor de contingut de pestanya
        self.tab_content_frame = ctk.CTkFrame(
            main_container,
            fg_color="transparent"
        )
        self.tab_content_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.tab_content_frame.grid_rowconfigure(0, weight=1)
        self.tab_content_frame.grid_columnconfigure(0, weight=1)
        
        # Crear frames per a cada pestanya
        self.tab_convertidor = ctk.CTkFrame(self.tab_content_frame, fg_color="transparent")
        self.tab_optimitzador = ctk.CTkFrame(self.tab_content_frame, fg_color="transparent")
        self.tab_rotar = ctk.CTkFrame(self.tab_content_frame, fg_color="transparent")
        
        # Configurar pestanyes
        self.setup_tab_convertidor()
        self.setup_tab_optimitzador()
        self.setup_tab_rotar()
        
        # Mostrar pestanya activa
        self.mostrar_tab("Convertidor")
        
        # Footer
        self.crear_footer(main_container)
    
    def crear_header(self, parent):
        """Barra superior única: el logo ocupa la meitat esquerra, la
        navegació per pestanyes queda centrada dins la meitat dreta, i el
        botó d'Ajuda es manté discret a l'extrem dret. Tot en una mateixa
        franja perquè es llegeixi com un sol capçal professional, no com
        dues barres apilades i descoordinades."""
        header_frame = ctk.CTkFrame(parent, height=178, fg_color=COLOR_BG_PRIMARY)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_propagate(False)

        header_line = ctk.CTkFrame(header_frame, height=1, fg_color=COLOR_BORDER)
        header_line.place(relx=0, rely=1.0, relwidth=1, anchor="sw")
        
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.grid(row=0, column=0, sticky="nsew", padx=32, pady=2)
        header_content.grid_columnconfigure(0, weight=1)   # meitat esquerra -> logo
        header_content.grid_columnconfigure(1, weight=1)   # meitat dreta -> navegació
        header_content.grid_columnconfigure(2, weight=0)   # extrem -> Ajuda
        header_content.grid_rowconfigure(0, weight=1)

        # --- Logo (meitat esquerra) ------------------------------------
        # S'elimina el fons pla de la imatge original perquè s'integri amb
        # el fons de l'aplicació sense mostrar cap requadre ni vora.
        try:
            logo_file = resource_path(LOGO_PATH)
            if not logo_file.exists():
                logo_file = Path(LOGO_PATH)
            logo_image = load_logo_with_transparency(logo_file)
            orig_w, orig_h = logo_image.size
            escala = LOGO_DISPLAY_HEIGHT / orig_h
            logo_w = max(1, round(orig_w * escala))
            self.logo_ctk = ctk.CTkImage(
                light_image=logo_image,
                dark_image=logo_image,
                size=(logo_w, LOGO_DISPLAY_HEIGHT)
            )
            logo_label = ctk.CTkLabel(header_content, image=self.logo_ctk, text="")
            logo_label.grid(row=0, column=0, sticky="w")
        except Exception:
            fallback_label = ctk.CTkLabel(
                header_content,
                text="MultiPDF Professional",
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY
            )
            fallback_label.grid(row=0, column=0, sticky="w")

        # --- Navegació (centrada a la meitat dreta) ---------------------
        nav_capsule = ctk.CTkFrame(
            header_content,
            fg_color=COLOR_NAV_BG,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        nav_capsule.grid(row=0, column=1)

        self.nav_segmented = ctk.CTkSegmentedButton(
            nav_capsule,
            values=TAB_NAMES,
            command=self.on_nav_click,
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_NAV_BG,
            selected_color=COLOR_NAV_ACTIVE,
            selected_hover_color=COLOR_NAV_ACTIVE,
            unselected_color=COLOR_NAV_BG,
            unselected_hover_color=COLOR_NAV_HOVER,
            text_color=COLOR_NAV_TEXT_ACTIVE,
            text_color_disabled=COLOR_NAV_TEXT_INACTIVE,
            corner_radius=8,
            border_width=0
        )
        self.nav_segmented.grid(row=0, column=0, padx=4, pady=4)
        self.nav_segmented.set("Convertidor")
        self._estilitzar_segmented_text(
            self.nav_segmented, COLOR_NAV_TEXT_ACTIVE, COLOR_NAV_TEXT_INACTIVE, "Convertidor"
        )

        # --- Ajuda (extrem dret) -----------------------------------------
        info_btn = ctk.CTkButton(
            header_content,
            text="Ajuda",
            width=90,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_BG_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_STRONG,
            command=self.mostrar_ajuda
        )
        info_btn.grid(row=0, column=2, sticky="e", padx=(24, 0))

    def _estilitzar_segmented_text(self, segmented, color_actiu, color_inactiu, valor_actiu):
        """Aplica color de text diferenciat a cada segment perquè l'opció
        seleccionada destaqui i la resta quedin clarament en segon pla,
        sense necessitat de contorns que semblin botons apagats."""
        try:
            for valor, boto in segmented._buttons_dict.items():
                boto.configure(text_color=color_actiu if valor == valor_actiu else color_inactiu)
        except Exception:
            pass
    
    def on_nav_click(self, tab_name):
        self._estilitzar_segmented_text(
            self.nav_segmented, COLOR_NAV_TEXT_ACTIVE, COLOR_NAV_TEXT_INACTIVE, tab_name
        )
        if tab_name == self.active_tab:
            return
        self.active_tab = tab_name
        self.mostrar_tab(tab_name)
    
    def mostrar_tab(self, tab_name):
        self.tab_convertidor.grid_forget()
        self.tab_optimitzador.grid_forget()
        self.tab_rotar.grid_forget()
        
        target = getattr(self, f"tab_{tab_name.lower()}")
        target.grid(row=0, column=0, sticky="nsew")


    def crear_footer(self, parent):
        footer = ctk.CTkFrame(
            parent,
            height=40,
            fg_color=COLOR_BG_PANEL,
            border_width=0,
            corner_radius=0
        )
        footer.grid(row=3, column=0, sticky="ew", padx=0, pady=0)
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_propagate(False)

        footer_top_line = ctk.CTkFrame(footer, height=1, fg_color=COLOR_BORDER)
        footer_top_line.place(relx=0, rely=0, relwidth=1)
        
        footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
        footer_inner.grid(row=0, column=0, sticky="ew", padx=24)
        footer_inner.grid_columnconfigure(0, weight=1)
        
        footer_text = ctk.CTkLabel(
            footer_inner,
            text="Josep Pol i Font © 2026",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_FAINT
        )
        footer_text.grid(row=0, column=0, sticky="w", pady=10)

        # Indicador d'estat del sistema: un punt discret en lloc de xifres
        # cridaneres, per no alarmar l'usuari amb el consum real de RAM/CPU.
        system_frame = ctk.CTkFrame(footer_inner, fg_color="transparent")
        system_frame.grid(row=0, column=1, sticky="e", pady=10)

        self.system_dot = ctk.CTkLabel(
            system_frame,
            text="●",
            font=ctk.CTkFont(size=9),
            text_color=COLOR_ACCENT_GREEN,
            width=12
        )
        self.system_dot.pack(side="left", padx=(0, 6))

        self.system_label = ctk.CTkLabel(
            system_frame,
            text="CPU 0% · RAM 0%",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_FAINT
        )
        self.system_label.pack(side="left")
        
        self.actualizar_system_info()
    
    def actualizar_system_info(self):
        """Refresca l'indicador de CPU/RAM del peu de pàgina."""
        try:
            usage = current_usage()
            self.system_label.configure(
                text=f"CPU: {usage.cpu_percent:.0f}% | RAM: {usage.ram_percent:.0f}%"
            )
            self.system_dot.configure(
                text_color=COLOR_ACCENT_RED if usage.is_saturated else COLOR_ACCENT_GREEN
            )
        except Exception as exc:
            logger.debug("No se pudo leer el uso del sistema: %s", exc)
        self.after(SYSTEM_INFO_REFRESH_MS, self.actualizar_system_info)


    def mostrar_ajuda(self):
        ajuda_text = """
GESTOR PROFESSIONAL DE DOCUMENTS PDF v4.2

📋 FUNCIONALITATS:

CONVERTIDOR
  • Converteix imatges a PDFs
  • Suporta múltiples formats (JPG, PNG, BMP, etc.)
  • Dos modes de resolució: Alta o Usuari (50%)
  • Afegeix marcadors automàticament
  • Suporta estructura R/V

🗜️ OPTIMITZADOR (Imatges → PDF Comprimit)
  • Crea PDFs optimitzats directament des d'imatges
  • Analitza el pes total i ofereix recomanació automàtica
  • Paràmetres personalitzables: DPI, Qualitat JPEG i Escala
  • Processament dinàmic per chunks i Safe Mode

ROTAR
  • Rota pàgines individuals
  • Opcions: -90°, 180°, +90°
  • Vista prèvia en temps real amb adaptació dinàmica
  • Botó de guardat permanentment visible i accessible
  • Preserva marcadors

© 2026 - Totes les funcionalitats integrades
        """
        messagebox.showinfo("Ajuda", ajuda_text)
