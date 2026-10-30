# G-Yeza Helpdesk

IT help-desk ticketing for desktop (Windows/Linux/macOS) and Android, built with Kivy + KivyMD
in the G-Yeza colours (#106098 and #3192c7).

## What works now (version 1.0)
- Log a ticket: title, requester, contact, category, priority, assignee, description
- Ticket numbers (#1001, #1002 ...) and an automatic due time from priority (Urgent 4h, High 8h, Medium 24h, Low 72h)
- Statuses: Open, In Progress, On Hold, Resolved, Closed - change them with one tap, reopen when needed
- Notes and an activity log on every ticket (who changed what, and when)
- Dashboard: counts for open / in progress / overdue / on hold / unassigned / resolved today, plus "needs attention"
- Search and filters (Active, All, each status, Overdue, Mine)
- Export all tickets to CSV (copied to the clipboard; on desktop also saved to Documents)
- Works fully offline. Data is one JSON file in the app's private folder.

## Files
| File | Purpose |
|---|---|
| `main.py` | The screens (Kivy / KivyMD 2.x) |
| `gyeza_store.py` | Ticket logic and storage - no Kivy, easy to test |
| `buildozer.spec` | Android build settings |
| `.github/workflows/build_apk.yml` | Builds the signed APK on GitHub |
| `.github/workflows/Build_exe.yml` | Builds the Windows .exe on GitHub |

## Run on your computer
```
pip install -r requirements.txt
python main.py
```

## Build the apps
Push to `main` (or run the workflow by hand from the Actions tab). The APK and the EXE appear
under "Artifacts" on the finished run. After the first APK build, commit the generated
`android/debug.keystore` so later builds keep the same signature and install as updates.

## Important limitation
Tickets are stored on each device separately. Two technicians on two phones will NOT see the same
list until a shared server (e.g. Firebase) is added - that is the next step.
