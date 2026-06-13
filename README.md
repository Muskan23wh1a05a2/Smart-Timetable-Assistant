# 🗓️ Student Schedule Assistant — Track A (Week 1-2)

An AI-powered calendar management assistant for students. This is the
**Foundation & Quick Win** milestone: basic Google Calendar integration,
event creation/viewing, and recurring class schedule management, all in a
Streamlit dashboard.

---

## ✅ Week 1-2 Checklist (Track A)

- [x] GitHub repo with scheduling project structure
- [x] Development environment setup (Python, Streamlit, Google Calendar API)
- [x] Google Calendar connection & authentication
- [x] Event creation and viewing functionality
- [x] Class schedule input and local storage
- [x] Calendar display in Streamlit interface
- [ ] Deploy on Streamlit Cloud *(steps below — you do this part)*
- [ ] Record 2-minute demo *(tips below)*

---

## 📁 Project Structure

```
student-calendar-agent/
├── app.py                  # Main Streamlit app (UI + tabs)
├── google_calendar.py      # Google Calendar API auth + CRUD helpers
├── schedule_store.py        # Local JSON storage for class schedule
├── requirements.txt         # Python dependencies
├── .gitignore               # Keeps credentials/tokens out of git
├── .streamlit/
│   └── config.toml          # Streamlit theme config
└── README.md                 # This file
```

---

## 1. Create the GitHub Repo

```bash
git init
git add .
git commit -m "Week 1-2: Foundation - calendar integration + class schedule"
git branch -M main
git remote add origin https://github.com/<Muskan23wh1a05a2>/student-calendar-agent.git
git push -u origin main
```

---

## 2. Set Up Your Development Environment

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Get Google Calendar API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Go to **APIs & Services → Library**, search for **Google Calendar API**, and click **Enable**.
4. Go to **APIs & Services → OAuth consent screen**:
   - Choose "External" (unless you have a Workspace account).
   - Fill in the required app info (app name, support email).
   - Add your own Google account as a **test user**.
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   - Application type: **Desktop app**
   - Name it anything, e.g. "Student Calendar Assistant"
6. Download the JSON file, rename it to `credentials.json`, and place it in
   the project root folder (same level as `app.py`).

> ⚠️ `credentials.json` and `token.json` are in `.gitignore` — never commit
> these files to GitHub.

---

## 4. Run the App Locally

```bash
streamlit run app.py
```

- Click **"🔗 Connect to Google Calendar"** in the sidebar.
- A browser window will open asking you to log in and grant calendar access.
- After approval, a `token.json` file is created automatically so future runs
  won't need re-authentication.

---

## 5. Using the App

### Tab 1 — Upcoming Events
View your next 20 upcoming Google Calendar events in a table, with the
option to delete any of them.

### Tab 2 — Add Event
Create a new event directly on your Google Calendar (title, description,
location, date/time range).

### Tab 3 — Class Schedule
Add your recurring weekly classes (course name, instructor, days, time,
room). This is stored locally in `class_schedule.json` and will be used in
later weeks for conflict detection and automated scheduling.

---

## 6. Deploy on Streamlit Cloud

