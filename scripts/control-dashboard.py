#!/usr/bin/env python3
"""Compact glass dashboard replacing the old text-only control menu."""
import subprocess
import re
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

CSS = b"""
window { background: rgba(13,14,24,.90); border: 1px solid rgba(255,255,255,.18); border-radius: 24px; }
label { color: #f4f3ff; font-family: JetBrainsMono Nerd Font; } #heading { font-size: 18px; font-weight: bold; } #detail { color: rgba(240,240,255,.62); font-size: 11px; }
button { background: rgba(255,255,255,.075); color: #f5f3ff; border: 1px solid rgba(255,255,255,.12); border-radius: 15px; padding: 16px; } button:hover { background: rgba(186,154,255,.23); border-color: rgba(211,188,255,.8); }
"""
def palette_css():
    try:
        colors = dict(re.findall(r"@define-color\\s+(\\w+)\\s+(#[0-9a-fA-F]{6});", (Path.home()/'.config/waybar/colors.css').read_text()))
        return CSS.replace(b'#f4f3ff', colors.get('foreground','#f4f3ff').encode()).replace(b'#f5f3ff', colors.get('foreground','#f5f3ff').encode()).replace(b'#ba9aff', colors.get('accent','#ba9aff').encode()).replace(b'#d3bcff', colors.get('accent','#d3bcff').encode())
    except Exception: return CSS
class Dashboard(Gtk.Window):
    def __init__(self):
        super().__init__(); self.set_decorated(False); self.set_keep_above(True); self.set_skip_taskbar_hint(True); self.set_type_hint(Gdk.WindowTypeHint.DIALOG); self.set_default_size(650,330); self.connect('key-press-event', lambda w,e: self.destroy() if e.keyval == Gdk.KEY_Escape else None)
        provider=Gtk.CssProvider(); provider.load_from_data(palette_css()); Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin=22); self.add(body)
        h=Gtk.Box(); title=Gtk.Label(label='OUTLAW  /  CONTROL'); title.set_name('heading'); title.set_xalign(0); h.pack_start(title,True,True,0); stat=Gtk.Label(label='a compact desktop dashboard'); stat.set_name('detail'); h.pack_end(stat,False,False,0); body.pack_start(h,False,False,0)
        grid=Gtk.Grid(column_spacing=10,row_spacing=10); body.pack_start(grid,True,True,0)
        for i,(name,detail,cmd) in enumerate([('󰤨  Wi‑Fi','networks','wifi-menu'),('󰂯  Bluetooth','devices','bluetooth-menu'),('󰕾  Audio','volume','pavucontrol'),('󰸉  Wallpaper','gallery','wallpaper-menu'),('󰎆  Media','play / pause','playerctl play-pause'),('󰒓  Settings','system','systemsettings5')]):
            b=Gtk.Button(label=name+'\n'+detail); b.connect('clicked',self.run,cmd); grid.attach(b,i%3,i//3,1,1)
    def run(self, _, cmd): subprocess.Popen(['sh','-lc',cmd]); self.destroy()
if __name__=='__main__':
    w=Dashboard(); w.show_all(); Gtk.main()
