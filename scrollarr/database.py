import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, text, DateTime, inspect, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.sql import func
from typing import Optional
from .core_logic import SourceManager
from .sources.royalroad import RoyalRoadSource
from .sources.patreon import PatreonSource
from .config import config_manager
import alembic.config
import alembic.command

Base = declarative_base()


class Story(Base):
    __tablename__ = 'stories'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    source_url = Column(String, unique=True, nullable=False)
    cover_path = Column(String, nullable=True)
    monitored = Column(Boolean, default=True)
    is_monitored = Column(Boolean, default=True)
    last_updated = Column(DateTime, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    status = Column(String, default='Monitoring')
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    rating = Column(String, nullable=True)
    language = Column(String, nullable=True)
    publication_status = Column(String, default='Unknown')
    profile_id = Column(Integer, ForeignKey('ebook_profiles.id'), nullable=True)
    provider_name = Column(String, nullable=True)
    notify_on_new_chapter = Column(Boolean, default=True)
    alternative_source_url = Column(String, nullable=True)

    chapters = relationship("Chapter", back_populates="story", cascade="all, delete-orphan")
    profile = relationship("EbookProfile")
    download_histories = relationship("DownloadHistory", back_populates="story", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Story(title='{self.title}', author='{self.author}')>"

class Chapter(Base):
    __tablename__ = 'chapters'

    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=False)
    title = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    local_path = Column(String, nullable=True)
    is_downloaded = Column(Boolean, default=False)
    volume_number = Column(Integer, default=1)
    volume_title = Column(String, nullable=True)
    index = Column(Integer, nullable=True)
    status = Column(String, default='pending')
    published_date = Column(DateTime, nullable=True)
    tags = Column(String, nullable=True)

    story = relationship("Story", back_populates="chapters")
    download_histories = relationship("DownloadHistory", back_populates="chapter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chapter(title='{self.title}', story_id={self.story_id})>"

class DownloadHistory(Base):
    __tablename__ = 'download_history'

    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey('chapters.id'), nullable=True)
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=True)
    status = Column(String, nullable=False)  # 'downloaded', 'failed'
    event_type = Column(String, default='download', server_default='download') # 'download', 'system', 'error'
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(String, nullable=True)

    chapter = relationship("Chapter", back_populates="download_histories")
    story = relationship("Story", back_populates="download_histories")

    def __repr__(self):
        return f"<DownloadHistory(chapter_id={self.chapter_id}, status='{self.status}')>"

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    key = Column(String, unique=True, nullable=False)
    is_enabled = Column(Boolean, default=True)
    config = Column(String, nullable=True)

    def __repr__(self):
        return f"<Source(name='{self.name}', enabled={self.is_enabled})>"

class EbookProfile(Base):
    __tablename__ = 'ebook_profiles'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    css = Column(String, nullable=True)
    output_format = Column(String, default='epub')
    pdf_page_size = Column(String, default='A4')

    def __repr__(self):
        return f"<EbookProfile(name='{self.name}')>"

class NotificationSettings(Base):
    __tablename__ = 'notification_settings'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False) # 'webhook', 'email'
    target = Column(String, nullable=False) # URL or Email
    events = Column(String, default='') # Comma-separated: 'download,failure,new_chapters'
    attach_file = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    def __repr__(self):
        return f"<NotificationSettings(name='{self.name}', kind='{self.kind}')>"

# Setup database
# Priority: Environment Variable > Config file > Default
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    DB_URL = config_manager.get("database_url", "sqlite:///library.db")

connect_args = {}
if DB_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DB_URL, connect_args=connect_args)

