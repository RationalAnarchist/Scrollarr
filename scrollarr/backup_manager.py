import os
import shutil
import sqlite3
import datetime
import logging
from pathlib import Path
from .config import config_manager
from .database import engine

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_db_path(self):
        db_url = config_manager.get("database_url", "sqlite:///library.db")
        if db_url.startswith("sqlite"):
            db_path = db_url.replace("sqlite:///", "")
            return db_path
        return None

    def create_backup(self, is_auto: bool = False):
        db_path = self.get_db_path()
        if not db_path or not os.path.exists(db_path):
            raise ValueError("Unsupported or missing database for backup.")
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "library_backup_auto" if is_auto else "library_backup_manual"
        backup_filename = f"{prefix}_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        try:
            # Safe backup using sqlite3 api
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(str(backup_path))
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            logger.info(f"Database backup created successfully: {backup_path}")

            # Enforce retention policy: keep only the 5 most recent automatic backups
            if is_auto:
                try:
                    self.prune_auto_backups()
                except Exception as prune_e:
                    logger.warning(f"Failed to prune old backups: {prune_e}")

            return str(backup_filename)
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            raise e

    def prune_auto_backups(self):
        auto_backups = [b for b in self.list_backups() if b["is_auto"]]
        if len(auto_backups) > 5:
            for old_backup in auto_backups[5:]:
                self.delete_backup(old_backup["filename"])

    def list_backups(self):
        backups = []
        for file in self.backup_dir.glob("*.db"):
            stat = file.stat()
            # Differentiate auto vs manual. Any legacy backup without _auto_ is treated as manual/user-created.
            is_auto = "_auto_" in file.name
            backups.append({
                "filename": file.name,
                "size": stat.st_size,
                "created_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_auto": is_auto
            })
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups

    def restore_backup(self, filename: str):
        db_path = self.get_db_path()
        if not db_path:
            raise ValueError("Unsupported database for restore.")
            
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file {filename} not found.")
            
        try:
            logger.info(f"Checking integrity of backup {filename} before restoring...")
            # Verify and repair the backup file itself before restoring it
            from .database import check_and_repair_db
            check_and_repair_db(str(backup_path))

            logger.info(f"Restoring database from {filename}...")
            # Dispose of existing connections in the engine so the file isn't locked
            engine.dispose()
            
            # Use sqlite3 API to safely overwrite current db with backup
            src = sqlite3.connect(str(backup_path))
            dst = sqlite3.connect(db_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            
            # Clean up old journal/WAL files for the current db so they aren't replayed on the restored db
            for ext in ["-wal", "-shm"]:
                journal_file = db_path + ext
                if os.path.exists(journal_file):
                    try:
                        os.remove(journal_file)
                        logger.info(f"Removed journal file: {journal_file}")
                    except Exception as je:
                        logger.warning(f"Could not remove journal file {journal_file}: {je}")

            # Verify integrity of the newly restored active database
            check_and_repair_db(db_path)

            logger.info(f"Database successfully restored from {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup {filename}: {e}")
            raise e

    def delete_backup(self, filename: str):
        backup_path = self.backup_dir / filename
        if backup_path.exists():
            backup_path.unlink()
            logger.info(f"Deleted backup: {filename}")
            return True
        return False
