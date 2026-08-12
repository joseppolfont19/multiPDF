"""Domain logic: no GUI, no dialogs, no global state.

Everything here can run inside a test, a cron job or a container. The GUI and
the CLI are two interchangeable front-ends over this package.
"""

from .bookmarks import add_bookmarks, count_pages
from .compression import Recommendation, recommend_settings
from .conversion import build_pdf_for_folder, images_to_pdf, open_and_transform, process_tree
from .discovery import FolderStats, find_all_images, find_images, natural_sort_key, scan_folder
from .resources import SystemUsage, current_usage, wait_for_resources

__all__ = [
    "add_bookmarks",
    "count_pages",
    "Recommendation",
    "recommend_settings",
    "build_pdf_for_folder",
    "images_to_pdf",
    "open_and_transform",
    "process_tree",
    "FolderStats",
    "find_all_images",
    "find_images",
    "natural_sort_key",
    "scan_folder",
    "SystemUsage",
    "current_usage",
    "wait_for_resources",
]