if DB_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def run_migrations():
    """Run Alembic migrations programmatically."""
    print("Checking for database migrations...")

    # Locate alembic.ini
    alembic_ini_path = os.path.join(os.getcwd(), "config", "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        print(f"Warning: alembic.ini not found at {alembic_ini_path}. Skipping migrations.")
        return

    alembic_cfg = alembic.config.Config(alembic_ini_path)


    print("Running alembic upgrade head...")
    try:
        alembic.command.upgrade(alembic_cfg, "head")
        print("Migrations completed.")
    except Exception as e:
        print(f"Error running migrations: {e}")
        raise e

def check_and_repair_db(db_path: str):
    """Checks the database integrity and performs automatic self-healing if corrupted."""
    import sqlite3
    import shutil

    if not os.path.exists(db_path):
        return

    print(f"Checking database integrity for {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchall()
        conn.close()

        if result == [('ok',)]:
            print("Database integrity check: OK")
            return

        print(f"CRITICAL: Database corruption detected in {db_path}! Result: {result}")
        print("Attempting automatic self-healing database recovery...")

        backup_path = db_path + ".bak"
        recovered_path = db_path + ".recovered"

        # 1. Back up the corrupted database (overwriting any previous backup)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(db_path, backup_path)

        # 2. Connect to the backup database to dump (safe from WAL locks)
        conn = sqlite3.connect(backup_path)
        print("Dumping schema and data to SQL script...")
        sql_dump = []
        for line in conn.iterdump():
            if line.startswith("BEGIN TRANSACTION") or line.startswith("COMMIT"):
                continue
            sql_dump.append(line)
        conn.close()

        # 3. Create fresh recovered database
        if os.path.exists(recovered_path):
            os.remove(recovered_path)

        new_conn = sqlite3.connect(recovered_path)
        new_cursor = new_conn.cursor()

        # Replay the SQL statements
        new_cursor.execute("BEGIN TRANSACTION;")
        for statement in sql_dump:
            try:
                new_cursor.execute(statement)
            except sqlite3.Error as e:
                # Skip duplicate keys or errors safely
                if "UNIQUE constraint failed" not in str(e):
                    print(f"Warning during self-healing: Skipped statement due to error: {e}")
        new_conn.commit()

        # 4. Verify integrity of the recovered database
        new_cursor.execute("PRAGMA integrity_check")
        recovered_result = new_cursor.fetchall()
        new_conn.close()

        if recovered_result == [('ok',)]:
            print("Integrity check of rebuilt database PASSED!")
            print("Applying self-healed database...")

            # Remove old DB and journal files
            if os.path.exists(db_path):
                os.remove(db_path)
            for ext in ["-wal", "-shm"]:
                journal_file = db_path + ext
                if os.path.exists(journal_file):
                    os.remove(journal_file)

            # Swap
            os.rename(recovered_path, db_path)
            print("Database self-healing completed successfully! Database is now healthy.")
        else:
            print(f"ERROR: Rebuilt database failed integrity check: {recovered_result}")
            if os.path.exists(recovered_path):
                os.remove(recovered_path)

    except Exception as e:
        print(f"Failed to perform self-healing database recovery: {e}")

def init_db(engine=engine):
    """Creates the database tables and runs migrations."""
    if os.getenv("DEFER_DB_INIT") == "true":
        print("Database initialization deferred by DEFER_DB_INIT environment variable.")
        return

    # Check and repair database if it's SQLite
    if DB_URL.startswith("sqlite:///"):
        db_path = DB_URL.split("sqlite:///")[1]
        if db_path and db_path != ":memory:":
            check_and_repair_db(db_path)
            
    # We now rely on Alembic to create tables and manage schema
    run_migrations()

    # Create a database backup on startup
    try:
        from .backup_manager import BackupManager
        backup_mgr = BackupManager()
        print("Creating automatic database backup on startup...")
        backup_mgr.create_backup()
    except Exception as backup_e:
        print(f"Failed to create automatic startup backup: {backup_e}")

def sync_story(url: str, session: Optional[Session] = None):
    """
    Fetches the latest chapters for the story at the given URL and updates the database.
    """
    # 1. Setup SourceManager
    manager = SourceManager()
    manager.register_provider(RoyalRoadSource())
    manager.register_provider(PatreonSource())

    # 2. Get Provider
    provider = manager.get_provider_for_url(url)
    if not provider:
        raise ValueError(f"No provider found for URL: {url}")

    # 3. Fetch Data
    metadata = provider.get_metadata(url)
    chapters_data = provider.get_chapter_list(url)

    # 4. Update Database
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        # Check if story exists
        story = session.query(Story).filter(Story.source_url == url).first()

        if not story:
            story = Story(
                title=metadata.get('title', 'Unknown'),
                author=metadata.get('author', 'Unknown'),
                source_url=url,
                cover_path=None,
                status='Monitoring'
            )
            session.add(story)
            session.flush() # Ensure ID is available
        else:
            # Update metadata if needed
            story.title = metadata.get('title', story.title)
            story.author = metadata.get('author', story.author)

        # If story is new, story.chapters is empty.
        # If story exists, story.chapters contains current DB chapters.
        existing_chapters = {}
        if story.chapters:
             existing_chapters = {c.source_url: c for c in story.chapters}

        new_chapters_count = 0
        for i, chapter_data in enumerate(chapters_data):
            chapter_url = chapter_data['url']
            chapter_title = chapter_data['title']

            if chapter_url not in existing_chapters:
                new_chapter = Chapter(
                    title=chapter_title,
                    source_url=chapter_url,
                    index=i + 1
                )
                # Associate with story
                story.chapters.append(new_chapter)
                new_chapters_count += 1
            else:
                # Update index if it's missing or changed
                existing_chap = existing_chapters[chapter_url]
                if existing_chap.index != i + 1:
                    existing_chap.index = i + 1

        if new_chapters_count > 0:
            story.last_updated = func.now()

        session.commit()

    except Exception as e:
        session.rollback()
        raise e
    finally:
        if should_close:
            session.close()

if __name__ == "__main__":
    init_db()
