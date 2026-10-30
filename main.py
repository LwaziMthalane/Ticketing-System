"""G-Yeza Helpdesk - IT ticketing for desktop and Android (Kivy + KivyMD 2.x).

Local-first: every ticket is stored in one JSON file on the device. The ticket
logic lives in gyeza_store.py; this file is only the screens.
"""
import os
import sys
from datetime import datetime

from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import escape_markup, platform
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

from gyeza_store import (ACTIVE, CATEGORIES, PRIORITIES, STATUSES, Store)

VERSION = "1.0.0"

# G-Yeza brand colours: #106098 and #3192c7
BLUE = (16 / 255, 96 / 255, 152 / 255, 1)
LIGHT = (49 / 255, 146 / 255, 199 / 255, 1)
PAGE_BG = (0.94, 0.96, 0.98, 1)
WHITE = (1, 1, 1, 1)
DARK = (0.08, 0.13, 0.19, 1)
MUTED = (0.40, 0.47, 0.54, 1)
CHIP_OFF = (0.90, 0.94, 0.97, 1)
RED = (0.78, 0.16, 0.14, 1)
AMBER = (0.86, 0.52, 0.02, 1)
GREEN = (0.16, 0.57, 0.31, 1)
GREY = (0.46, 0.52, 0.58, 1)
PURPLE = (0.45, 0.33, 0.70, 1)

STATUS_COLORS = {"Open": LIGHT, "In Progress": AMBER, "On Hold": PURPLE, "Resolved": GREEN, "Closed": GREY}
PRIORITY_COLORS = {"Low": GREY, "Medium": LIGHT, "High": AMBER, "Urgent": RED}
FILTERS = ("Active", "All", "Open", "In Progress", "On Hold", "Resolved", "Closed", "Overdue", "Mine")
NAV = (("dashboard", "view-dashboard-outline", "Home"), ("tickets", "ticket-outline", "Tickets"),
       ("new", "plus-circle-outline", "New"), ("settings", "cog-outline", "Settings"))


