"""Ticket data layer for G-Yeza Helpdesk.

Pure Python (no Kivy) so it works the same on desktop and Android and can be
tested on its own. All data lives in one JSON file written atomically.
"""
import csv
import io
import json
import os
from datetime import datetime, timedelta

STATUSES = ("Open", "In Progress", "On Hold", "Resolved", "Closed")
ACTIVE = ("Open", "In Progress", "On Hold")
PRIORITIES = ("Low", "Medium", "High", "Urgent")
CATEGORIES = ("Hardware", "Software", "Network", "Account / Access", "Email", "Printer", "Other")
SLA_HOURS = {"Urgent": 4, "High": 8, "Medium": 24, "Low": 72}
STAMP = "%Y-%m-%d %H:%M"
EDITABLE = ("status", "priority", "category", "assignee")


def now():
    return datetime.now()


def stamp(dt=None):
    return (dt or now()).strftime(STAMP)


def parse_stamp(text):
    try:
        return datetime.strptime(str(text).strip(), STAMP)
    except (ValueError, TypeError):
        return None


def span_text(delta):
    """'2h 10m', '3d 4h', '35m' for a timedelta (absolute value)."""
    minutes = int(abs(delta.total_seconds()) // 60)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"


class Store:
    def __init__(self, path):
        self.path = path
        self.data = self._blank()
        self.load()

    # ------------------------------------------------------------ persistence
    @staticmethod
    def _blank():
        return {"version": 1, "next_id": 1001,
                "settings": {"tech_name": "", "company": "G-Yeza Data Solutions"},
                "tickets": []}

    def load(self):
        data = self._blank()
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
            if isinstance(saved, dict):
                if isinstance(saved.get("settings"), dict):
                    data["settings"].update(saved["settings"])
                if isinstance(saved.get("tickets"), list):
                    data["tickets"] = [t for t in saved["tickets"] if isinstance(t, dict) and isinstance(t.get("id"), int)]
                if isinstance(saved.get("next_id"), int):
                    data["next_id"] = saved["next_id"]
        except (OSError, ValueError):
            pass
        top = max((t["id"] for t in data["tickets"]), default=1000)
        data["next_id"] = max(data["next_id"], top + 1)
        self.data = data

    def save(self):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=1)
        os.replace(tmp, self.path)

    # --------------------------------------------------------------- settings
    @property
    def settings(self):
        return self.data["settings"]

    @property
    def tickets(self):
        return self.data["tickets"]

    def who(self):
        return self.settings.get("tech_name", "").strip() or "Technician"

    # ---------------------------------------------------------------- tickets
    def get(self, tid):
        for t in self.tickets:
            if t["id"] == tid:
                return t
        return None

    @staticmethod
    def due_for(priority, start=None):
        return stamp((start or now()) + timedelta(hours=SLA_HOURS.get(priority, 24)))

    def _log(self, t, kind, text, who=None):
        t["log"].append({"when": stamp(), "who": who or self.who(), "kind": kind, "text": text})
        t["updated"] = stamp()

    def create(self, title, requester, contact="", category="Other", priority="Medium",
               assignee="", description=""):
        title, requester = str(title).strip(), str(requester).strip()
        if not title:
            raise ValueError("Title is required.")
        if not requester:
            raise ValueError("Requester name is required.")
        if category not in CATEGORIES:
            category = "Other"
        if priority not in PRIORITIES:
            priority = "Medium"
        created = now()
        t = {"id": self.data["next_id"], "title": title, "description": str(description).strip(),
             "requester": requester, "contact": str(contact).strip(), "category": category,
             "priority": priority, "status": "Open", "assignee": str(assignee).strip(),
             "created": stamp(created), "updated": stamp(created),
             "due": self.due_for(priority, created), "resolved": "", "log": []}
        self.data["next_id"] += 1
        self._log(t, "created", "Ticket created")
        self.tickets.append(t)
        self.save()
        return t

    def set_field(self, tid, field, value):
        """Change status / priority / category / assignee and record it in the log."""
        t = self.get(tid)
        if t is None or field not in EDITABLE:
            return False
        value = str(value).strip()
        if field == "status" and value not in STATUSES:
            return False
        if field == "priority" and value not in PRIORITIES:
            return False
        if field == "category" and value not in CATEGORIES:
            return False
        old = t.get(field, "")
        if old == value:
            return False
        t[field] = value
        label = field.capitalize()
        self._log(t, field, f"{label}: {old or 'none'} -> {value or 'none'}")
        if field == "priority" and t["status"] in ACTIVE:
            t["due"] = self.due_for(value, parse_stamp(t["created"]))
        if field == "status":
            if value in ("Resolved", "Closed"):
                t["resolved"] = t["resolved"] or stamp()
            else:
                t["resolved"] = ""
        self.save()
        return True

    def add_comment(self, tid, text):
        t = self.get(tid)
        text = str(text).strip()
        if t is None or not text:
            return False
        self._log(t, "comment", text)
        self.save()
        return True

    def delete(self, tid):
        t = self.get(tid)
        if t is None:
            return False
        self.tickets.remove(t)
        self.save()
        return True

    def delete_all(self):
        self.data["tickets"] = []
        self.save()

    # ----------------------------------------------------------------- queries
    def is_overdue(self, t):
        due = parse_stamp(t.get("due"))
        return t.get("status") in ACTIVE and due is not None and due < now()

    def due_text(self, t):
        if t.get("status") not in ACTIVE:
            return "Resolved " + t["resolved"] if t.get("resolved") else t.get("status", "")
        due = parse_stamp(t.get("due"))
        if due is None:
            return ""
        delta = due - now()
        if delta.total_seconds() < 0:
            return f"Overdue by {span_text(delta)}"
        return f"Due in {span_text(delta)}"

    def query(self, status="All", text="", mine=False):
        """status: All, Active, one of STATUSES, or Overdue."""
        text = str(text).strip().lower().lstrip("#")
        me = self.settings.get("tech_name", "").strip().lower()
        out = []
        for t in self.tickets:
            if status == "Active" and t["status"] not in ACTIVE:
                continue
            if status == "Overdue" and not self.is_overdue(t):
                continue
            if status in STATUSES and t["status"] != status:
                continue
            if mine and (not me or t.get("assignee", "").strip().lower() != me):
                continue
            if text:
                hay = " ".join([str(t["id"]), t["title"], t["requester"], t.get("contact", ""),
                                t["category"], t.get("assignee", ""), t.get("description", "")]).lower()
                if text not in hay:
                    continue
            out.append(t)
        out.sort(key=lambda t: t.get("updated", ""), reverse=True)
        return out

    def counts(self):
        today = now().strftime("%Y-%m-%d")
        c = {s: 0 for s in STATUSES}
        c["Overdue"] = c["Unassigned"] = c["Resolved today"] = 0
        for t in self.tickets:
            c[t["status"]] = c.get(t["status"], 0) + 1
            if self.is_overdue(t):
                c["Overdue"] += 1
            if t["status"] in ACTIVE and not t.get("assignee", "").strip():
                c["Unassigned"] += 1
            if t["status"] in ("Resolved", "Closed") and str(t.get("resolved", "")).startswith(today):
                c["Resolved today"] += 1
        return c

    def attention(self, limit=5):
        """Overdue first, then Urgent/High active tickets."""
        hot = [t for t in self.tickets if t["status"] in ACTIVE and (self.is_overdue(t) or t["priority"] in ("Urgent", "High"))]
        hot.sort(key=lambda t: (not self.is_overdue(t), -PRIORITIES.index(t["priority"]), t["created"]))
        return hot[:limit]

    # ------------------------------------------------------------------ export
    def export_csv(self):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ID", "Title", "Status", "Priority", "Category", "Requester", "Contact",
                    "Assignee", "Created", "Updated", "Due", "Resolved", "Description"])
        for t in sorted(self.tickets, key=lambda t: t["id"]):
            w.writerow([t["id"], t["title"], t["status"], t["priority"], t["category"], t["requester"],
                        t.get("contact", ""), t.get("assignee", ""), t["created"], t["updated"],
                        t["due"], t.get("resolved", ""), t.get("description", "")])
        return buf.getvalue()

    def add_samples(self):
        me = self.settings.get("tech_name", "").strip()
        samples = [
            ("Cannot connect to office Wi-Fi", "Thandi Mokoena", "thandi@example.co.za", "Network", "High", me,
             "Laptop shows 'limited connectivity' since this morning. Other devices are fine."),
            ("Printer on 2nd floor jams every page", "Sipho Dlamini", "031 555 0142", "Printer", "Medium", "",
             "Paper tray was replaced yesterday. Error code E-04."),
            ("Reset password for payroll system", "Anele Naidoo", "anele@example.co.za", "Account / Access", "Urgent", me,
             "Locked out ahead of month-end payroll run."),
            ("Install Microsoft Office on new laptop", "Lerato Khumalo", "lerato@example.co.za", "Software", "Low", "",
             "New starter on Monday."),
            ("Outlook keeps asking for password", "Pieter van Wyk", "pieter@example.co.za", "Email", "Medium", me,
             "Happens every few minutes since the password change."),
        ]
        for title, req, contact, cat, pri, who, desc in samples:
            self.create(title, req, contact, cat, pri, who, desc)
        # make a couple of them look "lived in"
        if len(self.tickets) >= 3:
            self.set_field(self.tickets[-3]["id"], "status", "In Progress")
        if len(self.tickets) >= 1:
            self.add_comment(self.tickets[-1]["id"], "Requested remote access details from the user.")
        return len(samples)
