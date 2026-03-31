"""HTML ID constants for Dash components.

Naming convention: <NAME>_<TYPE>_<PAGE>_ID
- NAME: Semantic purpose (e.g., START_JOB, EMAIL)
- TYPE: Component type (BUTTON, INPUT, DIV, DROPDOWN, STORE, MODAL, ALERT, LINK, etc.)
- PAGE: Page scope (SHARED, HOME, INPUT, JOB_SUBMISSION, RESULTS, etc.)
- ID: Required suffix

See docs/conventions/html_ids.md for full details.
"""

# =============================================================================
# SHARED / GLOBAL
# =============================================================================

# --- Locations ---
URL_LOCATION_SHARED_ID = "url-location-shared-id"  # nocheck - dcc.Location used by Dash routing

# --- Modals ---
ERROR_MODAL_SHARED_ID = "error-modal-shared-id"  # nocheck - used via set_props()
LOADING_OVERLAY_MODAL_SHARED_ID = "loading-overlay-modal-shared-id"

# --- Divs ---
ERROR_TITLE_DIV_SHARED_ID = (
    "error-title-div-shared-id"  # nocheck - used via set_props()
)
ERROR_MESSAGE_DIV_SHARED_ID = (
    "error-message-div-shared-id"  # nocheck - used via set_props()
)

# --- Buttons ---
DOWNLOAD_BUTTON_SHARED_ID = "download-button-shared-id"  # nocheck - used in files_route, testing only
NAVBAR_TOGGLER_BUTTON_SHARED_ID = "navbar-toggler-button-shared-id"

# --- Collapses ---
NAVBAR_COLLAPSE_DIV_SHARED_ID = "navbar-collapse-div-shared-id"


# =============================================================================
# HOME
# =============================================================================

# --- Buttons ---
START_BUTTON_HOME_ID = "start-button-home-id"

# --- Inputs ---
JOB_INPUT_HOME_ID = "job-input-home-id"

# --- FormTexts ---
JOB_FEEDBACK_FORMTEXT_HOME_ID = "job-feedback-formtext-home-id"

# =============================================================================
# INPUT
# =============================================================================

# --- Buttons ---
CHECK_INPUT_BUTTON_INPUT_ID = (  # nocheck - used via FormFactory
    "check_input_button_input_id"
)

# --- Divs ---
HEADER_DIV_INPUT_ID = "header-div-input-id"  # nocheck - used via landing_page_layout_column
MAIN_CONTENT_DIV_INPUT_ID = "main-content-div-input-id"

# --- Uploads ---
CSV_UPLOAD_INPUT_ID = "csv-upload-input-id"

# --- Feedback ---
UPLOAD_FEEDBACK_DIV_INPUT_ID = "upload-feedback-input-id"

# --- Stores ---
JOB_STORE_INPUT_ID = "job-store-input-id"
FORM_VALID_STORE_INPUT_ID = "form-valid-store-input-id"
UPLOADED_FILE_NAME_STORE_INPUT_ID = "uploaded-file-name-store-input-id"

# =============================================================================
# JOB_SUBMISSION
# =============================================================================

# --- Buttons ---
SUBMIT_BUTTON_JOB_SUBMISSION_ID = "submit-button-job-submission-id"
CHANGE_INPUT_BUTTON_JOB_SUBMISSION_ID = "change-input-button-job-submission-id"
VIEW_RESULTS_BUTTON_JOB_SUBMISSION_ID = "view-results-button-job-submission-id"
RESUBMIT_BUTTON_JOB_SUBMISSION_ID = "resubmit-button-job-submission-id"

# --- Divs ---
HEADER_DIV_JOB_SUBMISSION_ID = "header-div-job-submission-id"  # nocheck - used via landing_page_layout_column
MAIN_CONTENT_DIV_JOB_SUBMISSION_ID = "main-content-div-job-submission-id"
STATUS_DIV_JOB_SUBMISSION_ID = "status-div-job-submission-id"
JOB_LOGS_DIV_JOB_SUBMISSION_ID = "job-logs-div-job-submission-id"

# --- Intervals ---
INTERVAL_JOB_SUBMISSION_ID = "interval-job-submission-id"

# --- Stores ---
JOB_STORE_JOB_SUBMISSION_ID = "job-store-job-submission-id"

# --- Accordions ---
ACCORDION_JOB_SUBMISSION_ID = "accordion-job-submission-id"

# --- Icons ---
ICON_JOB_SUBMISSION_ID = "icon-job-submission-id"

# =============================================================================
# RESULTS
# =============================================================================

# --- Buttons ---
BACK_BUTTON_RESULTS_ID = "back-button-results-id"  # nocheck - used as href button, testing only

