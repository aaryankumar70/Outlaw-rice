#!/usr/bin/env python3

import subprocess
import re
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib


ROOT = Path.home() / "Pictures" / "Wallpapers"
CTL = Path.home() / "outlaw-rice" / "scripts" / "wallpaperctl"

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

WINDOW_W = 900
WINDOW_H = 260


CSS = b"""
window {
    background-color: rgba(8, 9, 15, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 3px;
}

#search {
    background-color: rgba(10, 11, 18, 0.48);
    color: #f5f4ff;
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 4px;
    padding: 4px 5px;
    font-size: 11px;
}

#search:focus {
    border-color: rgba(197, 167, 255, 0.65);
    box-shadow: none;
}

#carousel {
    background: transparent;
}

#card {
    background-color: rgba(12, 13, 20, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 2px;
}

#card-selected {
    background-color: rgba(255, 255, 255, 0.06);
    border: 2px solid #c5a7ff;
    border-radius: 2px;
}

#empty {
    color: rgba(255, 255, 255, 0.50);
    font-size: 11px;
}
"""


def palette_css():

    css = CSS

    try:
        colors_file = (
            Path.home()
            / ".config"
            / "waybar"
            / "colors.css"
        )

        text = colors_file.read_text()

        colors = dict(
            re.findall(
                r"@define-color\s+(\w+)\s+(#[0-9a-fA-F]{6});",
                text
            )
        )

        accent = colors.get(
            "accent",
            "#c5a7ff"
        )

        foreground = colors.get(
            "foreground",
            "#f5f4ff"
        )

        background = colors.get(
            "background",
            "#08090f"
        )

        # Convert wallpaper-derived background to rgba
        r = int(background[1:3], 16)
        g = int(background[3:5], 16)
        b = int(background[5:7], 16)

        themed_background = (
            f"rgba({r}, {g}, {b}, 0.72)"
        )

        css = css.replace(
            b"rgba(8, 9, 15, 0.72)",
            themed_background.encode()
        )

        css = css.replace(
            b"#f5f4ff",
            foreground.encode()
        )

        css = css.replace(
            b"#c5a7ff",
            accent.encode()
        )

    except Exception:
        pass

    return css

class WallpaperCard:

    def __init__(self, path, callback):

        self.path = path

        self.event = Gtk.EventBox()

        self.event.set_name(
            "card"
        )

        self.image = Gtk.Image()

        self.event.add(
            self.image
        )

        self.event.connect(
            "button-press-event",
            callback,
            self.path
        )

        self.original = None

        try:

            self.original = (
                GdkPixbuf.Pixbuf.new_from_file(
                    str(path)
                )
            )

        except Exception:

            pass


    def set_geometry(
        self,
        width,
        height,
        selected=False
    ):

        width = int(width)
        height = int(height)

        self.event.set_size_request(
            width,
            height
        )

        if selected:

            self.event.set_name(
                "card-selected"
            )

        else:

            self.event.set_name(
                "card"
            )

        if self.original:

            target_w = max(
                1,
                width - 4
            )

            target_h = max(
                1,
                height - 4
            )

            source_w = (
                self.original.get_width()
            )

            source_h = (
                self.original.get_height()
            )

            source_ratio = (
                source_w / source_h
            )

            target_ratio = (
                target_w / target_h
            )

            # Crop instead of stretching
            if source_ratio > target_ratio:

                crop_w = int(
                    source_h * target_ratio
                )

                crop_x = (
                    source_w - crop_w
                ) // 2

                cropped = (
                    self.original.new_subpixbuf(
                        crop_x,
                        0,
                        crop_w,
                        source_h
                    )
                )

            else:

                crop_h = int(
                    source_w / target_ratio
                )

                crop_y = (
                    source_h - crop_h
                ) // 2

                cropped = (
                    self.original.new_subpixbuf(
                        0,
                        crop_y,
                        source_w,
                        crop_h
                    )
                )

            scaled = cropped.scale_simple(
                target_w,
                target_h,
                GdkPixbuf.InterpType.BILINEAR
            )

            self.image.set_from_pixbuf(
                scaled
            )


