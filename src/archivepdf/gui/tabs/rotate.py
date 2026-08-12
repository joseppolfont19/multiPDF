"""Tab 3 -- Rotar: per-page rotation with a live preview."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from ...core.rotation import PdfRotationSession
from ...exceptions import MissingDependencyError
from ..theme import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_BLUE_HOVER,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_PRIMARY_HOVER,
    COLOR_ACCENT_RED,
    COLOR_ACCENT_RED_HOVER,
    COLOR_BG_HOVER,
    COLOR_BG_PANEL,
    COLOR_BG_PANEL_ALT,
    COLOR_BG_PRIMARY,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_PREVIEW_BG,
    COLOR_TEXT_FAINT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)

logger = logging.getLogger(__name__)

# Breathing room kept between the rendered page and the canvas edges.
CANVAS_PADDING = 40


class RotateTabMixin:
    """Widgets and behaviour of the rotation tab."""

    def setup_tab_rotar(self):
        self.tab_rotar.grid_rowconfigure(0, weight=1)
        self.tab_rotar.grid_columnconfigure(0, weight=1)
        
        rotar_main = ctk.CTkFrame(self.tab_rotar, fg_color=COLOR_BG_PRIMARY)
        rotar_main.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        rotar_main.grid_rowconfigure(0, weight=1)
        rotar_main.grid_columnconfigure(0, weight=0)  # Panel de controls amb ample fix/estable
        rotar_main.grid_columnconfigure(1, weight=1)  # Panell de previsualització flexible

        # Contenedor lateral de control
        control_panel = ctk.CTkFrame(
            rotar_main,
            width=360,
            fg_color=COLOR_BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER
        )
        control_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        control_panel.grid_propagate(False)
        control_panel.grid_columnconfigure(0, weight=1)
        
        # Estructura interna: controls superiors desplaçables (row 0) i
        # botó de guardar fix a baix (row 1), sempre visible.
        control_panel.grid_rowconfigure(0, weight=1)
        control_panel.grid_rowconfigure(1, weight=0)

        # 1. Contenidor superior desplazable per a opcions i navegació
        controls_scroll = ctk.CTkScrollableFrame(
            control_panel,
            fg_color="transparent",
            corner_radius=0
        )
        controls_scroll.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))
        controls_scroll.grid_columnconfigure(0, weight=1)

        # --- Opcions de Selecció ---
        sel_pdf_title = ctk.CTkLabel(
            controls_scroll,
            text="Seleccionar PDF",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        sel_pdf_title.pack(fill="x", padx=15, pady=(10, 5))
        
        self.rotar_file_label = ctk.CTkLabel(
            controls_scroll,
            text="Cap PDF seleccionat",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=300
        )
        self.rotar_file_label.pack(fill="x", padx=15, pady=(0, 10))
        
        rotar_sel_btn = ctk.CTkButton(
            controls_scroll,
            text="Obrir PDF",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="white",
            corner_radius=8,
            border_width=0,
            command=self.rotar_select_pdf
        )
        rotar_sel_btn.pack(fill="x", padx=15, pady=(0, 14))
        
        sep1 = ctk.CTkFrame(controls_scroll, height=1, fg_color=COLOR_BORDER)
        sep1.pack(fill="x", padx=15, pady=5)
        
        # --- Navegació ---
        nav_title = ctk.CTkLabel(
            controls_scroll,
            text="Navegació",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        nav_title.pack(fill="x", padx=15, pady=(10, 5))
        
        nav_btn_frame = ctk.CTkFrame(controls_scroll, fg_color="transparent")
        nav_btn_frame.pack(fill="x", padx=15, pady=(0, 8))
        nav_btn_frame.grid_columnconfigure((0, 1), weight=1, uniform="nav")
        
        self.rotar_prev_btn = ctk.CTkButton(
            nav_btn_frame,
            text="◄",
            width=40,
            height=36,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=self.rotar_prev_page
        )
        self.rotar_prev_btn.grid(row=0, column=0, padx=(0, 4))
        
        self.rotar_next_btn = ctk.CTkButton(
            nav_btn_frame,
            text="►",
            width=40,
            height=36,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=self.rotar_next_page
        )
        self.rotar_next_btn.grid(row=0, column=1, padx=(4, 0))
        
        page_input_frame = ctk.CTkFrame(controls_scroll, fg_color="transparent")
        page_input_frame.pack(fill="x", padx=15, pady=(0, 8))
        page_input_frame.grid_columnconfigure(0, weight=1)
        
        self.rotar_page_entry = ctk.CTkEntry(
            page_input_frame,
            placeholder_text="Pàgina",
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_BG_PANEL_ALT,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_MUTED,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            state="disabled"
        )
        self.rotar_page_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.rotar_page_entry.bind("<Return>", self.rotar_go_to_page)
        
        self.rotar_go_btn = ctk.CTkButton(
            page_input_frame,
            text="Ir",
            width=50,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=self.rotar_go_to_page
        )
        self.rotar_go_btn.grid(row=0, column=1)
        
        self.rotar_page_info = ctk.CTkLabel(
            controls_scroll,
            text="Pàgina 0 de 0",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.rotar_page_info.pack(fill="x", padx=15, pady=(0, 10))
        
        sep2 = ctk.CTkFrame(controls_scroll, height=1, fg_color=COLOR_BORDER)
        sep2.pack(fill="x", padx=15, pady=5)
        
        # --- Rotació ---
        rot_title = ctk.CTkLabel(
            controls_scroll,
            text="Rotació",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        rot_title.pack(fill="x", padx=15, pady=(10, 5))
        
        rotation_frame = ctk.CTkFrame(controls_scroll, fg_color="transparent")
        rotation_frame.pack(fill="x", padx=15, pady=(0, 8))
        rotation_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="rot")
        
        self.rotar_left_btn = ctk.CTkButton(
            rotation_frame,
            text="⟲ -90°",
            height=38,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_RED_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=lambda: self.rotar_rotate_page(-90)
        )
        self.rotar_left_btn.grid(row=0, column=0, padx=(0, 3))
        
        self.rotar_180_btn = ctk.CTkButton(
            rotation_frame,
            text="180°",
            height=38,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_RED_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=lambda: self.rotar_rotate_page(180)
        )
        self.rotar_180_btn.grid(row=0, column=1, padx=3)
        
        self.rotar_right_btn = ctk.CTkButton(
            rotation_frame,
            text="⟳ +90°",
            height=38,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_RED_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=lambda: self.rotar_rotate_page(90)
        )
        self.rotar_right_btn.grid(row=0, column=2, padx=(3, 0))
        
        self.rotar_rotation_label = ctk.CTkLabel(
            controls_scroll,
            text="Rotació: 0°",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.rotar_rotation_label.pack(fill="x", padx=15, pady=(0, 10))

        # 2. Contenidor inferior fix per al botó de Guardar (Sempre visible)
        save_panel = ctk.CTkFrame(control_panel, fg_color="transparent")
        save_panel.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 15))
        save_panel.grid_columnconfigure(0, weight=1)

        sep3 = ctk.CTkFrame(save_panel, height=1, fg_color=COLOR_BORDER)
        sep3.pack(fill="x", padx=0, pady=(0, 10))

        save_title = ctk.CTkLabel(
            save_panel,
            text="Guardar PDF",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        save_title.pack(fill="x", padx=0, pady=(0, 8))

        self.rotar_save_btn = ctk.CTkButton(
            save_panel,
            text="💾 Guardar PDF Modificat",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_BG_PANEL_ALT,
            hover_color=COLOR_ACCENT_PRIMARY_HOVER,
            text_color=COLOR_TEXT_FAINT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            state="disabled",
            command=self.rotar_save_pdf
        )
        self.rotar_save_btn.pack(fill="x", padx=0, pady=0)

        # --- Panell de Previsualització ---
        preview_panel = ctk.CTkFrame(
            rotar_main,
            fg_color=COLOR_BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER
        )
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.grid_rowconfigure(1, weight=1)
        preview_panel.grid_columnconfigure(0, weight=1)
        
        preview_title = ctk.CTkLabel(
            preview_panel,
            text="Previsualització",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        preview_title.pack(fill="x", padx=20, pady=(15, 10))
        
        canvas_container = ctk.CTkFrame(
            preview_panel,
            fg_color=COLOR_PREVIEW_BG,
            corner_radius=8
        )
        canvas_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        self.rotar_canvas = tk.Canvas(
            canvas_container,
            bg=COLOR_PREVIEW_BG,
            highlightthickness=0,
            borderwidth=0
        )
        self.rotar_canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.rotar_canvas.bind(
            "<Configure>",
            lambda _event: (
                self.rotar_show_page(self.rotation_session.current_page)
                if self.rotation_session
                else self.dibuixar_placeholder_preview()
            )
        )
        
        self.dibuixar_placeholder_preview()
        
        self.rotar_status = ctk.CTkLabel(
            preview_panel,
            text="Esperant PDF...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.rotar_status.pack(fill="x", padx=20, pady=(0, 15))
    
    def dibuixar_placeholder_preview(self):
        self.rotar_canvas.delete("all")
        try:
            w = self.rotar_canvas.winfo_width()
            h = self.rotar_canvas.winfo_height()
            w = w if w >= 10 else 400
            h = h if h >= 10 else 300
        except Exception:
            w, h = 400, 300
        
        page_w = min(w - 40, 350)
        page_h = min(h - 40, 480)
        page_x = (w - page_w) // 2
        page_y = (h - page_h) // 2
        
        self.rotar_canvas.create_rectangle(
            page_x + 3, page_y + 3,
            page_x + page_w + 3, page_y + page_h + 3,
            fill="#0c0d10", outline="", width=0
        )
        self.rotar_canvas.create_rectangle(
            page_x, page_y,
            page_x + page_w, page_y + page_h,
            fill=COLOR_BG_PANEL_ALT, outline=COLOR_BORDER_STRONG, width=1
        )
        
        icon_size = 48
        icon_x = page_x + page_w // 2
        icon_y = page_y + page_h // 2 - 20
        
        self.rotar_canvas.create_rectangle(
            icon_x - icon_size//2, icon_y - icon_size//2,
            icon_x + icon_size//2, icon_y + icon_size//2,
            fill=COLOR_BG_HOVER, outline=COLOR_BORDER_STRONG, width=1
        )
        
        for i, y_offset in enumerate([-10, 0, 10]):
            line_w = 28 - abs(i) * 6
            self.rotar_canvas.create_line(
                icon_x - line_w//2, icon_y + y_offset,
                icon_x + line_w//2, icon_y + y_offset,
                fill=COLOR_TEXT_FAINT, width=2, capstyle="round"
            )
        
        self.rotar_canvas.create_text(
            icon_x, icon_y + 45,
            text="Esperant PDF...",
            fill=COLOR_TEXT_MUTED,
            font=("Segoe UI", 12, "normal"),
            anchor="center"
        )

    # ── LÒGICA ───────────────────────────────────────────────────────

    def rotar_select_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Selecciona PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not file_path:
            return

        try:
            if self.rotation_session is not None:
                self.rotation_session.close()
                self.rotation_session = None

            session = PdfRotationSession(file_path)
        except MissingDependencyError as exc:
            messagebox.showerror("Falta una dependència", str(exc))
            return
        except Exception as exc:
            logger.exception("No se pudo abrir el PDF %s", file_path)
            messagebox.showerror("Error", f"No s'ha pogut obrir el PDF: {exc}")
            return

        self.rotation_session = session
        self.rotar_file_label.configure(text=Path(file_path).name)
        self.rotar_enable_controls()
        self.rotar_show_page(0)
        self.rotar_status.configure(
            text=(
                f"PDF carregat: {session.total_pages} pàgines, "
                f"{session.bookmark_count} marcadors"
            )
        )

    def rotar_enable_controls(self):
        for boto in (self.rotar_prev_btn, self.rotar_next_btn, self.rotar_go_btn):
            boto.configure(
                state="normal", fg_color=COLOR_ACCENT_BLUE, text_color="white", border_width=0
            )

        self.rotar_page_entry.configure(state="normal")

        for boto in (self.rotar_left_btn, self.rotar_180_btn, self.rotar_right_btn):
            boto.configure(
                state="normal", fg_color=COLOR_ACCENT_RED, text_color="white", border_width=0
            )

        self.rotar_save_btn.configure(
            state="normal",
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_PRIMARY_HOVER,
            text_color="white",
            border_width=0,
        )

    def rotar_show_page(self, page_num):
        session = self.rotation_session
        if session is None or not session.is_valid_page(page_num):
            return

        session.go_to(page_num)
        image = session.render_page(page_num)
        image = self._encaixar_a_canvas(image)

        canvas_w = max(self.rotar_canvas.winfo_width(), 400)
        canvas_h = max(self.rotar_canvas.winfo_height(), 400)

        self.rotar_photo = ImageTk.PhotoImage(image)
        self.rotar_canvas.delete("all")
        self.rotar_canvas.create_image(
            canvas_w // 2, canvas_h // 2, image=self.rotar_photo, anchor="center"
        )

        self.rotar_page_entry.delete(0, "end")
        self.rotar_page_entry.insert(0, str(page_num + 1))
        self.rotar_page_info.configure(text=f"Pàgina {page_num + 1} de {session.total_pages}")
        self.rotar_rotation_label.configure(
            text=f"Rotació aplicada: {session.rotation_of(page_num)}°"
        )

    def _encaixar_a_canvas(self, image):
        """Escala la imatge perquè càpiga sencera al canvas, sense deformar-la."""
        canvas_w = max(self.rotar_canvas.winfo_width(), 400)
        canvas_h = max(self.rotar_canvas.winfo_height(), 400)

        available_w = canvas_w - CANVAS_PADDING
        available_h = canvas_h - CANVAS_PADDING
        if available_w <= 1 or available_h <= 1:
            return image

        image_ratio = image.width / image.height
        container_ratio = available_w / available_h

        if image_ratio > container_ratio:
            new_w = max(1, available_w)
            new_h = max(1, int(new_w / image_ratio))
        else:
            new_h = max(1, available_h)
            new_w = max(1, int(new_h * image_ratio))

        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def rotar_prev_page(self):
        if self.rotation_session and self.rotation_session.current_page > 0:
            self.rotar_show_page(self.rotation_session.current_page - 1)

    def rotar_next_page(self):
        session = self.rotation_session
        if session and session.current_page < session.total_pages - 1:
            self.rotar_show_page(session.current_page + 1)

    def rotar_go_to_page(self, event=None):
        session = self.rotation_session
        if session is None:
            return
        try:
            page_num = int(self.rotar_page_entry.get()) - 1
        except ValueError:
            messagebox.showwarning("Advertència", "Introdueix un número vàlid")
            return

        if session.is_valid_page(page_num):
            self.rotar_show_page(page_num)
        else:
            messagebox.showwarning(
                "Advertència", f"Pàgina fora de rang (1-{session.total_pages})"
            )

    def rotar_rotate_page(self, angle):
        session = self.rotation_session
        if session is None:
            return
        session.rotate(session.current_page, angle)
        self.rotar_show_page(session.current_page)

    def rotar_save_pdf(self):
        session = self.rotation_session
        if session is None:
            return
        try:
            output_path = session.save()
        except Exception as exc:
            logger.exception("Error guardando el PDF rotado")
            messagebox.showerror("Error", f"Error al guardar el PDF: {exc}")
            return

        self.rotar_status.configure(text=f"PDF guardat: {output_path.name}")
        messagebox.showinfo("Èxit", f"PDF guardat com:\n{output_path}")