def resource(name):
    """Find a bundled file both when running from source and inside a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ---------------------------------------------------------------- small widgets
class Painted(MDBoxLayout):
    """A box with a rounded, recolourable background."""

    def __init__(self, bg=None, radius=0, **kwargs):
        super().__init__(**kwargs)
        self._bg = None
        if bg is not None:
            with self.canvas.before:
                self._bg = Color(*bg)
                self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_bg(self, rgba):
        if self._bg is not None:
            self._bg.rgba = rgba


class Tap(ButtonBehavior, Painted):
    """A tappable Painted box."""


def label(text, size=14, color=DARK, bold=False, halign="left"):
    """Wrapping label that grows to fit its text."""
    text = escape_markup(str(text))
    if bold:
        text = f"[b]{text}[/b]"
    lbl = MDLabel(text=text, markup=True, size_hint_y=None, height=dp(size + 8), font_size=dp(size),
                  theme_text_color="Custom", text_color=color, halign=halign)
    lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
    lbl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1] + dp(4), dp(size + 6))))
    return lbl


def line(text, size=14, color=DARK, bold=False, halign="left", height=None):
    """Single fixed-height line that is cut off with '...' when too long."""
    text = escape_markup(str(text))
    if bold:
        text = f"[b]{text}[/b]"
    lbl = MDLabel(text=text, markup=True, size_hint_y=None, height=dp(height or size + 8), font_size=dp(size),
                  theme_text_color="Custom", text_color=color, halign=halign, valign="middle",
                  shorten=True, shorten_from="right")
    lbl.bind(size=lambda i, s: setattr(i, "text_size", s))
    return lbl


def centered(text, size=13, color=DARK, bold=False):
    text = escape_markup(str(text))
    if bold:
        text = f"[b]{text}[/b]"
    lbl = MDLabel(text=text, markup=True, font_size=dp(size), theme_text_color="Custom", text_color=color,
                  halign="center", valign="middle")
    lbl.bind(size=lambda i, s: setattr(i, "text_size", s))
    return lbl


def card(widgets, pad=14, spacing=6, bg=WHITE):
    c = Painted(bg=bg, radius=dp(12), orientation="vertical", size_hint_y=None, padding=dp(pad), spacing=dp(spacing))
    c.bind(minimum_height=c.setter("height"))
    for w in widgets:
        c.add_widget(w)
    return c


def pill(text, callback, bg=BLUE, fg=WHITE, height=44, width=None):
    box = Tap(bg=bg, radius=dp(height / 2), size_hint_y=None, height=dp(height), padding=(dp(16), 0))
    if width:
        box.size_hint_x = None
        box.width = dp(width)
    box.lbl = centered(text, 14, fg, bold=True)
    box.add_widget(box.lbl)
    box.bind(on_release=lambda *_: callback())
    return box


def badge(text, color, width=92):
    box = Painted(bg=color, radius=dp(11), size_hint=(None, None), size=(dp(width), dp(22)))
    box.add_widget(centered(text, 11, WHITE, bold=True))
    return box


def chip_group(options, current, on_pick, cols=3, colors=None):
    """Row(s) of tap-to-select chips. Calls on_pick(value) when one is tapped."""
    colors = colors or {}
    grid = GridLayout(cols=cols, spacing=dp(6), size_hint_y=None)
    rows = -(-len(options) // cols)
    grid.height = rows * dp(38) + (rows - 1) * dp(6)
    items = {}
    state = {"cur": current}

    def paint_all():
        for opt, (box, lbl) in items.items():
            on = opt == state["cur"]
            box.set_bg(colors.get(opt, BLUE) if on else CHIP_OFF)
            lbl.text_color = WHITE if on else DARK

    for opt in options:
        box = Tap(bg=CHIP_OFF, radius=dp(19), size_hint_y=None, height=dp(38), padding=(dp(4), 0))
        lbl = centered(opt, 13, DARK)
        box.add_widget(lbl)
        items[opt] = (box, lbl)

        def picked(_, opt=opt):
            state["cur"] = opt
            paint_all()
            on_pick(opt)

        box.bind(on_release=picked)
        grid.add_widget(box)
    paint_all()
    return grid


def text_field(hint, text="", multiline=False, height=56):
    field = MDTextField(MDTextFieldHintText(text=hint), mode="outlined", multiline=multiline, text=str(text or ""),
                        size_hint_y=None, height=dp(height))
    holder = MDBoxLayout(size_hint_y=None, height=dp(height + 12), padding=(0, dp(8), 0, 0))
    holder.add_widget(field)
    return holder, field


# ------------------------------------------------------------------------- app
class HelpdeskApp(MDApp):
    title = "G-Yeza Helpdesk"

    # ------------------------------------------------------------ build / chrome
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Window.clearcolor = PAGE_BG
        Window.softinput_mode = "below_target"
        if platform in ("win", "linux", "macosx"):
            Window.size = (460, 760)
        self.icon = resource("icon.png")

        self.store = Store(os.path.join(self.user_data_dir, "helpdesk.json"))
        self.history = []
        self.current = None
        self.filter = "Active"
        self.search = ""
        self.drafts = {}
        self.cur_scroll = None
        self.comment_field = None

        self.float = FloatLayout()
        root = Painted(bg=PAGE_BG, orientation="vertical")

        header = Painted(bg=BLUE, size_hint_y=None, height=dp(56), padding=(dp(4), 0, dp(12), 0), spacing=dp(4))
        self.head_btn = MDIconButton(icon="lifebuoy", theme_icon_color="Custom", icon_color=WHITE,
                                     pos_hint={"center_y": 0.5})
        self.head_btn.bind(on_release=lambda *_: self.back() if self.history else None)
        self.title_label = MDLabel(text="", theme_text_color="Custom", text_color=WHITE, font_size=dp(20))
        self.title_label.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        header.add_widget(self.head_btn)
        header.add_widget(self.title_label)
        root.add_widget(header)
        root.add_widget(Painted(bg=LIGHT, size_hint_y=None, height=dp(3)))

        row = MDBoxLayout()
        row.add_widget(Widget())
        self.body = MDBoxLayout(size_hint_x=None)
        row.add_widget(self.body)
        row.add_widget(Widget())
        root.add_widget(row)
        Window.bind(width=self.fit_body)
        self.fit_body()

        nav = Painted(bg=WHITE, size_hint_y=None, height=dp(62))
        self.nav_cells = {}
        for key, icon, text in NAV:
            cell = Tap(orientation="vertical", padding=(0, dp(7), 0, dp(3)), spacing=dp(1))
            ic = MDIcon(icon=icon, theme_text_color="Custom", text_color=MUTED, font_size=dp(24),
                        size_hint=(None, None), size=(dp(26), dp(26)), pos_hint={"center_x": 0.5})
            lb = centered(text, 11, MUTED)
            lb.size_hint_y = None
            lb.height = dp(15)
            cell.add_widget(ic)
            cell.add_widget(lb)
            cell.bind(on_release=lambda *_, k=key: self.tab(k))
            self.nav_cells[key] = (ic, lb)
            nav.add_widget(cell)
        root.add_widget(nav)

        self.float.add_widget(root)
        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_interval(self.tick, 60)
        self.show_page(("dashboard",))
        return self.float

    def fit_body(self, *_):
        self.body.width = min(Window.width, dp(820))

    def tick(self, _dt):
        if self.current and self.current[0] == "dashboard":
            self.refresh()

    def toast(self, text):
        box = Painted(bg=(0.08, 0.13, 0.19, 0.95), radius=dp(8), size_hint=(0.9, None), height=dp(48),
                      padding=(dp(14), 0), pos_hint={"center_x": 0.5, "y": 0.11})
        box.add_widget(MDLabel(text=escape_markup(text), markup=True, theme_text_color="Custom", text_color=WHITE,
                               font_size=dp(14)))
        self.float.add_widget(box)
        Clock.schedule_once(lambda dt: self.float.remove_widget(box) if box.parent else None, 2.6)

    # --------------------------------------------------------------- navigation
    def tab(self, key):
        self.history = []
        self.show_page((key,), push=False)

    def go(self, *page):
        self.show_page(tuple(page))

    def back(self):
        if self.history:
            self.show_page(self.history.pop(), push=False)

    def on_key(self, window, key, *args):
        if key == 27:  # Android back button / Esc
            if self.history:
                self.back()
                return True
            if self.current and self.current[0] != "dashboard":
                self.tab("dashboard")
                return True
        return False

    def show_page(self, page, push=True):
        if push and self.current is not None and self.current != page:
            self.history.append(self.current)
        self.current = page
        builders = {"dashboard": self.page_dashboard, "tickets": self.page_tickets, "new": self.page_new,
                    "settings": self.page_settings, "ticket": self.page_ticket}
        self.comment_field = None
        self.body.clear_widgets()
        self.body.add_widget(builders[page[0]](*page[1:]))
        titles = {"dashboard": "Helpdesk", "tickets": "Tickets", "new": "New ticket", "settings": "Settings",
                  "ticket": f"Ticket #{page[1]}" if len(page) > 1 else "Ticket"}
        self.title_label.text = titles[page[0]]
        self.head_btn.icon = "arrow-left" if self.history else "lifebuoy"
        active = {"ticket": "tickets"}.get(page[0], page[0])
        for key, (ic, lb) in self.nav_cells.items():
            ic.text_color = lb.text_color = BLUE if key == active else MUTED

    def refresh(self):
        """Rebuild the current page but keep scroll position and any half-typed comment."""
        y = self.cur_scroll.scroll_y if self.cur_scroll is not None else 1
        if self.comment_field is not None and self.current[0] == "ticket":
            self.drafts[self.current[1]] = self.comment_field.text
        self.show_page(self.current, push=False)
        scroll = self.cur_scroll
        Clock.schedule_once(lambda dt: setattr(scroll, "scroll_y", y), 0.05)

    def new_scroll(self):
        scroll = ScrollView(do_scroll_x=False)
        content = MDBoxLayout(orientation="vertical", spacing=dp(10), padding=(dp(12), dp(10), dp(12), dp(24)),
                              size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        self.cur_scroll = scroll
        return scroll, content

    # --------------------------------------------------------------- ticket row
    def ticket_row(self, t):
        overdue = self.store.is_overdue(t)
        row = Tap(bg=WHITE, radius=dp(12), size_hint_y=None, height=dp(88), padding=dp(10), spacing=dp(10))
        row.add_widget(Painted(bg=PRIORITY_COLORS[t["priority"]], radius=dp(3), size_hint_x=None, width=dp(5)))
        col = MDBoxLayout(orientation="vertical", spacing=dp(2))
        col.add_widget(line(t["title"], 15, DARK, bold=True, height=22))
        col.add_widget(line(f"#{t['id']}  ·  {t['requester']}  ·  {t['category']}", 12, MUTED, height=18))
        bottom = MDBoxLayout(spacing=dp(8), size_hint_y=None, height=dp(24))
        bottom.add_widget(badge(t["status"], STATUS_COLORS[t["status"]]))
        bottom.add_widget(line(self.store.due_text(t), 12, RED if overdue else MUTED, halign="right", height=24))
        col.add_widget(bottom)
        row.add_widget(col)
        row.bind(on_release=lambda *_: self.go("ticket", t["id"]))
        return row

    # ---------------------------------------------------------------- dashboard
    def page_dashboard(self):
        scroll, content = self.new_scroll()
        hour = datetime.now().hour
        greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        name = self.store.settings.get("tech_name", "").strip()

        top = Painted(bg=WHITE, radius=dp(12), size_hint_y=None, height=dp(96), padding=dp(10), spacing=dp(12))
        top.add_widget(Image(source=resource("logo.png"), size_hint=(None, 1), width=dp(92), fit_mode="contain"))
        text = MDBoxLayout(orientation="vertical", spacing=dp(2))
        text.add_widget(line(f"{greet}{', ' + name if name else ''}", 17, BLUE, bold=True, height=28))
        text.add_widget(line("Helpdesk ticketing", 13, MUTED, height=20))
        text.add_widget(line(datetime.now().strftime("%A, %d %B %Y"), 12, MUTED, height=18))
        top.add_widget(text)
        content.add_widget(top)

        c = self.store.counts()
        tiles = (("Open", c["Open"], LIGHT, "Open"), ("In progress", c["In Progress"], AMBER, "In Progress"),
                 ("Overdue", c["Overdue"], RED, "Overdue"), ("On hold", c["On Hold"], PURPLE, "On Hold"),
                 ("Unassigned", c["Unassigned"], BLUE, "Active"), ("Resolved today", c["Resolved today"], GREEN, "Resolved"))
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(3 * 74 + 2 * 8))
        for caption, value, color, flt in tiles:
            tile = Tap(bg=WHITE, radius=dp(12), orientation="vertical", padding=(dp(14), dp(8)), spacing=dp(0))
            tile.add_widget(line(str(value), 26, color, bold=True, height=38))
            tile.add_widget(line(caption, 13, MUTED, height=20))
            tile.bind(on_release=lambda *_, f=flt: self.open_filter(f))
            grid.add_widget(tile)
        content.add_widget(grid)

        content.add_widget(pill("+  New ticket", lambda: self.tab("new")))

        hot = self.store.attention()
        content.add_widget(label("Needs attention", 15, DARK, bold=True))
        if hot:
            for t in hot:
                content.add_widget(self.ticket_row(t))
        else:
            content.add_widget(card([label("All clear - nothing overdue or urgent.", 14, MUTED)]))

        recent = self.store.query("All")[:5]
        if recent:
            content.add_widget(label("Recently updated", 15, DARK, bold=True))
            for t in recent:
                content.add_widget(self.ticket_row(t))
        elif not self.store.tickets:
            content.add_widget(card([label("No tickets yet. Tap New ticket to log your first one, or load sample "
                                           "tickets from Settings to try the app out.", 14, MUTED)]))
        return scroll

    def open_filter(self, flt):
        self.filter = flt
        self.search = ""
        self.tab("tickets")

    # ------------------------------------------------------------------ tickets
    def page_tickets(self):
        outer = MDBoxLayout(orientation="vertical", padding=(dp(12), dp(6), dp(12), 0), spacing=dp(6))
        holder, field = text_field("Search tickets (title, name, #id)", self.search)
        outer.add_widget(holder)
        outer.add_widget(chip_group(FILTERS, self.filter, self.set_filter, cols=3))
        count = label("", 12, MUTED)
        outer.add_widget(count)

        scroll = ScrollView(do_scroll_x=False)
        box = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, padding=(0, 0, 0, dp(16)))
        box.bind(minimum_height=box.setter("height"))
        scroll.add_widget(box)
        self.cur_scroll = scroll
        outer.add_widget(scroll)

        def fill(*_):
            self.search = field.text
            box.clear_widgets()
            flt = self.filter
            found = self.store.query("Active" if flt == "Mine" else flt, field.text, mine=(flt == "Mine"))
            if flt == "Mine" and not self.store.settings.get("tech_name", "").strip():
                count.text = "Set your name in Settings so 'Mine' knows which tickets are yours."
            else:
                count.text = f"{len(found)} ticket{'s' if len(found) != 1 else ''}"
            for t in found[:100]:
                box.add_widget(self.ticket_row(t))
            if len(found) > 100:
                box.add_widget(label("Showing the 100 most recently updated. Use search to narrow down.", 12, MUTED))
            if not found:
                box.add_widget(card([label("Nothing matches.", 14, MUTED)]))

        field.bind(text=fill)
        self._fill_tickets = fill
        fill()
        return outer

    def set_filter(self, value):
        self.filter = value
        self._fill_tickets()

    # --------------------------------------------------------------- new ticket
    def page_new(self):
        scroll, content = self.new_scroll()
        values = {"category": "Other", "priority": "Medium"}
        h_title, f_title = text_field("Title (what is the problem?)")
        h_req, f_req = text_field("Requester name")
        h_contact, f_contact = text_field("Requester email or phone")
        h_assign, f_assign = text_field("Assign to", self.store.settings.get("tech_name", ""))
        h_desc, f_desc = text_field("Description", multiline=True, height=110)
        msg = label("", 13, RED)

        def pick(key):
            return lambda v: values.__setitem__(key, v)

        def create():
            try:
                t = self.store.create(f_title.text, f_req.text, f_contact.text, values["category"],
                                      values["priority"], f_assign.text, f_desc.text)
            except ValueError as err:
                msg.text = str(err)
                return
            self.toast(f"Ticket #{t['id']} created")
            self.history = [("dashboard",)]
            self.current = ("tickets",)
            self.show_page(("ticket", t["id"]))

        for w in (h_title, h_req, h_contact):
            content.add_widget(w)
        content.add_widget(label("Category", 12, MUTED, bold=True))
        content.add_widget(chip_group(CATEGORIES, values["category"], pick("category"), cols=3))
        content.add_widget(label("Priority", 12, MUTED, bold=True))
        content.add_widget(chip_group(PRIORITIES, values["priority"], pick("priority"), cols=4, colors=PRIORITY_COLORS))
        content.add_widget(h_assign)
        content.add_widget(h_desc)
        content.add_widget(msg)
        content.add_widget(pill("Create ticket", create))
        return scroll

    # ------------------------------------------------------------- ticket detail
    def change(self, tid, field, value):
        if self.store.set_field(tid, field, value):
            self.toast(f"{field.capitalize()}: {value}")
            self.refresh()

    def page_ticket(self, tid):
        t = self.store.get(tid)
        scroll, content = self.new_scroll()
        if t is None:
            content.add_widget(card([label("This ticket no longer exists.", 15, MUTED)]))
            return scroll
        overdue = self.store.is_overdue(t)

        info = [label(t["title"], 18, DARK, bold=True),
                label(f"#{t['id']}  ·  opened {t['created']}", 12, MUTED),
                label(t["requester"] + (f"  ·  {t['contact']}" if t["contact"] else ""), 14, DARK),
                label(self.store.due_text(t), 13, RED if overdue else MUTED, bold=overdue)]
        content.add_widget(card(info, spacing=3))

        content.add_widget(card([
            label("Status", 12, MUTED, bold=True),
            chip_group(STATUSES, t["status"], lambda v: self.change(tid, "status", v), cols=3, colors=STATUS_COLORS),
            label("Priority", 12, MUTED, bold=True),
            chip_group(PRIORITIES, t["priority"], lambda v: self.change(tid, "priority", v), cols=4,
                       colors=PRIORITY_COLORS),
            label("Category", 12, MUTED, bold=True),
            chip_group(CATEGORIES, t["category"], lambda v: self.change(tid, "category", v), cols=3)]))

        h_assign, f_assign = text_field("Assigned to", t["assignee"])
        buttons = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        buttons.add_widget(pill("Save", lambda: self.change(tid, "assignee", f_assign.text), height=44, width=90))
        me = self.store.settings.get("tech_name", "").strip()
        if me:
            buttons.add_widget(pill("Assign to me", lambda: self.change(tid, "assignee", me), bg=LIGHT, height=44))
        content.add_widget(card([h_assign, buttons]))

        if t["description"]:
            content.add_widget(card([label("Description", 12, MUTED, bold=True), label(t["description"], 14, DARK)]))

        h_comment, f_comment = text_field("Add a note or reply", self.drafts.get(tid, ""), multiline=True, height=90)
        self.comment_field = f_comment

        def add_note(resolve=None):
            text = f_comment.text.strip()
            if text:
                self.store.add_comment(tid, text)
            if resolve:
                self.store.set_field(tid, "status", resolve)
            if not text and not resolve:
                self.toast("Type a note first")
                return
            self.drafts.pop(tid, None)
            f_comment.text = ""
            self.toast("Saved")
            self.refresh()

        actions = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        actions.add_widget(pill("Add note", add_note, height=44))
        if t["status"] in ACTIVE:
            actions.add_widget(pill("Resolve", lambda: add_note("Resolved"), bg=GREEN, height=44))
        else:
            actions.add_widget(pill("Reopen", lambda: add_note("Open"), bg=AMBER, height=44))
        content.add_widget(card([h_comment, actions]))

        entries = [label("Activity", 12, MUTED, bold=True)]
        for e in reversed(t["log"]):
            entries.append(label(f"{e['when']}  ·  {e['who']}", 11, MUTED))
            entries.append(label(e["text"], 14, DARK if e["kind"] == "comment" else MUTED))
        content.add_widget(card(entries, spacing=2))

        armed = {"on": False}
        delete = pill("Delete ticket", lambda: None, bg=(0.98, 0.90, 0.90, 1), fg=RED, height=44)

        def delete_pressed():
            if not armed["on"]:
                armed["on"] = True
                delete.lbl.text = "[b]Tap again to confirm[/b]"
                Clock.schedule_once(lambda dt: reset(), 3)
                return
            self.store.delete(tid)
            self.toast(f"Ticket #{tid} deleted")
            self.drafts.pop(tid, None)
            self.back() if self.history else self.tab("tickets")

        def reset():
            armed["on"] = False
            delete.lbl.text = "[b]Delete ticket[/b]"

        delete.bind(on_release=lambda *_: delete_pressed())
        content.add_widget(delete)
        return scroll

    # ----------------------------------------------------------------- settings
    def page_settings(self):
        scroll, content = self.new_scroll()
        h_name, f_name = text_field("Your name (shown on notes you add)", self.store.settings.get("tech_name", ""))
        h_company, f_company = text_field("Company", self.store.settings.get("company", ""))
        msg = label("", 13, GREEN)

        def save():
            self.store.settings["tech_name"] = f_name.text.strip()
            self.store.settings["company"] = f_company.text.strip()
            self.store.save()
            msg.text = "Saved."

        content.add_widget(card([label("Profile", 12, MUTED, bold=True), h_name, h_company,
                                 pill("Save", save, height=44), msg]))

        def export():
            data = self.store.export_csv()
            Clipboard.copy(data)
            saved = ""
            try:
                folder = os.path.join(os.path.expanduser("~"), "Documents")
                if platform not in ("win", "linux", "macosx") or not os.path.isdir(folder):
                    folder = self.user_data_dir
                path = os.path.join(folder, "helpdesk_tickets.csv")
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(data)
                saved = f" and saved to {path}" if platform in ("win", "linux", "macosx") else ""
            except OSError:
                pass
            self.toast("CSV copied to clipboard" + saved)

        def samples():
            n = self.store.add_samples()
            self.toast(f"Added {n} sample tickets")
            self.tab("dashboard")

        wipe_state = {"on": False}
        wipe = pill("Delete ALL tickets", lambda: None, bg=(0.98, 0.90, 0.90, 1), fg=RED, height=44)

        def wipe_pressed():
            if not wipe_state["on"]:
                wipe_state["on"] = True
                wipe.lbl.text = "[b]Tap again - this cannot be undone[/b]"
                Clock.schedule_once(lambda dt: wipe_reset(), 3)
                return
            self.store.delete_all()
            self.toast("All tickets deleted")
            self.tab("dashboard")

        def wipe_reset():
            wipe_state["on"] = False
            wipe.lbl.text = "[b]Delete ALL tickets[/b]"

        wipe.bind(on_release=lambda *_: wipe_pressed())
        content.add_widget(card([
            label("Data", 12, MUTED, bold=True),
            label(f"{len(self.store.tickets)} tickets stored on this device.", 14, DARK),
            pill("Export tickets (CSV)", export, bg=LIGHT, height=44),
            pill("Load sample tickets", samples, bg=LIGHT, height=44),
            wipe], spacing=8))
        content.add_widget(card([
            label("About", 12, MUTED, bold=True),
            label(f"G-Yeza Helpdesk {VERSION}", 14, DARK),
            label("Tickets are stored only on this device. Each phone or PC has its own list until a shared "
                  "server is added.", 12, MUTED)]))
        return scroll


if __name__ == "__main__":
    HelpdeskApp().run()