class Picker(Gtk.Window):

    def __init__(self):

        super().__init__(
            type=Gtk.WindowType.TOPLEVEL
        )

        self.set_title(
            "Wallpaper Picker"
        )

        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)

        self.set_type_hint(
            Gdk.WindowTypeHint.NORMAL
        )

        self.set_default_size(
            WINDOW_W,
            WINDOW_H
        )

        self.set_resizable(False)

        # Transparent window surface
        screen = self.get_screen()

        visual = screen.get_rgba_visual()

        if visual:

            self.set_visual(
                visual
            )

        self.connect(
            "key-press-event",
            self.key
        )

        self.files = sorted(
            p
            for p in ROOT.glob("**/*")
            if p.is_file()
            and p.suffix.lower() in EXTENSIONS
        )

        self.visible = self.files[:]

        self.selected = 0

        self.animating = False
        self.animation_start = 0
        self.animation_direction = 0
        self.animation_duration = 180

        self.cards = {}

        self.build_ui()

        self.position_center()

        self.render()


    def build_ui(self):

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        outer.set_margin_top(16)
        outer.set_margin_bottom(14)
        outer.set_margin_start(18)
        outer.set_margin_end(18)

        self.add(
            outer
        )

        # -------------------------
        # Search
        # -------------------------

        self.search = Gtk.Entry()

        self.search.set_name(
            "search"
        )

        self.search.set_placeholder_text(
            "⌕   Search wallpapers"
        )

        # Make sure it starts completely empty
        self.search.set_text("")

        self.search.connect(
            "changed",
            self.filter
        )

        outer.pack_start(
            self.search,
            False,
            False,
            0
        )

        # -------------------------
        # Carousel
        # -------------------------

        carousel_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        # No arrow buttons.
        # The carousel is controlled with
        # Left / Right keys and mouse clicks.

        self.carousel = Gtk.Fixed()

        self.carousel.set_name(
            "carousel"
        )

        carousel_row.pack_start(
            self.carousel,
            True,
            True,
            0
        )

        outer.pack_start(
            carousel_row,
            True,
            True,
            0
        )


    def position_center(self):

        screen = self.get_screen()

        monitor = screen.get_primary_monitor()

        geo = screen.get_monitor_geometry(
            monitor
        )

        self.move(
            geo.x
            + (geo.width - WINDOW_W) // 2,

            geo.y
            + (geo.height - WINDOW_H) // 2
        )


    # -------------------------------------------------
    # Carousel geometry
    # -------------------------------------------------

    def slot_geometry(self, slot):

        """
        Five fixed carousel positions.

             0       1        2        3       4

           small   medium   SELECTED  medium   small
        """

        if slot == 0:

            return (
                5,
                43,
                115,
                78
            )

        if slot == 1:

            return (
                125,
                27,
                155,
                106
            )

        if slot == 2:

            return (
                285,
                7,
                250,
                142
            )

        if slot == 3:

            return (
                545,
                27,
                155,
                106
            )

        return (
            705,
            43,
            115,
            78
        )


    def index_for_slot(self, slot):

        if not self.visible:

            return None

        offset = slot - 2

        return (
            self.selected + offset
        ) % len(self.visible)


    # -------------------------------------------------
    # Build carousel
    # -------------------------------------------------

    def render(self):

        for child in self.carousel.get_children():

            self.carousel.remove(
                child
            )

        self.cards.clear()

        if not self.visible:

            label = Gtk.Label(
                label="No matching wallpapers"
            )

            label.set_name(
                "empty"
            )

            self.carousel.put(
                label,
                300,
                65
            )

            self.carousel.show_all()

            return

        for slot in range(5):

            index = self.index_for_slot(
                slot
            )

            if index is None:

                continue

            path = self.visible[
                index
            ]

            card = WallpaperCard(
                path,
                self.card_clicked
            )

            self.cards[index] = card

            x, y, w, h = (
                self.slot_geometry(
                    slot
                )
            )

            card.set_geometry(
                w,
                h,
                slot == 2
            )

            self.carousel.put(
                card.event,
                x,
                y
            )

        self.carousel.show_all()


    # -------------------------------------------------
    # Animation
    # -------------------------------------------------

    def move_selection(self, direction):

        if not self.visible:

            return

        if self.animating:

            return

        if len(self.visible) == 1:

            return

        self.animation_direction = direction

        self.animation_start = (
            GLib.get_monotonic_time()
        )

        self.animating = True

        self.selected = (
            self.selected + direction
        ) % len(self.visible)

        GLib.timeout_add(
            16,
            self.animate
        )


    def animate(self):

        elapsed = (
            GLib.get_monotonic_time()
            - self.animation_start
        ) / 1000.0

        progress = min(
            1.0,
            elapsed / self.animation_duration
        )

        # Smooth ease-in-out
        eased = (
            3 * progress * progress
            - 2
            * progress
            * progress
            * progress
        )

        self.render_animation(
            eased
        )

        if progress >= 1.0:

            self.animating = False

            self.render()

            return False

        return True


    def render_animation(self, progress):

        direction = (
            self.animation_direction
        )

        for child in self.carousel.get_children():

            self.carousel.remove(
                child
            )

        self.cards.clear()

        for old_slot in range(5):

            old_index = (
                self.selected
                - direction
                + (old_slot - 2)
            ) % len(self.visible)

            path = self.visible[
                old_index
            ]

            card = WallpaperCard(
                path,
                self.card_clicked
            )

            self.cards[old_index] = card

            new_slot = (
                old_slot - direction
            )

            # Cards leaving the screen
            if (
                new_slot < 0
                or new_slot > 4
            ):

                if direction > 0:

                    x, y, w, h = (
                        self.slot_geometry(0)
                    )

                    x -= 150

                else:

                    x, y, w, h = (
                        self.slot_geometry(4)
                    )

                    x += 150

                old_x, old_y, old_w, old_h = (
                    self.slot_geometry(
                        old_slot
                    )
                )

                x = (
                    old_x
                    + (x - old_x)
                    * progress
                )

                y = (
                    old_y
                    + (y - old_y)
                    * progress
                )

                w = (
                    old_w
                    + (w - old_w)
                    * progress
                )

                h = (
                    old_h
                    + (h - old_h)
                    * progress
                )

                card.set_geometry(
                    w,
                    h,
                    False
                )

                self.carousel.put(
                    card.event,
                    int(x),
                    int(y)
                )

                continue

            old_x, old_y, old_w, old_h = (
                self.slot_geometry(
                    old_slot
                )
            )

            new_x, new_y, new_w, new_h = (
                self.slot_geometry(
                    new_slot
                )
            )

            x = (
                old_x
                + (new_x - old_x)
                * progress
            )

            y = (
                old_y
                + (new_y - old_y)
                * progress
            )

            w = (
                old_w
                + (new_w - old_w)
                * progress
            )

            h = (
                old_h
                + (new_h - old_h)
                * progress
            )

            selected = (
                new_slot == 2
            )

            card.set_geometry(
                w,
                h,
                selected
            )

            self.carousel.put(
                card.event,
                int(x),
                int(y)
            )

        self.carousel.show_all()


    # -------------------------------------------------
    # Mouse
    # -------------------------------------------------

    def card_clicked(
        self,
        widget,
        event,
        path
    ):

        if self.animating:

            return True

        try:

            index = self.visible.index(
                path
            )

        except ValueError:

            return True

        current = self.selected

        if index == current:

            self.apply_selected()

            return True

        count = len(
            self.visible
        )

        forward = (
            index - current
        ) % count

        backward = (
            current - index
        ) % count

        if forward <= backward:

            direction = 1

        else:

            direction = -1

        self.move_selection(
            direction
        )

        return True


    # -------------------------------------------------
    # Search
    # -------------------------------------------------

    def filter(self, *_):

        query = (
            self.search
            .get_text()
            .lower()
            .strip()
        )

        self.visible = [
            path
            for path in self.files
            if query in path.name.lower()
        ]

        self.selected = 0

        self.animating = False

        self.render()


    # -------------------------------------------------
    # Apply
    # -------------------------------------------------

    def apply_selected(self):

        if not self.visible:

            return

        path = self.visible[
            self.selected
        ]

        subprocess.Popen(
            [
                str(CTL),
                "set",
                str(path)
            ]
        )

        self.destroy()


    # -------------------------------------------------
    # Keyboard
    # -------------------------------------------------

    def key(self, _, event):

        key = event.keyval

        if key == Gdk.KEY_Escape:

            self.destroy()

            return True

        if key in (
            Gdk.KEY_Return,
            Gdk.KEY_KP_Enter
        ):

            self.apply_selected()

            return True

        if key == Gdk.KEY_Left:

            self.move_selection(-1)

            return True

        if key == Gdk.KEY_Right:

            self.move_selection(1)

            return True

        return False


# ---------------------------------------------------------
# Start
# ---------------------------------------------------------

if __name__ == "__main__":

    # Apply themed CSS before creating the picker
    provider = Gtk.CssProvider()

    provider.load_from_data(
        palette_css()
    )

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win = Picker()

    win.show_all()

    Gtk.main()
