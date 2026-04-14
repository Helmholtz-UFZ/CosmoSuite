"""Module for interaction between webservice and database."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import (
    POSTGRES_DB,
    POSTGRES_HOST_NAME,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from src.error_handling import JobNotFound

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for declarative base."""

    pass


class SessionScope:
    """Context manager for managing database sessions with retry logic."""

    def __init__(self, session_factory):
        """Initialize the session scope with a session factory."""
        self.session_factory = session_factory
        self.max_retries = 3
        self.retry_delay = 1
        self.session = None

    def __enter__(self):
        """Create a new session and handle retries for database operations."""
        for attempt in range(self.max_retries + 1):
            try:
                self.session = self.session_factory()
                return self.session  # success
            except OperationalError as e:
                if attempt < self.max_retries:
                    log.warning(f"Database OperationalError: {e}")
                    log.warning(
                        f"Retrying operation (attempt {attempt + 1}/{self.max_retries + 1})"  # noqa
                    )
                    time.sleep(self.retry_delay)
                else:
                    log.error(f"Max retries ({self.max_retries}) exceeded")
                    raise
            except SQLAlchemyError as e:
                log.error(f"Database error: {e}")
                raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback the session based on exception type."""
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

        # False means exceptions are re-raised outside the `with`
        return False


class DbManager:
    """Class for interacting with the postgres database."""

    _engine = None
    _Session = None

    @classmethod
    def _get_session(cls):
        """Return the session factory, creating the engine on first call."""
        if cls._Session is None:
            database_url = (
                f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
                f"{POSTGRES_HOST_NAME}:{POSTGRES_PORT}/{POSTGRES_DB}"
            )
            cls._engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
            )
            cls._Session = sessionmaker(bind=cls._engine)
        return cls._Session

    @classmethod
    def session_scope(cls):
        """Provide a transactional scope around a series of operations."""
        return SessionScope(session_factory=cls._get_session())

    @classmethod
    def query_distinct_modules(cls) -> List[str]:
        """Return all distinct module names from the logs table.

        Returns
        -------
        list[str]
            Sorted list of unique module names.
        """
        with cls.session_scope() as session:
            rows = (
                session.query(LogTable.module)
                .distinct()
                .order_by(LogTable.module)
                .all()
            )
            return [row[0] for row in rows]

    @classmethod
    def query_logs(
        cls,
        date: str,
        sh: int,
        sm: int,
        eh: int,
        em: int,
        levels: List[str],
        pid: Optional[int] = None,
        excluded_modules: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query logs from the database with specified filters.

        Parameters
        ----------
        date : str
            Date in the format 'YYYY-MM-DD'
        sh : int
            Start hour (0-23)
        sm : int
            Start minute (0-59)
        eh : int
            End hour (0-23)
        em : int
            End minute (0-59)
        levels : list
            List of log levels to include (e.g., ['INFO', 'ERROR'])
        pid : int, optional
            Process ID to filter logs by
        excluded_modules : list[str], optional
            Module names to exclude from results
        """
        log.debug(f"Querying logs from {date} {sh}:{sm} to {date} {eh}:{em}")

        start_datetime = datetime.strptime(
            f"{date} {sh:02d}:{sm:02d}:00", "%Y-%m-%d %H:%M:%S"
        )
        end_datetime = datetime.strptime(
            f"{date} {eh:02d}:{em:02d}:59", "%Y-%m-%d %H:%M:%S"
        )

        with cls.session_scope() as session:
            query = session.query(LogTable).filter(
                LogTable.timestamp >= start_datetime,
                LogTable.timestamp <= end_datetime,
                LogTable.level.in_(levels),
            )

            if pid is not None:
                query = query.filter(LogTable.pid == pid)

            if excluded_modules:
                query = query.filter(LogTable.module.notin_(excluded_modules))

            # Order results by timestamp
            query = query.order_by(LogTable.timestamp)

            # Execute query and convert results to dictionaries
            logs = [log.to_dict() for log in query.all()]

        return logs

    @classmethod
    def delete_logs_older_than(cls, cutoff_datetime):
        """Delete all log records older than the given datetime."""
        log.info(f"Deleting logs older than {cutoff_datetime}")
        with cls.session_scope() as session:
            session.query(LogTable).filter(LogTable.timestamp < cutoff_datetime).delete(
                synchronize_session=False
            )

    @classmethod
    def check_existence(cls, job_id):
        """Check if a job with the given job ID exists in the database."""
        log.debug(f"Check existence of job: {job_id}")
        with cls.session_scope() as session:
            job_row = session.query(JobTable.job_id).filter_by(job_id=job_id).first()
        return job_row is not None

    @classmethod
    def add_entry(cls, data_to_insert):
        """Add or update a job entry in the database."""
        log.debug(
            f"Add entry to database: {data_to_insert['job_id']}",
        )
        with cls.session_scope() as session:
            job_row = (
                session.query(JobTable.job_id)
                .filter_by(job_id=data_to_insert["job_id"])
                .first()
            )

            if job_row is not None:
                log.debug("Update entry.")
                job = (
                    session.query(JobTable)
                    .filter_by(job_id=data_to_insert["job_id"])
                    .first()
                )
                for column_name, column_value in data_to_insert.items():
                    setattr(job, column_name, column_value)
            else:
                log.debug("New entry.")
                job_row = JobTable(**data_to_insert)
                session.add(job_row)

    @classmethod
    def update_column(cls, job_id, column_dic):
        """Update specific columns in the 'JobTable' for a given job ID."""
        log.debug(f"Update columns for job: {job_id}")

        with cls.session_scope() as session:
            job = session.query(JobTable).filter_by(job_id=job_id).first()
            if job is None:
                raise JobNotFound(job_id)

            for column_name, column_value in column_dic.items():
                setattr(job, column_name, column_value)

    @classmethod
    def set_submitted(cls, job_id):
        """Update the 'submitted' column in the 'JobTable' for a given job ID.

        The method works as well as a lock so that the job is not submitted twice.

        Returns:
        bool: True if the job was successfully marked as submitted, False if it was
        already submitted.
        """
        log.debug(f"Set submitted for job: {job_id}")

        with cls.session_scope() as session:
            job = (
                session.query(JobTable)
                .filter_by(job_id=job_id)
                .with_for_update()
                .first()
            )
            if job is None:
                raise JobNotFound(job_id)

            if job.submitted and job.status in ["RUNNING", "COMPLETED"]:
                return False
            else:
                job.submitted = True
                return True

    @classmethod
    def get_job_columns(cls, job_id):
        """Retrieve all columns of a specific job entry based on its job ID."""
        log.debug(f"Get columns for job: {job_id}")

        with cls.session_scope() as session:
            job_row = session.query(JobTable).filter_by(job_id=job_id).first()

            if job_row is None:
                raise JobNotFound(job_id)

            job_columns = {
                column.name: getattr(job_row, column.name)
                for column in JobTable.__table__.columns
            }

        return job_columns

    @classmethod
    def delete_job(cls, job_id):
        """Delete a job entry from the database based on its job ID."""
        log.debug(f"Delete job: {job_id}")
        with cls.session_scope() as session:
            job = session.query(JobTable).filter_by(job_id=job_id).first()

            if job is None:
                raise JobNotFound(job_id)

            session.delete(job)

    @classmethod
    def list_jobs(cls):
        """List all jobs in the database with their submission date and status."""
        log.debug("List all jobs.")

        with cls.session_scope() as session:
            job_rows = session.query(JobTable).all()

            job_info = {}
            for job_row in job_rows:
                job_info[job_row.job_id] = {
                    "start_date": job_row.start_date,
                    "input_data": job_row.input_data,
                    "status": job_row.status,
                    "submitted": job_row.submitted,
                    "notified_end": job_row.notified_end,
                    "logs": job_row.logs,
                    "version": job_row.version,
                }
        return job_info


class JobTable(Base):
    """Represents the 'jobs' table in the database."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    start_date = Column("start_date", Date)
    input_data = Column("input_data", JSON)
    submitted = Column("submitted", Boolean)
    notified_end = Column("notified_end", Boolean)
    logs = Column("logs", String)
    status = Column("status", String)
    version = Column("version", String)


class LogTable(Base):
    """SQLAlchemy model for the logs table."""

    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=False), nullable=False)
    pid = Column(Integer, nullable=False)
    level = Column(String(10), nullable=False)
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary format."""
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": self.pid,
            "level": self.level,
            "message": self.message,
            "module": self.module,
        }


if __name__ == "__main__":
    DbManager.check_existence("test_job")
