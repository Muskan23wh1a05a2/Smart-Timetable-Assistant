# Architecture Documentation — Student Schedule Assistant

This document explains how the application is structured, how data flows
between components, and how the core scheduling algorithms work.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit UI (app.py)                     │
│  Dashboard | Events | Class Schedule | Assignments | Exams |      │
│  Free Time/Conflicts | Calendar View | AI Assistant | Export      │
└───────────┬───────────────┬───────────────┬───────────────┬─────┘
            │                │               │               │
            ▼                ▼               ▼               ▼
   ┌────────────────┐ ┌─────────────┐ ┌──────────────┐ ┌────────────┐
   │ google_calendar │ │ schedule_   │ │ assignment_  │ │ exam_store │
   │   .py           │ │ store.py    │ │ store.py     │ │   .py      │
   │ (Google Cal API)│ │ (local JSON)│ │ (local JSON) │ │(local JSON)│
   └────────┬────────┘ └─────────────┘ └──────────────┘ └────────────┘
            │
            ▼
   ┌─────────────────────────┐      ┌──────────────────────────┐
   │ conflict_detector.py     │      │ academic_calendar.py      │
   │ - overlap detection       │      │ - semester/term templates │
   │ - free-slot finder        │      │ - holidays/festivals       │
   └──────────────────────────┘      └──────────────────────────┘

   ┌──────────────────────────┐      ┌──────────────────────────┐
   │ agent.py (LangGraph)      │      │ export_utils.py            │
   │ - conversational tools     │      │ - .ics / CSV / text export │
   │ - wraps the modules above  │      └──────────────────────────┘
   └──────────────────────────┘

   ┌──────────────────────────┐      ┌──────────────────────────┐
   │ calendar_view.py          │      │ validators.py / reminder.py│
   │ - month/week/day rendering │      │ - input validation,        │
   └──────────────────────────┘      │   friendly errors, email   │
                                       └──────────────────────────┘
```

Each module has a single responsibility, and `app.py` is purely the
presentation layer — it calls into these modules and renders results.

---

## 2. Data Storage

| Data | Storage | File |
|---|---|---|
| Calendar events | Google Calendar (cloud, via OAuth) | n/a |
| Recurring class schedule | Local JSON | `class_schedule.json` |
| Assignments | Local JSON | `assignments.json` |
| Exams | Local JSON | `exams.json` |
| Academic terms | Local JSON | `academic_terms.json` |
| Holidays/festivals | Local JSON | `academic_holidays.json` |
| OAuth tokens | Local JSON (gitignored) | `token.json` |
| OAuth client secret | Local JSON (gitignored) | `credentials.json` |

Local JSON files are simple, human-readable, and require no database setup —
appropriate for a single-user academic tool. They live in the app's working
directory and are excluded from version control via `.gitignore`.

---

## 3. Google Calendar Integration Flow

1. **Authentication (`google_calendar.get_calendar_service`)**
   - Uses OAuth 2.0 "Desktop App" flow via `google-auth-oauthlib`.
   - First run: opens a browser window for the user to grant calendar access.
   - Subsequent runs: reuses `token.json` (refreshed automatically if expired).
   - Scope requested: `https://www.googleapis.com/auth/calendar` (full
     read/write access to the user's primary calendar).

2. **Reading events (`list_upcoming_events`)**
   - Calls `events().list()` on the `primary` calendar, filtered by `timeMin`,
     sorted by start time, with `singleEvents=True` (expands recurring events
     into individual instances).
   - Cached for 60 seconds in `app.py` (`get_events_safe`) to reduce API calls
     across tabs/reruns — Streamlit reruns the whole script on every interaction.

3. **Writing events (`create_event`, `delete_event`)**
   - `create_event` builds an event body with `start`/`end` in
     `Asia/Kolkata` timezone by default and calls `events().insert()`.
   - `delete_event` calls `events().delete()` by event ID.

4. **Error handling**
   - All Google API calls are wrapped in try/except in `app.py`.
   - `validators.friendly_api_error()` maps common exceptions (expired
     tokens, missing credentials, 403/404/429 errors, network failures) to
     human-readable messages with suggested fixes.

---

## 4. Scheduling Algorithms (`conflict_detector.py`)

### 4.1 Conflict Detection — `find_event_conflicts` / `check_new_event_conflict`
Two time ranges `[start_a, end_a)` and `[start_b, end_b)` are considered
**overlapping** if:

```
start_a < end_b   AND   start_b < end_a
```

- `find_event_conflicts(events)`: parses all event start/end times, sorts
  them, and does a pairwise overlap check (O(n²), fine for the small number
  of events a student has).
- `check_new_event_conflict(new_start, new_end, events, class_schedule)`:
  checks a *proposed* new event against (a) existing Google Calendar events
  and (b) the recurring class schedule for that weekday. Used before creating
  any event (manually or via the AI agent) so conflicts are caught
  proactively rather than after the fact.