# --- Divs ---
HEADER_DIV_RESULTS_ID = "header-div-results-id"
MAIN_CONTENT_DIV_RESULTS_ID = "main-content-div-results-id"

# --- Stores ---
JOB_STORE_RESULTS_ID = "job-store-results-id"

# --- Tables ---
SUMMARY_TABLE_RESULTS_ID = "summary-table-results-id"  # nocheck - testing only

# =============================================================================
# WORKER_MANAGEMENT
# =============================================================================

# --- Buttons ---
REFRESH_BUTTON_WORKER_MANAGEMENT_ID = "refresh-button-worker-management-id"
KILL_BUTTON_WORKER_MANAGEMENT_ID = "kill-button-worker-management-id"
CANCEL_BUTTON_WORKER_MANAGEMENT_ID = "cancel-button-worker-management-id"
KILL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID = (
    "kill-modal-cancel-button-worker-management-id"
)
KILL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID = (
    "kill-modal-confirm-button-worker-management-id"
)
CANCEL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID = (
    "cancel-modal-cancel-button-worker-management-id"
)
CANCEL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID = (
    "cancel-modal-confirm-button-worker-management-id"
)
TEST_JOB_BUTTON_WORKER_MANAGEMENT_ID = "test-job-button-worker-management-id"

# --- Divs ---
DUMMY_DIV_WORKER_MANAGEMENT_ID = "dummy-div-worker-management-id"
STATS_CARD_DIV_WORKER_MANAGEMENT_ID = "stats-card-div-worker-management-id"
LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID = "last-refresh-div-worker-management-id"
KILL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID = (
    "kill-modal-task-info-div-worker-management-id"
)
CANCEL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID = (
    "cancel-modal-task-info-div-worker-management-id"
)
TEST_JOB_FEEDBACK_DIV_WORKER_MANAGEMENT_ID = (
    "test-job-feedback-div-worker-management-id"
)

# --- Modals ---
KILL_MODAL_WORKER_MANAGEMENT_ID = "kill-modal-worker-management-id"
CANCEL_MODAL_WORKER_MANAGEMENT_ID = "cancel-modal-worker-management-id"

# --- Tables ---
ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID = "active-tasks-table-worker-management-id"
RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID = "reserved-tasks-table-worker-management-id"
SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID = (
    "scheduled-tasks-table-worker-management-id"
)
REVOKED_TASKS_TABLE_WORKER_MANAGEMENT_ID = "revoked-tasks-table-worker-management-id"

# =============================================================================
# JOB_MANAGEMENT
# =============================================================================

# --- Buttons ---
DELETE_BUTTON_JOB_MANAGEMENT_ID = "delete-button-job-management-id"
CLEAN_BUTTON_JOB_MANAGEMENT_ID = "clean-button-job-management-id"
REFRESH_BUTTON_JOB_MANAGEMENT_ID = "refresh-button-job-management-id"

# --- Stores ---
DUMMY_STORE_JOB_MANAGEMENT_ID = "dummy-store-job-management-id"

# --- Tables ---
JOBS_TABLE_JOB_MANAGEMENT_ID = "jobs-table-job-management-id"

# =============================================================================
# LOGS
# =============================================================================

# --- DatePickers ---
DATE_RANGE_DATEPICKER_LOGS_ID = "date-range-datepicker-logs-id"

# --- Divs ---
LOG_OUTPUT_DIV_LOGS_ID = "log-output-div-logs-id"
TIME_ERROR_DIV_LOGS_ID = "time-error-div-logs-id"

# --- Dropdowns ---
LOG_LEVELS_DROPDOWN_LOGS_ID = "log-levels-dropdown-logs-id"

# --- Input Groups ---
TIME_INPUT_GROUP_LOGS_ID = "time-input-group-logs-id"

# --- Inputs ---
START_HOUR_INPUT_LOGS_ID = "start-hour-input-logs-id"
START_MINUTE_INPUT_LOGS_ID = "start-minute-input-logs-id"
END_HOUR_INPUT_LOGS_ID = "end-hour-input-logs-id"
END_MINUTE_INPUT_LOGS_ID = "end-minute-input-logs-id"
PID_INPUT_LOGS_ID = "pid-input-logs-id"

# --- Buttons ---
REFRESH_BUTTON_LOGS_ID = "refresh-button-logs-id"

# --- Checklists ---
PID_RADIO_CHECKLIST_LOGS_ID = "pid-radio-checklist-logs-id"
LIVE_MODE_CHECKLIST_LOGS_ID = "live-mode-checklist-logs-id"

# --- Dropdowns (continued) ---
MODULE_EXCLUDE_DROPDOWN_LOGS_ID = "module-exclude-dropdown-logs-id"

# --- Intervals ---
AUTO_POLL_INTERVAL_LOGS_ID = "auto-poll-interval-logs-id"
