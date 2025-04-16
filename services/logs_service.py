import os
import logging
from datetime import datetime, timedelta
from app import db
from models import SystemLog

logger = logging.getLogger(__name__)

def log_to_db(message, level="INFO", module="System"):
    """
    Log a message to the database
    """
    try:
        log_entry = SystemLog(
            level=level,
            module=module,
            message=message
        )
        db.session.add(log_entry)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log to database: {str(e)}")
        return False

def get_latest_logs(limit=100):
    """
    Get the latest log entries from the database
    """
    try:
        logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs from database: {str(e)}")
        return []

def get_logs_by_level(level, limit=100):
    """
    Get log entries filtered by level
    """
    try:
        logs = SystemLog.query.filter_by(level=level).order_by(SystemLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs by level from database: {str(e)}")
        return []

def get_logs_by_timerange(start_time, end_time, limit=1000):
    """
    Get log entries within a specific time range
    """
    try:
        logs = SystemLog.query.filter(
            SystemLog.timestamp.between(start_time, end_time)
        ).order_by(SystemLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs by timerange from database: {str(e)}")
        return []

def get_error_count(hours=24):
    """
    Get count of errors in the last N hours
    """
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        count = SystemLog.query.filter(
            SystemLog.level == "ERROR",
            SystemLog.timestamp >= start_time
        ).count()
        return count
    except Exception as e:
        logger.error(f"Failed to get error count from database: {str(e)}")
        return 0

def clear_old_logs(days=30):
    """
    Clear logs older than specified number of days
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = SystemLog.query.filter(SystemLog.timestamp < cutoff_date).delete()
        db.session.commit()
        logger.info(f"Cleared {deleted} old log entries")
        return deleted
    except Exception as e:
        logger.error(f"Failed to clear old logs: {str(e)}")
        db.session.rollback()
        return 0
