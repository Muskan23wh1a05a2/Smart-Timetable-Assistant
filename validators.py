"""
validators.py
---------------
Input validation helpers for scheduling requests, events, assignments, and exams.
Each function returns (is_valid: bool, error_message: str or None).
"""

import datetime


def validate_event_input(title, start_dt, end_dt):
    """Validates a calendar event's title and time range."""
    if not title or not title.strip():
        return False, "Event title cannot be empty."
    if len(title) > 200:
        return False, "Event title is too long (max 200 characters)."
    if end_dt <= start_dt:
        return False, "End time must be after start time."
    if (end_dt - start_dt) > datetime.timedelta(days=7):
        return False, "Event duration cannot exceed 7 days."
    if start_dt < datetime.datetime.now() - datetime.timedelta(days=1):
        return False, "Cannot create events more than 1 day in the past."
    return True, None


def validate_class_session(course_name, days, start_time, end_time):
    """Validates a recurring class session entry."""
    if not course_name or not course_name.strip():
        return False, "Course name cannot be empty."
    if not days:
        return False, "Please select at least one day of the week."
    valid_days = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
    if not set(days).issubset(valid_days):
        return False, f"Invalid day(s) selected. Must be one of {valid_days}."
    if end_time <= start_time:
        return False, "Class end time must be after start time."
    return True, None


def validate_assignment(title, course, due_date):
    """Validates an assignment entry."""
    if not title or not title.strip():
        return False, "Assignment title cannot be empty."
    if not course or not course.strip():
        return False, "Course name cannot be empty."
    if not isinstance(due_date, (datetime.date, datetime.datetime)):
        return False, "Invalid due date."
    return True, None


def validate_exam(course, exam_date, duration_minutes, study_hours_goal):
    """Validates an exam entry."""
    if not course or not course.strip():
        return False, "Course name cannot be empty."
    if not isinstance(exam_date, (datetime.date, datetime.datetime)):
        return False, "Invalid exam date."
    if exam_date < datetime.date.today():
        return False, "Exam date cannot be in the past."
    if duration_minutes <= 0 or duration_minutes > 480:
        return False, "Exam duration must be between 1 and 480 minutes."
    if study_hours_goal < 0 or study_hours_goal > 200:
        return False, "Study hours goal must be between 0 and 200."
    return True, None


def validate_date_range(start_date, end_date):
    """Validates that a start date is before or equal to an end date."""
    if start_date > end_date:
        return False, "Start date must be before or equal to end date."
    return True, None


def validate_natural_language_request(text):
    """Basic validation for natural language scheduling requests sent to the AI agent."""
    if not text or not text.strip():
        return False, "Please enter a request."
    if len(text) > 1000:
        return False, "Request is too long (max 1000 characters)."
    return True, None


class ScheduleAPIError(Exception):
    """Raised when an external API (Google Calendar, OpenAI, SMTP) call fails."""
    def __init__(self, service_name, original_error):
        self.service_name = service_name
        self.original_error = original_error
        super().__init__(f"{service_name} error: {original_error}")


def friendly_api_error(service_name, exception):
    """
    Converts a raw exception from an external API into a user-friendly message.
    """
    err_str = str(exception).lower()

    if service_name == "Google Calendar":
        if "invalid_grant" in err_str or "token" in err_str:
            return ("Your Google Calendar session has expired or is invalid. "
                    "Please delete `token.json` and reconnect.")
        if "quota" in err_str or "rate" in err_str:
            return "Google Calendar API rate limit reached. Please wait a moment and try again."
        if "404" in err_str or "not found" in err_str:
            return "The requested calendar event was not found (it may have already been deleted)."
        return f"Google Calendar error: {exception}"

    if service_name == "OpenAI":
        if "api key" in err_str or "authentication" in err_str or "401" in err_str:
            return "Invalid OpenAI API key. Please check the key you entered."
        if "rate" in err_str or "429" in err_str:
            return "OpenAI rate limit reached. Please wait a moment and try again."
        if "quota" in err_str or "billing" in err_str:
            return "OpenAI account has insufficient quota/billing. Please check your OpenAI account."
        return f"AI Assistant error: {exception}"

    if service_name == "Email":
        if "authentication" in err_str or "535" in err_str:
            return ("Email authentication failed. Make sure you're using a Gmail "
                    "App Password, not your regular password.")
        return f"Email error: {exception}"

    return f"{service_name} error: {exception}"
