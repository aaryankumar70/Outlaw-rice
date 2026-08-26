#!/usr/bin/env python3
"""Bottom-centred wallpaper gallery for Outlaw Rice.

This intentionally is not a Rofi mode: it is a small, keyboard-first GTK
overlay with real thumbnails, so the selection layout stays faithful to the
desktop reference.
"""
import subprocess
import re
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf

ROOT = Path.home() / "Pictures" / "Wallpapers"
CTL = Path.home() / "outlaw-rice" / "scripts" / "wallpaperctl"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

CSS = b"""
window { background-color: rgba(11, 12, 20, .83); border: 1px solid rgba(255,255,255,.19); border-radius: 26px; }
#title { color: rgba(245,246,255,.96); font-size: 13px; font-weight: 700; }
#subtitle { color: rgba(225,226,255,.58); font-size: 10px; }
entry { background: rgba(255,255,255,.09); color: #f8f7ff; border: 1px solid rgba(255,255,255,.13); border-radius: 16px; padding: 9px 13px; }
#thumb { background: transparent; border: 2px solid transparent; border-radius: 13px; padding: 3px; }
#thumb:selected, #thumb:hover { background: rgba(197,167,255,.22); border-color: rgba(220,198,255,.86); }
#hint { color: rgba(240,240,255,.53); font-size: 10px; }
"""

def palette_css(css):
    """Use Matugen's current Waybar palette in this GTK surface too."""
    try:
        text = (Path.home() / ".config" / "waybar" / "colors.css").read_text()
        colors = dict(re.findall(r"@define-color\\s+(\\w+)\\s+(#[0-9a-fA-F]{6});", text))
        accent, foreground = colors.get("accent", "#c5a7ff"), colors.get("foreground", "#f5f4ff")
        return CSS.replace(b"#f8f7ff", foreground.encode()).replace(b"#f5f4ff", foreground.encode()).replace(b"#c5a7ff", accent.encode()).replace(b"#dcc6ff", accent.encode())
    except Exception:
        return CSS

class Picker(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False); self.set_keep_above(True); self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_default_size(790, 300); self.set_resizable(False)
        self.connect("key-press-event", self.key)
        self.files = sorted(p for p in ROOT.expanduser().glob("**/*") if p.suffix.lower() in EXTENSIONS)
        self.visible = self.files[:]
        self.selected = 0
        provider = Gtk.CssProvider(); provider.load_from_data(palette_css(CSS))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=16)
        self.add(outer)
        header = Gtk.Box(spacing=8); outer.pack_start(header, False, False, 0)
        label = Gtk.Label(label="WALLPAPERS"); label.set_name("title"); label.set_xalign(0); header.pack_start(label, True, True, 0)
        self.name = Gtk.Label(); self.name.set_name("subtitle"); self.name.set_xalign(1); header.pack_end(self.name, False, False, 0)
        self.row = Gtk.FlowBox(); self.row.set_name("thumb"); self.row.set_max_children_per_line(6); self.row.set_selection_mode(Gtk.SelectionMode.SINGLE); self.row.set_homogeneous(True)
        self.row.connect("selected-children-changed", self.changed)
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER); scroll.add(self.row); outer.pack_start(scroll, True, True, 0)
        self.search = Gtk.Entry(); self.search.set_placeholder_text("⌕  Search wallpapers"); self.search.connect("changed", self.filter); outer.pack_start(self.search, False, False, 0)
        hint = Gtk.Label(label="← / → browse    Enter apply    Esc close    •    Matugen colours update after selection")
        hint.set_name("hint"); outer.pack_start(hint, False, False, 0)
        self.render(); self.position_bottom()

    def position_bottom(self):
        screen = self.get_screen(); monitor = screen.get_primary_monitor(); geo = screen.get_monitor_geometry(monitor)
        self.move(geo.x + (geo.width - 790) // 2, geo.y + geo.height - 350)

    def tile(self, path):
        try: pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 112, 112, True)
        except Exception: return None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        image = Gtk.Image.new_from_pixbuf(pix); box.pack_start(image, True, True, 0)
        text = Gtk.Label(label=path.stem[:16]); text.set_ellipsize(3); box.pack_start(text, False, False, 0)
        child = Gtk.FlowBoxChild(); child.add(box); return child

    def render(self):
        for child in self.row.get_children(): self.row.remove(child)
        for path in self.visible:
            child = self.tile(path)
            if child: self.row.add(child)
        self.row.show_all()
        if self.visible:
            self.selected = min(self.selected, len(self.visible) - 1); self.row.select_child(self.row.get_children()[self.selected]); self.name.set_text(self.visible[self.selected].name)
        else: self.name.set_text("No matching wallpapers")

    def filter(self, *_):
        query = self.search.get_text().lower().strip(); self.visible = [p for p in self.files if query in p.name.lower()]; self.selected = 0; self.render()

    def changed(self, box):
        selected = box.get_selected_children()
        if selected:
            self.selected = box.get_children().index(selected[0]); self.name.set_text(self.visible[self.selected].name)

    def key(self, _, event):
        if event.keyval == Gdk.KEY_Escape: self.destroy(); return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.visible:
            subprocess.Popen([str(CTL), "set", str(self.visible[self.selected])]); self.destroy(); return True
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Right) and self.visible:
            self.selected = (self.selected + (-1 if event.keyval == Gdk.KEY_Left else 1)) % len(self.visible)
            child = self.row.get_children()[self.selected]; self.row.select_child(child); child.grab_focus(); return True
        return False

if __name__ == "__main__":
    win = Picker(); win.show_all(); Gtk.main()
