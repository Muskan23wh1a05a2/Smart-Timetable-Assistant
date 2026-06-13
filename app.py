"""
app.py
------
Student Schedule Assistant - Production-Ready Academic Scheduling App
(Track A, Weeks 1-8)

Features:
- Connect & authenticate with Google Calendar
- Dashboard with upcoming events, assignments, exams overview
- Monthly/Weekly/Daily calendar views
- Create/view/delete calendar events with input validation
- Recurring class schedule (lectures, labs, tutorials)
- Assignment deadline tracker with priority levels
- Exam schedule + automated study time allocation
- Conflict detection & free time finder
- AI conversational scheduling assistant (LangChain)
- Indian academic calendar (terms, breaks, festivals)
- Export to .ics calendar file and CSV/text reports
- Friendly error handling for API/network failures

Run with:
    streamlit run app.py
"""

import datetime
import streamlit as st
import pandas as pd

from google_calendar import get_calendar_service, list_upcoming_events, create_event, delete_event
from schedule_store import load_schedule, save_schedule, add_class, remove_class, SESSION_TYPES, get_courses
from conflict_detector import find_event_conflicts, check_new_event_conflict, find_free_slots
from assignment_store import (
    load_assignments, add_assignment, remove_assignment,
    toggle_completed, get_upcoming_assignments, PRIORITY_LEVELS
)
from reminder import send_email_reminder, build_assignment_reminder_body, build_event_reminder_body
from exam_store import load_exams, add_exam, remove_exam, get_upcoming_exams, allocate_study_slots
from academic_calendar import (
    load_terms, add_term, remove_term, get_active_term,
    load_holidays, add_holiday, remove_holiday, get_upcoming_holidays
)
from validators import (
    validate_event_input, validate_class_session, validate_assignment,
    validate_exam, validate_date_range, validate_natural_language_request,
    friendly_api_error
)
from export_utils import generate_ics, generate_csv_report, generate_text_summary
from calendar_view import render_month_view, render_week_view, render_day_view

st.set_page_config(page_title="Student Schedule Assistant", page_icon="🗓️", layout="wide")

st.title("🗓️ Student Schedule Assistant")
st.caption("Production-ready academic scheduling assistant: calendar sync, conflict detection, "
           "exam study planning, and an AI scheduling agent.")

# ----------------------------------------------------------------------
# Sidebar: Google Calendar Connection
# ----------------------------------------------------------------------
st.sidebar.header("Google Calendar")

if "service" not in st.session_state:
    st.session_state.service = None

if st.sidebar.button("🔗 Connect to Google Calendar"):
    try:
        st.session_state.service = get_calendar_service()
        st.sidebar.success("Connected to Google Calendar!")
    except FileNotFoundError as e:
        st.sidebar.error(friendly_api_error("Google Calendar", e))
    except Exception as e:
        st.sidebar.error(friendly_api_error("Google Calendar", e))

if st.session_state.service:
    st.sidebar.success("✅ Calendar connected")
else:
    st.sidebar.info("Not connected yet. Click the button above and follow the README setup steps.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Setup help:** see `README.md` for how to get your `credentials.json` "
    "from Google Cloud Console."
)

with st.sidebar.expander("🔒 Privacy & Data"):
    st.markdown(
        "- All schedule/assignment/exam data is stored **locally** on this "
        "device (JSON files), never uploaded anywhere.\n"
        "- Google Calendar access uses OAuth with the **calendar scope only** "
        "(no email, contacts, or Drive access).\n"
        "- Your OpenAI API key and Gmail App Password are kept **in-memory "
        "for this session only** — never written to disk or logs.\n"
        "- `credentials.json` and `token.json` are excluded from git via "
        "`.gitignore` and must never be shared or committed."
    )


@st.cache_data(ttl=60)
def _cached_upcoming_events(_service_id, max_results=100):
    """Cache events for 60s to avoid hammering the API across tabs/reruns."""
    time_min = datetime.datetime.utcnow().isoformat() + "Z"
    return list_upcoming_events(st.session_state.service, max_results=max_results, time_min=time_min)


def get_events_safe(max_results=100):
    """Fetches upcoming events with friendly error handling. Returns [] on failure."""
    if not st.session_state.service:
        return []
    try:
        return _cached_upcoming_events(id(st.session_state.service), max_results=max_results)
    except Exception as e:
        st.error(friendly_api_error("Google Calendar", e))
        return []


# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🏠 Dashboard", "📅 Upcoming Events", "➕ Add Event", "📚 Class Schedule",
    "📝 Assignments", "🔍 Free Time & Conflicts", "🤖 AI Assistant",
    "🎓 Exams & Study Planner", "🇮🇳 Academic Calendar",
    "🗂️ Calendar View", "⬇️ Export"
])

# ----------------------------------------------------------------------
# Tab 0: Dashboard
# ----------------------------------------------------------------------
with tab0:
    st.subheader("🏠 Dashboard")

    active_term = get_active_term()
    if active_term:
        st.info(f"📌 Current term: **{active_term['name']}** "
                f"({active_term['start_date']} → {active_term['end_date']})")

    col1, col2, col3 = st.columns(3)

    # --- Upcoming events ---
    with col1:
        st.markdown("#### 📅 Next Events")
        if not st.session_state.service:
            st.warning("Connect Google Calendar to see events.")
        else:
            events = get_events_safe(max_results=10)
            if events:
                for e in events[:5]:
                    start = e["start"].get("dateTime", e["start"].get("date"))
                    st.markdown(f"- **{e.get('summary','(No title)')}** — {start}")
            else:
                st.info("No upcoming events.")

    # --- Assignments with deadline notifications ---
    with col2:
        st.markdown("#### 📝 Assignment Deadlines")
        upcoming_assignments = get_upcoming_assignments(days_ahead=7, sort_by_priority=True)
        if upcoming_assignments:
            priority_emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
            for a in upcoming_assignments[:5]:
                due_dt = datetime.datetime.strptime(f"{a['due_date']} {a.get('due_time','23:59')}", "%Y-%m-%d %H:%M")
                hours_left = (due_dt - datetime.datetime.now()).total_seconds() / 3600
                emoji = priority_emoji.get(a.get("priority", "Medium"), "🟡")
                urgency = " ⏰ **DUE SOON**" if hours_left < 24 else ""
                st.markdown(f"- {emoji} **{a['title']}** ({a['course']}) — {a['due_date']}{urgency}")
        else:
            st.success("No assignments due in the next 7 days! 🎉")

    # --- Exams ---
    with col3:
        st.markdown("#### 🎓 Upcoming Exams")
        upcoming_exams = get_upcoming_exams(days_ahead=30)
        if upcoming_exams:
            for e in upcoming_exams[:5]:
                days_left = (datetime.datetime.strptime(e["exam_date"], "%Y-%m-%d").date() - datetime.date.today()).days
                st.markdown(f"- **{e['course']}** — {e['exam_date']} ({days_left}d left)")
        else:
            st.info("No exams in the next 30 days.")

    st.markdown("---")

    # --- Conflict summary ---
    st.markdown("#### ⚠️ Conflict Resolution")
    if not st.session_state.service:
        st.warning("Connect Google Calendar to check for conflicts.")
    else:
        events = get_events_safe(max_results=50)
        conflicts = find_event_conflicts(events)
        if conflicts:
            st.error(f"{len(conflicts)} conflict(s) found among your upcoming events:")
            for i, c in enumerate(conflicts):
                with st.expander(f"Conflict {i+1}: {c['event1']} ↔ {c['event2']}"):
                    st.markdown(f"- **{c['event1']}**: {c['event1_time']}")
                    st.markdown(f"- **{c['event2']}**: {c['event2_time']}")
                    st.caption("Go to the 'Upcoming Events' tab to delete or the 'Add Event' tab "
                               "to reschedule one of these.")
        else:
            st.success("✅ No conflicts detected.")

    st.markdown("---")
    st.markdown("#### 🎉 Upcoming Holidays / Festivals")
    holidays = get_upcoming_holidays(days_ahead=14)
    if holidays:
        st.write(", ".join(f"{h['name']} ({h['date']})" for h in holidays))
    else:
        st.caption("None in the next 14 days.")