1. Push your code to GitHub (without `credentials.json` / `token.json`).
2. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Click **"New app"**, select your repo, branch (`main`), and main file (`app.py`).
4. **Important:** Since this app uses OAuth with a local browser flow
   (`run_local_server`), the Google sign-in won't work the same way on
   Streamlit Cloud. For the Week 1-2 demo, two options:
   - **Recommended for the milestone demo:** run the app **locally** and
     record your demo there — this satisfies "working deployed demo" for
     many course rubrics if you also deploy a static/limited version to
     Streamlit Cloud showing the UI (Class Schedule tab works fully online
     since it doesn't need Google auth).
   - **For a fully cloud-working version:** switch to a **Service Account**
     or implement the OAuth **web flow** with a redirect URI — this is a
     good Week 3-4 enhancement.
5. Add a `secrets.toml` (via Streamlit Cloud's "Secrets" settings) if you
   later store API keys there.

---

## 7. Recording Your 2-Minute Demo

Suggested flow:
1. (0:00–0:20) Briefly introduce the project: "Student Schedule Assistant —
   helps students manage classes, assignments, and calendar events."
2. (0:20–0:50) Show the **Class Schedule** tab: add a class, show it appear
   in the table.
3. (0:50–1:30) Show the **Connect to Google Calendar** button, then the
   **Upcoming Events** tab populating with real calendar data.
4. (1:30–2:00) Show **Add Event** — create an event and confirm it appears
   on your actual Google Calendar (switch to calendar.google.com briefly).

---

## 🔜 Next Steps (Week 3+)

- Conflict detection between class schedule and calendar events
- Natural language input via LangChain agent ("Schedule study time for my
  Database exam on Friday")
- Reminder/notification system (email or WhatsApp)
- Assignment deadline tracking

---

## 🚀 Week 3-4: Conversational Scheduling Agent

New features added this milestone:

- **conflict_detector.py** — detects overlapping events, checks new events
  against your class schedule, and finds free time slots
- **assignment_store.py** — local JSON tracker for assignment deadlines
- **reminder.py** — sends email reminders via Gmail SMTP
- **agent.py** — LangChain conversational agent with tools for scheduling,
  conflict checking, free-time finding, and assignment management

### New Tabs in the App
- **📝 Assignments** — add/track deadlines, see what's due in the next 14 days,
  send email reminders
- **🔍 Free Time & Conflicts** — pick a date and find open time slots; view
  all detected conflicts
- **🤖 AI Assistant** — chat naturally: "Find free time tomorrow afternoon",
  "Schedule study session Friday 4-6pm", "Add assignment: DBMS report due
  next Monday"

### Setup for AI Assistant
1. Get an OpenAI API key from https://platform.openai.com/api-keys
2. Paste it into the "OpenAI API Key" field in the AI Assistant tab
   (it's only stored for your current session, not saved to disk)

### Setup for Email Reminders
1. Use a Gmail account with 2-Step Verification enabled
2. Create an App Password: https://myaccount.google.com/apppasswords
3. Enter your Gmail address + app password in the Assignments tab's
   "Send Email Reminder" section

### Install new dependencies
```bash
pip install -r requirements.txt
```

### Updated Checklist
- [x] Integrate calendar management + conflict detection tools
- [x] Natural language scheduling via LangChain agent
- [x] Conflict detection for overlapping events
- [x] Assignment deadline tracking
- [x] "Find free time" queries
- [x] Email reminder system
- [ ] Milestone demo: agent schedules events and detects conflicts (record this!)

---

## 🎓 Week 5-6: Domain Specialization — Academic Schedule Manager (Option A1)

New features added this milestone:

- **schedule_store.py** — class sessions now have a `session_type`
  (Lecture / Lab / Tutorial / Seminar), so the same course can have
  multiple timetable entries
- **assignment_store.py** — assignments now have a `priority` level
  (Low / Medium / High / Critical); upcoming deadlines can be sorted by priority
- **exam_store.py** — track exams (date, time, duration, location, priority,
  study hours goal) and auto-suggest study time slots in free periods before
  each exam
- **academic_calendar.py** — semester/term templates (start/end dates, exam
  periods, semester breaks) + a pre-loaded list of common Indian national
  holidays/festivals (editable)

### New Tabs
- **🎓 Exams & Study Planner** — add exams, see countdown to each, and generate
  a study schedule that avoids conflicts with your classes/calendar (with a
  button to push study sessions straight to Google Calendar)
- **🇮🇳 Academic Calendar** — add your semester/term dates (with exam period
  and semester break ranges) and manage holidays/festivals; shows which term
  is currently active

### AI Assistant — New Capabilities
The chat agent can now also:
- Add exams and suggest study plans ("Suggest a study plan for my DBMS exam")
- List upcoming exams, assignments (with priority), and festivals
- Report the currently active semester/term
- Set priority levels when adding assignments

### Updated Checklist (Option A1)
- [x] Semester/term-based schedule templates
- [x] Course-specific scheduling (lectures, labs, tutorials)
- [x] Exam schedule management with study time allocation
- [x] Assignment deadline tracking with priority levels
- [x] Indian academic calendar (semester breaks, festivals)

---

## 🏁 Week 7-8: Polish & Production

New modules added this milestone:

- **calendar_view.py** — renders Monthly, Weekly, and Daily calendar views
  (combining Google Calendar events + recurring class schedule)
- **validators.py** — input validation for events, classes, assignments, exams,
  date ranges, and AI chat requests; plus `friendly_api_error()` for
  human-readable error messages on API/network failures
- **export_utils.py** — generates `.ics` calendar files (importable into Google
  Calendar/Outlook/Apple Calendar), CSV schedule reports, and plain-text summaries

### New Tabs
- **🏠 Dashboard** — at-a-glance view of next events, assignment deadlines
  (with "DUE SOON" warnings), upcoming exams, conflict resolution panel, and
  upcoming festivals/holidays
- **🗂️ Calendar View** — switch between Monthly, Weekly, and Daily perspectives
- **⬇️ Export** — download `.ics` calendar file, CSV report, or text summary

### Validation & Error Handling
- All forms (events, classes, assignments, exams, terms) now validate input
  before saving (e.g. end time after start time, no past due dates, required
  fields) and show clear inline error messages
- API failures (expired Google token, missing credentials, rate limits,
  network issues, invalid OpenAI key, email auth errors) now show friendly,
  actionable messages instead of raw stack traces
- Google Calendar event fetches are cached for 60 seconds (`get_events_safe`)
  to reduce API calls across tabs

### Updated Checklist
- [x] Clean calendar view (monthly/weekly/daily) — **Calendar View tab**
- [x] Schedule management dashboard with upcoming events — **Dashboard tab**
- [x] Assignment tracker with deadline notifications — **Dashboard + Assignments tab**
- [x] Simple conflict resolution interface — **Dashboard "Conflict Resolution" panel**
- [x] Export functionality (.ics, CSV, text report) — **Export tab**
- [x] Input validation for scheduling requests and events
- [x] Friendly error messages for API failures and conflicts
- [ ] Final demo video (5-7 min) — record this covering: Dashboard → Calendar
      View (monthly/weekly/daily) → Add Event with conflict detection →
      Assignments/Exams with priorities → AI Assistant chat → Export to .ics
- [ ] Milestone: Production-ready academic scheduling application 🎉