### 4.2 Free-Time Finder — `find_free_slots`
For a given day:

1. Define the search window (default 08:00–22:00).
2. Collect all "busy" intervals for that day:
   - Google Calendar events occurring on that date
   - Recurring class sessions whose `days` list includes that weekday
3. Sort and **merge overlapping busy intervals** into a minimal set of
   non-overlapping blocks.
4. Walk through the day from `day_start` to `day_end`, computing the gaps
   *between* busy blocks (and before the first / after the last).
5. Return only gaps ≥ `min_duration_minutes`.

This is the same primitive used by:
- The **Free Time & Conflicts** tab (manual "find free time on date X")
- The **AI Assistant**'s `find_free_time` tool
- The **Exam Study Planner**'s `allocate_study_slots`

### 4.3 Study Time Allocation — `exam_store.allocate_study_slots`
Given an exam with a `study_hours_goal` (e.g. 10 hours) and a window of
`days_before` (e.g. 7 days):

1. Iterate backwards from the day before the exam to `days_before` days prior
   (skipping any days in the past).
2. For each day, call `find_free_slots` (same algorithm as above) with the
   requested `session_length_minutes`.
3. Greedily consume free slots — splitting a slot into one or more
   `session_length_minutes` chunks — until the cumulative allocated minutes
   reach `study_hours_goal * 60`, or all candidate days are exhausted.
4. Return a list of `{date, start, end, course}` suggestions. The UI then
   offers a one-click button to push each suggestion to Google Calendar as a
   "Study: <course>" event (re-checked for conflicts at creation time).

This is a **greedy interval-scheduling heuristic** — it prioritizes the
days closest to the exam first and fills available gaps without trying to
find a globally "optimal" distribution, which keeps the algorithm simple,
fast (no external solver), and predictable for users.

---

## 5. Conversational AI Agent (`agent.py`)

- Built with **LangGraph's `create_react_agent`** (ReAct-style: the LLM
  reasons about which tool to call, calls it, observes the result, and
  repeats until it can answer).
- The LLM (`ChatOpenAI`, e.g. `gpt-4o-mini`) is given a fixed **system prompt**
  describing its role, today's date, and tool-usage rules (e.g. "always check
  conflicts before creating an event").
- **Tools exposed to the agent** are thin wrappers around the same modules
  used by the UI (`google_calendar`, `schedule_store`, `assignment_store`,
  `exam_store`, `conflict_detector`, `academic_calendar`) — this guarantees
  the AI agent and the manual UI always produce consistent results, since
  they share the same underlying logic.
- Each user message is sent as `{"messages": [{"role": "user", "content": ...}]}`;
  the graph returns a `messages` list, and the last message's `.content` is
  shown to the user.
- Chat history is kept in `st.session_state` for the current session only
  (not persisted to disk).

---

## 6. Privacy & Data Protection

- **No third-party data sharing**: all data (class schedule, assignments,
  exams, term/holiday config) is stored in local JSON files on the user's own
  machine — never sent to any server other than Google (for calendar data)
  and OpenAI (only the text of chat messages, if the AI Assistant is used).
- **Credentials never committed**: `credentials.json` (OAuth client secret),
  `token.json` (OAuth access/refresh tokens), and all `*.json` data files are
  listed in `.gitignore` and must never be pushed to GitHub.
- **OpenAI API key**: entered per-session in the UI (password-masked input),
  stored only in `st.session_state` (in-memory), never written to disk or logs.
- **Email reminders**: Gmail credentials (address + App Password) are entered
  per-session in the UI, used only to open a single SMTP connection via
  `smtplib`, and are not persisted.
- **Minimal OAuth scope**: only the `calendar` scope is requested — no Gmail,
  Drive, or profile data access is requested via OAuth.
- **Local-first design**: the app can run entirely offline except for the
  Google Calendar sync and (optional) AI Assistant / email features — so a
  user who only wants the class schedule, assignment tracker, and exam
  planner needs no external accounts at all.

---

## 7. Request/Response Flow Example: "Schedule a study session for Friday 4-6pm"

1. User types the request in the **AI Assistant** chat.
2. `validators.validate_natural_language_request()` checks the input isn't
   empty/too long.
3. The LangGraph agent receives the message, reasons that it needs to create
   a calendar event, and calls the `create_calendar_event` tool with
   `start_datetime="2026-06-19T16:00:00"`, `end_datetime="2026-06-19T18:00:00"`.
4. Inside the tool:
   - `list_upcoming_events()` fetches current events.
   - `check_new_event_conflict()` checks against events + class schedule.
   - If a conflict exists, the tool returns a warning string (no event
     created) and the agent relays this to the user, asking how to proceed.
   - If no conflict, `create_event()` calls the Google Calendar API and
     returns success.
5. The agent's final response is shown in the chat, and `st.cache_data` is
   cleared so the **Dashboard** / **Calendar View** / **Upcoming Events**
   tabs reflect the new event on next render.