# ----------------------------------------------------------------------
# Tab 1: Upcoming Events
# ----------------------------------------------------------------------
with tab1:
    st.subheader("Upcoming Google Calendar Events")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar to see your events.")
    else:
        if st.button("🔄 Refresh Events"):
            st.cache_data.clear()
            st.rerun()

        try:
            events = get_events_safe(max_results=20)
            if not events:
                st.info("No upcoming events found.")
            else:
                rows = []
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    rows.append({
                        "Event": event.get("summary", "(No title)"),
                        "Start": start,
                        "Location": event.get("location", ""),
                        "Event ID": event["id"],
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df.drop(columns=["Event ID"]), use_container_width=True)

                # Conflict detection
                conflicts = find_event_conflicts(events)
                if conflicts:
                    st.warning(f"⚠️ {len(conflicts)} scheduling conflict(s) detected!")
                    for c in conflicts:
                        st.markdown(
                            f"- **{c['event1']}** ({c['event1_time']}) overlaps with "
                            f"**{c['event2']}** ({c['event2_time']})"
                        )
                else:
                    st.success("✅ No conflicts detected among your upcoming events.")

                st.markdown("#### Delete an event")
                event_options = {f"{r['Event']} ({r['Start']})": r["Event ID"] for r in rows}
                selected = st.selectbox("Select event to delete", options=["-- none --"] + list(event_options.keys()))
                if selected != "-- none --":
                    if st.button("🗑️ Delete selected event"):
                        try:
                            delete_event(st.session_state.service, event_options[selected])
                            st.success("Event deleted!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(friendly_api_error("Google Calendar", e))
        except Exception as e:
            st.error(friendly_api_error("Google Calendar", e))

# ----------------------------------------------------------------------
# Tab 2: Add Event
# ----------------------------------------------------------------------
with tab2:
    st.subheader("Create a New Calendar Event")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar to create events.")
    else:
        with st.form("add_event_form"):
            summary = st.text_input("Event Title", placeholder="e.g. Database Systems Assignment Due")
            description = st.text_area("Description (optional)")
            location = st.text_input("Location (optional)", placeholder="e.g. Room 204 / Online")

            col1, col2 = st.columns(2)
            with col1:
                event_date = st.date_input("Date", value=datetime.date.today())
                start_time = st.time_input("Start Time", value=datetime.time(9, 0))
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today())
                end_time = st.time_input("End Time", value=datetime.time(10, 0))

            submitted = st.form_submit_button("➕ Add to Google Calendar")

            if submitted:
                start_dt = datetime.datetime.combine(event_date, start_time)
                end_dt = datetime.datetime.combine(end_date, end_time)

                is_valid, error_msg = validate_event_input(summary, start_dt, end_dt)
                if not is_valid:
                    st.error(error_msg)
                else:
                    # Check for conflicts before creating
                    try:
                        existing_events = get_events_safe(max_results=50)
                        class_schedule = load_schedule()
                        conflicts = check_new_event_conflict(start_dt, end_dt, existing_events, class_schedule)
                    except Exception as e:
                        conflicts = []
                        st.warning(friendly_api_error("Google Calendar", e))

                    proceed = True
                    if conflicts:
                        st.warning("⚠️ Potential conflict(s) detected:")
                        for c in conflicts:
                            st.markdown(f"- {c}")
                        proceed = st.checkbox("Create anyway despite conflict", key="force_create")

                    if not proceed:
                        st.info("Event not created. Check the box above to create it anyway, "
                                "or change the date/time and resubmit.")
                    else:
                        try:
                            create_event(
                                st.session_state.service,
                                summary=summary,
                                start_datetime=start_dt,
                                end_datetime=end_dt,
                                description=description,
                                location=location,
                            )
                            st.success(f"Event '{summary}' added to your Google Calendar!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(friendly_api_error("Google Calendar", e))

# ----------------------------------------------------------------------
# Tab 3: Class Schedule (local storage)
# ----------------------------------------------------------------------
with tab3:
    st.subheader("Your Recurring Class Schedule")
    st.caption("Stored locally in `class_schedule.json`. Each course can have multiple "
               "sessions (Lecture, Lab, Tutorial, Seminar) with different timings.")

    schedule = load_schedule()

    if schedule:
        df = pd.DataFrame(schedule)
        df["days"] = df["days"].apply(lambda d: ", ".join(d))
        # reorder columns nicely
        cols = ["course_name", "session_type", "days", "start_time", "end_time", "instructor", "location"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)

        st.markdown("#### Remove a session")
        options = [
            f"{i}: {c['course_name']} [{c.get('session_type','Lecture')}] "
            f"({', '.join(c['days'])} {c['start_time']}-{c['end_time']})"
            for i, c in enumerate(schedule)
        ]
        selected = st.selectbox("Select session to remove", options=["-- none --"] + options)
        if selected != "-- none --":
            idx = int(selected.split(":")[0])
            if st.button("🗑️ Remove session"):
                remove_class(idx)
                st.success("Session removed!")
                st.rerun()
    else:
        st.info("No classes added yet. Use the form below to add your first session.")

    st.markdown("---")
    st.markdown("#### Add a Class Session")
    st.caption("Add separate entries for Lecture, Lab, and Tutorial sessions of the same course "
               "if they happen at different times.")
    with st.form("add_class_form"):
        course_name = st.text_input("Course Name", placeholder="e.g. Data Structures")
        session_type = st.selectbox("Session Type", SESSION_TYPES)
        instructor = st.text_input("Instructor (optional)", placeholder="e.g. Dr. Sharma")
        days = st.multiselect("Days of the Week", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time", value=datetime.time(9, 0), key="class_start")
        with col2:
            end_time = st.time_input("End Time", value=datetime.time(10, 0), key="class_end")
        location = st.text_input("Room / Location (optional)", placeholder="e.g. Room 204 / Lab 3")

        submitted = st.form_submit_button("➕ Add Session")
        if submitted:
            is_valid, error_msg = validate_class_session(course_name, days, start_time, end_time)
            if not is_valid:
                st.error(error_msg)
            else:
                add_class(
                    course_name=course_name,
                    instructor=instructor,
                    days=days,
                    start_time=start_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    location=location,
                    session_type=session_type,
                )
                st.success(f"Added {session_type} for '{course_name}' to your schedule!")
                st.rerun()


# ----------------------------------------------------------------------
# Tab 4: Assignments
# ----------------------------------------------------------------------
with tab4:
    st.subheader("Assignment Deadline Tracker")

    assignments = load_assignments()

    if assignments:
        df = pd.DataFrame(assignments)
        st.dataframe(df, use_container_width=True)

        st.markdown("#### Manage Assignments")
        options = [
            f"{i}: {a['title']} ({a['course']}) - due {a['due_date']} "
            f"{'[DONE]' if a['completed'] else ''}"
            for i, a in enumerate(assignments)
        ]
        selected = st.selectbox("Select assignment", options=["-- none --"] + options, key="assign_select")
        if selected != "-- none --":
            idx = int(selected.split(":")[0])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Toggle completed"):
                    toggle_completed(idx)
                    st.rerun()
            with col2:
                if st.button("🗑️ Remove assignment"):
                    remove_assignment(idx)
                    st.rerun()

        st.markdown("---")
        st.markdown("#### Upcoming Deadlines (next 14 days, sorted by priority)")
        upcoming = get_upcoming_assignments(days_ahead=14, sort_by_priority=True)
        if upcoming:
            priority_emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
            for a in upcoming:
                emoji = priority_emoji.get(a.get("priority", "Medium"), "🟡")
                st.markdown(f"- {emoji} **{a['title']}** ({a['course']}) — due {a['due_date']} "
                            f"{a.get('due_time','')} · Priority: {a.get('priority','Medium')}")
        else:
            st.info("No upcoming deadlines in the next 14 days.")
    else:
        st.info("No assignments tracked yet. Add one below.")

    st.markdown("---")
    st.markdown("#### Add Assignment")
    with st.form("add_assignment_form"):
        title = st.text_input("Assignment Title", placeholder="e.g. DBMS Lab Report")
        course = st.text_input("Course", placeholder="e.g. Database Systems")
        col1, col2, col3 = st.columns(3)
        with col1:
            due_date = st.date_input("Due Date", value=datetime.date.today() + datetime.timedelta(days=7))
        with col2:
            due_time = st.time_input("Due Time", value=datetime.time(23, 59))
        with col3:
            priority = st.selectbox("Priority", PRIORITY_LEVELS, index=PRIORITY_LEVELS.index("Medium"))
        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("➕ Add Assignment")
        if submitted:
            is_valid, error_msg = validate_assignment(title, course, due_date)
            if not is_valid:
                st.error(error_msg)
            else:
                add_assignment(
                    title=title, course=course,
                    due_date=due_date.strftime("%Y-%m-%d"),
                    due_time=due_time.strftime("%H:%M"),
                    notes=notes,
                    priority=priority,
                )
                st.success(f"Added assignment '{title}' (Priority: {priority})!")
                st.rerun()

    if assignments and st.session_state.get("service"):
        st.markdown("---")
        st.markdown("#### 📧 Send Email Reminder for an Assignment")
        with st.expander("Send reminder"):
            sender_email = st.text_input("Your Gmail address", key="rem_sender")
            sender_pw = st.text_input("Gmail App Password", type="password", key="rem_pw")
            recipient = st.text_input("Send reminder to", key="rem_recipient")
            remind_options = [f"{i}: {a['title']} (due {a['due_date']})" for i, a in enumerate(assignments)]
            remind_select = st.selectbox("Assignment", options=["-- none --"] + remind_options, key="rem_select")

            if st.button("Send Reminder Email"):
                if remind_select == "-- none --":
                    st.error("Select an assignment first.")
                elif not (sender_email and sender_pw and recipient):
                    st.error("Fill in all email fields.")
                else:
                    idx = int(remind_select.split(":")[0])
                    a = assignments[idx]
                    try:
                        send_email_reminder(
                            sender_email, sender_pw, recipient,
                            subject=f"Reminder: {a['title']} due {a['due_date']}",
                            body=build_assignment_reminder_body(a),
                        )
                        st.success("Reminder email sent!")
                    except Exception as e:
                        st.error(friendly_api_error("Email", e))

# ----------------------------------------------------------------------
# Tab 5: Free Time & Conflicts
# ----------------------------------------------------------------------
with tab5:
    st.subheader("Find Free Time")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar to find free time.")
    else:
        target_date = st.date_input("Pick a date", value=datetime.date.today())
        min_duration = st.slider("Minimum free slot duration (minutes)", 15, 180, 30, step=15)

        if st.button("🔍 Find Free Slots"):
            try:
                events = get_events_safe(max_results=50)
                class_schedule = load_schedule()
                slots = find_free_slots(events, target_date, min_duration_minutes=min_duration,
                                         class_schedule=class_schedule)
                if slots:
                    st.success(f"Found {len(slots)} free slot(s) on {target_date}:")
                    for s, e in slots:
                        st.markdown(f"- **{s.strftime('%H:%M')} - {e.strftime('%H:%M')}** "
                                     f"({int((e-s).total_seconds()//60)} min)")
                else:
                    st.info(f"No free slots of at least {min_duration} minutes found on {target_date}.")
            except Exception as e:
                st.error(friendly_api_error("Google Calendar", e))

    st.markdown("---")
    st.subheader("Conflict Check")
    st.caption("Conflicts among your upcoming events are also shown automatically in the 'Upcoming Events' tab.")

    if st.session_state.service:
        try:
            events = get_events_safe(max_results=50)
            conflicts = find_event_conflicts(events)
            if conflicts:
                for c in conflicts:
                    st.markdown(
                        f"- ⚠️ **{c['event1']}** ({c['event1_time']}) overlaps with "
                        f"**{c['event2']}** ({c['event2_time']})"
                    )
            else:
                st.success("✅ No conflicts detected.")
        except Exception as e:
            st.error(friendly_api_error("Google Calendar", e))

# ----------------------------------------------------------------------
# Tab 6: AI Assistant (conversational agent)
# ----------------------------------------------------------------------
with tab6:
    st.subheader("🤖 AI Scheduling Assistant")
    st.caption(
        "Chat naturally: \"Find free time tomorrow afternoon\", "
        "\"Schedule a study session for Friday 4-6pm\", "
        "\"Add an assignment: DBMS report due next Monday\", etc."
    )

    openai_key = st.text_input("OpenAI API Key", type="password",
                                help="Get one at https://platform.openai.com/api-keys. "
                                     "Required to use the AI assistant.")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar first.")
    elif not openai_key:
        st.info("Enter your OpenAI API key above to start chatting with the assistant.")
    else:
        from agent import build_agent

        if "agent_executor" not in st.session_state or st.session_state.get("agent_key") != openai_key:
            try:
                st.session_state.agent_executor = build_agent(st.session_state.service, openai_key)
                st.session_state.agent_key = openai_key
                st.session_state.chat_history = []
            except Exception as e:
                st.error(friendly_api_error("OpenAI", e))
                st.stop()

        # Display chat history
        for msg in st.session_state.get("chat_history", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask me to schedule something, find free time, or add an assignment...")
        if user_input:
            is_valid, error_msg = validate_natural_language_request(user_input)
            if not is_valid:
                st.error(error_msg)
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            result = st.session_state.agent_executor.invoke(
                                {"messages": [{"role": "user", "content": user_input}]}
                            )
                            messages = result.get("messages", [])
                            answer = messages[-1].content if messages else "Sorry, I couldn't process that."
                        except Exception as e:
                            answer = friendly_api_error("OpenAI", e)
                        st.markdown(answer)

                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.cache_data.clear()

# ----------------------------------------------------------------------
# Tab 7: Exams & Study Planner
# ----------------------------------------------------------------------
with tab7:
    st.subheader("🎓 Exam Schedule & Study Time Allocation")

    exams = load_exams()

    if exams:
        df = pd.DataFrame(exams)
        st.dataframe(df, use_container_width=True)

        st.markdown("#### Remove an exam")
        options = [f"{i}: {e['course']} - {e['exam_date']} {e['exam_time']}" for i, e in enumerate(exams)]
        selected = st.selectbox("Select exam to remove", options=["-- none --"] + options)
        if selected != "-- none --":
            idx = int(selected.split(":")[0])
            if st.button("🗑️ Remove exam"):
                remove_exam(idx)
                st.rerun()

        st.markdown("---")
        st.markdown("#### Upcoming Exams (next 60 days)")
        upcoming_exams = get_upcoming_exams(days_ahead=60)
        if upcoming_exams:
            for e in upcoming_exams:
                days_left = (datetime.datetime.strptime(e["exam_date"], "%Y-%m-%d").date() - datetime.date.today()).days
                st.markdown(f"- **{e['course']}** — {e['exam_date']} {e['exam_time']} "
                            f"({days_left} day(s) away) · Priority: {e.get('priority','High')} "
                            f"· Goal: {e.get('study_hours_goal',10)}h study")
        else:
            st.info("No exams scheduled in the next 60 days.")
    else:
        st.info("No exams added yet. Add one below.")

    st.markdown("---")
    st.markdown("#### Add Exam")
    with st.form("add_exam_form"):
        course = st.text_input("Course", placeholder="e.g. Database Systems")
        col1, col2 = st.columns(2)
        with col1:
            exam_date = st.date_input("Exam Date", value=datetime.date.today() + datetime.timedelta(days=14), key="exam_date")
        with col2:
            exam_time = st.time_input("Exam Time", value=datetime.time(10, 0), key="exam_time")
        col3, col4, col5 = st.columns(3)
        with col3:
            duration = st.number_input("Duration (minutes)", min_value=30, max_value=300, value=120, step=15)
        with col4:
            priority = st.selectbox("Priority", PRIORITY_LEVELS, index=PRIORITY_LEVELS.index("High"), key="exam_priority")
        with col5:
            study_hours = st.number_input("Study hours goal", min_value=1, max_value=50, value=10)
        location = st.text_input("Exam Location (optional)", placeholder="e.g. Main Hall")

        submitted = st.form_submit_button("➕ Add Exam")
        if submitted:
            is_valid, error_msg = validate_exam(course, exam_date, int(duration), int(study_hours))
            if not is_valid:
                st.error(error_msg)
            else:
                add_exam(
                    course=course,
                    exam_date=exam_date.strftime("%Y-%m-%d"),
                    exam_time=exam_time.strftime("%H:%M"),
                    duration_minutes=int(duration),
                    location=location,
                    priority=priority,
                    study_hours_goal=int(study_hours),
                )
                st.success(f"Added exam for '{course}' on {exam_date}!")
                st.rerun()

    # ------------------------------------------------------------------
    # Study time allocation
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📖 Suggest Study Time Slots")
    st.caption("Finds free time in the days before an exam, based on your Google Calendar "
               "events and class schedule.")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar to get study time suggestions.")
    elif not exams:
        st.info("Add an exam above first.")
    else:
        exam_options = [f"{i}: {e['course']} - {e['exam_date']}" for i, e in enumerate(exams)]
        exam_selected = st.selectbox("Select exam", options=exam_options, key="study_exam_select")
        days_before = st.slider("Days before exam to consider", 1, 14, 7)
        session_length = st.slider("Study session length (minutes)", 30, 180, 60, step=15)

        if st.button("📖 Suggest Study Slots"):
            idx = int(exam_selected.split(":")[0])
            exam = exams[idx]
            try:
                events = get_events_safe(max_results=100)
                class_schedule = load_schedule()
                suggestions = allocate_study_slots(
                    exam, events, class_schedule,
                    days_before=days_before, session_length_minutes=session_length
                )
                if suggestions:
                    total_minutes = sum(
                        (datetime.datetime.strptime(s["end"], "%H:%M") -
                         datetime.datetime.strptime(s["start"], "%H:%M")).seconds // 60
                        for s in suggestions
                    )
                    st.success(f"Suggested {len(suggestions)} session(s), "
                               f"~{total_minutes/60:.1f}h total (goal: {exam.get('study_hours_goal',10)}h)")
                    for s in suggestions:
                        st.markdown(f"- **{s['date']}**: {s['start']} - {s['end']} — Study {s['course']}")

                    if st.button("➕ Add all study sessions to Google Calendar"):
                        try:
                            for s in suggestions:
                                start_dt = datetime.datetime.strptime(f"{s['date']} {s['start']}", "%Y-%m-%d %H:%M")
                                end_dt = datetime.datetime.strptime(f"{s['date']} {s['end']}", "%Y-%m-%d %H:%M")
                                create_event(
                                    st.session_state.service,
                                    summary=f"Study: {s['course']}",
                                    start_datetime=start_dt,
                                    end_datetime=end_dt,
                                    description=f"Auto-scheduled study session for {exam['course']} exam on {exam['exam_date']}",
                                )
                            st.success("Study sessions added to your Google Calendar!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(friendly_api_error("Google Calendar", e))
                else:
                    st.info("No suitable free slots found before this exam. Try increasing 'days before' "
                            "or reducing session length.")
            except Exception as e:
                st.error(friendly_api_error("Google Calendar", e))

# ----------------------------------------------------------------------
# Tab 8: Academic Calendar (Indian semester/term + holidays)
# ----------------------------------------------------------------------
with tab8:
    st.subheader("🇮🇳 Academic Calendar")
    st.caption("Manage semester/term dates, semester breaks, and Indian festivals/holidays.")

    st.markdown("#### Semester / Term Templates")
    terms = load_terms()
    active_term = get_active_term()

    if active_term:
        st.success(f"📌 Currently in: **{active_term['name']}** "
                   f"({active_term['start_date']} to {active_term['end_date']})")
    else:
        st.info("No active term for today's date. Add your current semester below.")

    if terms:
        df = pd.DataFrame(terms)
        st.dataframe(df, use_container_width=True)

        options = [f"{i}: {t['name']}" for i, t in enumerate(terms)]
        selected = st.selectbox("Select term to remove", options=["-- none --"] + options, key="term_select")
        if selected != "-- none --":
            idx = int(selected.split(":")[0])
            if st.button("🗑️ Remove term"):
                remove_term(idx)
                st.rerun()

    with st.form("add_term_form"):
        st.markdown("**Add Semester/Term**")
        name = st.text_input("Term Name", placeholder="e.g. Semester 5 (Odd 2026)")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Term Start Date", key="term_start")
        with col2:
            end_date = st.date_input("Term End Date", key="term_end")
        col3, col4 = st.columns(2)
        with col3:
            exam_start = st.date_input("Exam Period Start (optional)", key="exam_period_start")
        with col4:
            exam_end = st.date_input("Exam Period End (optional)", key="exam_period_end")
        col5, col6 = st.columns(2)
        with col5:
            break_start = st.date_input("Semester Break Start (optional)", key="break_start")
        with col6:
            break_end = st.date_input("Semester Break End (optional)", key="break_end")

        submitted = st.form_submit_button("➕ Add Term")
        if submitted:
            if not name or not name.strip():
                st.error("Please enter a term name.")
            else:
                is_valid, error_msg = validate_date_range(start_date, end_date)
                if not is_valid:
                    st.error(error_msg)
                else:
                    add_term(
                        name=name,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        exam_start=exam_start.strftime("%Y-%m-%d"),
                        exam_end=exam_end.strftime("%Y-%m-%d"),
                        break_start=break_start.strftime("%Y-%m-%d"),
                        break_end=break_end.strftime("%Y-%m-%d"),
                    )
                    st.success(f"Added term '{name}'!")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Holidays & Festivals")
    st.caption("Pre-loaded with common Indian national holidays/festivals for 2026 — edit as needed for your university.")

    holidays = load_holidays()
    upcoming_holidays = get_upcoming_holidays(days_ahead=60)

    if upcoming_holidays:
        st.markdown("**Upcoming (next 60 days):**")
        for h in upcoming_holidays:
            st.markdown(f"- 🎉 **{h['name']}** — {h['date']} ({h['type']})")
    else:
        st.info("No holidays in the next 60 days.")

    with st.expander("View / Manage all holidays"):
        if holidays:
            df = pd.DataFrame(holidays)
            st.dataframe(df, use_container_width=True)

            options = [f"{i}: {h['name']} ({h['date']})" for i, h in enumerate(holidays)]
            selected = st.selectbox("Select holiday to remove", options=["-- none --"] + options, key="holiday_select")
            if selected != "-- none --":
                idx = int(selected.split(":")[0])
                if st.button("🗑️ Remove holiday"):
                    remove_holiday(idx)
                    st.rerun()

        st.markdown("**Add a holiday/festival**")
        with st.form("add_holiday_form"):
            hname = st.text_input("Name", placeholder="e.g. Onam")
            hdate = st.date_input("Date", key="holiday_date")
            htype = st.selectbox("Type", ["national", "festival", "university"])
            hsubmit = st.form_submit_button("➕ Add Holiday")
            if hsubmit:
                if not hname:
                    st.error("Please enter a holiday name.")
                else:
                    add_holiday(hname, hdate.strftime("%Y-%m-%d"), htype)
                    st.success(f"Added '{hname}'!")
                    st.rerun()

# ----------------------------------------------------------------------
# Tab 9: Calendar View (Monthly / Weekly / Daily)
# ----------------------------------------------------------------------
with tab9:
    st.subheader("🗂️ Calendar View")
    st.caption("Combined view of your Google Calendar events and recurring class schedule. "
               "🟡 = Class session, 🟢 = Calendar event.")

    if not st.session_state.service:
        st.warning("Connect to Google Calendar from the sidebar to see your calendar.")
    else:
        view_mode = st.radio("View", ["Monthly", "Weekly", "Daily"], horizontal=True)
        class_schedule = load_schedule()

        try:
            if view_mode == "Monthly":
                col1, col2 = st.columns(2)
                with col1:
                    sel_year = st.number_input("Year", min_value=2020, max_value=2100,
                                                 value=datetime.date.today().year)
                with col2:
                    sel_month = st.selectbox("Month", list(range(1, 13)),
                                              index=datetime.date.today().month - 1,
                                              format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"))

                # Fetch events broadly around this month
                events = get_events_safe(max_results=100)
                html = render_month_view(int(sel_year), int(sel_month), events, class_schedule)
                st.markdown(html, unsafe_allow_html=True)

            elif view_mode == "Weekly":
                ref_date = st.date_input("Pick any date in the week", value=datetime.date.today())
                start_of_week = ref_date - datetime.timedelta(days=ref_date.weekday())
                events = get_events_safe(max_results=100)
                html = render_week_view(start_of_week, events, class_schedule)
                st.markdown(html, unsafe_allow_html=True)

            else:  # Daily
                sel_date = st.date_input("Pick a date", value=datetime.date.today(), key="daily_view_date")
                events = get_events_safe(max_results=100)
                html = render_day_view(sel_date, events, class_schedule)
                st.markdown(html, unsafe_allow_html=True)

        except Exception as e:
            st.error(friendly_api_error("Google Calendar", e))

# ----------------------------------------------------------------------
# Tab 10: Export
# ----------------------------------------------------------------------
with tab10:
    st.subheader("⬇️ Export Your Schedule")
    st.caption("Download your schedule as a calendar file (.ics) you can import into Google Calendar, "
               "Outlook, or Apple Calendar, or as a report (CSV / text summary).")

    class_schedule = load_schedule()
    assignments = load_assignments()
    exams = load_exams()
    holidays = get_upcoming_holidays(days_ahead=180)

    st.markdown("#### 📅 Calendar File (.ics)")
    st.caption("Includes your recurring class schedule, exams, and assignment deadlines. "
               "Optionally include your live Google Calendar events too.")

    include_gcal = False
    if st.session_state.service:
        include_gcal = st.checkbox("Also include my upcoming Google Calendar events", value=True)

    if st.button("Generate .ics file"):
        try:
            events_for_export = get_events_safe(max_results=100) if include_gcal else None
            ics_content = generate_ics(
                events=events_for_export,
                class_schedule=class_schedule,
                exams=exams,
                assignments=assignments,
                calendar_name="My Student Schedule",
            )
            st.download_button(
                label="⬇️ Download student_schedule.ics",
                data=ics_content,
                file_name="student_schedule.ics",
                mime="text/calendar",
            )
            st.success("ICS file ready! Click the download button above.")
        except Exception as e:
            st.error(f"Failed to generate calendar file: {e}")

    st.markdown("---")
    st.markdown("#### 📊 Schedule Report")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate CSV Report"):
            try:
                csv_content = generate_csv_report(
                    class_schedule=class_schedule, assignments=assignments, exams=exams
                )
                st.download_button(
                    label="⬇️ Download schedule_report.csv",
                    data=csv_content,
                    file_name="schedule_report.csv",
                    mime="text/csv",
                )
                st.success("CSV report ready!")
            except Exception as e:
                st.error(f"Failed to generate CSV report: {e}")

    with col2:
        if st.button("Generate Text Summary"):
            try:
                text_content = generate_text_summary(
                    class_schedule=class_schedule, assignments=assignments,
                    exams=exams, holidays=holidays
                )
                st.download_button(
                    label="⬇️ Download schedule_summary.txt",
                    data=text_content,
                    file_name="schedule_summary.txt",
                    mime="text/plain",
                )
                st.success("Text summary ready!")
                with st.expander("Preview"):
                    st.text(text_content)
            except Exception as e:
                st.error(f"Failed to generate text summary: {e}")
