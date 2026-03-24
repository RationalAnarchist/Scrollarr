import logging
import time
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from .database import SessionLocal, Story, Chapter, DownloadHistory, init_db
from .story_manager import StoryManager
from .notifications import NotificationManager
from .config import config_manager
from .library_manager import LibraryManager
from .discord_integration import fetch_discord_epub_metadata, download_discord_epub

# Configure logging
logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.story_manager = StoryManager()
        self.notification_manager = NotificationManager()
        self.library_manager = LibraryManager()
        self.running = False
        self.task_status = {} # {task_id: {last_run, duration, status, next_run}}

    def _track_job(self, job_name, func):
        """
        Wrapper to track job execution status and log to DB.
        """
        def wrapper():
            start_time = time.time()
            status = "Success"
            error_details = None

            try:
                # Log start
                logger.info(f"Starting job: {job_name}")
                func()
            except Exception as e:
                status = "Failed"
                error_details = str(e)
                logger.error(f"Job {job_name} failed: {e}")
            finally:
                end_time = time.time()
                duration = end_time - start_time

                # Update in-memory status
                self.task_status[job_name] = {
                    "last_run": datetime.now().isoformat(),
                    "duration": f"{duration:.2f}s",
                    "status": status,
                    "next_run": self._get_next_run_time(job_name)
                }

                # Log to DB
                session = SessionLocal()
                try:
                    history = DownloadHistory(
                        event_type='system',
                        status=status,
                        details=f"Task: {job_name}. {error_details if error_details else ''}"
                    )
                    session.add(history)
                    session.commit()
                except Exception as e:
                    logger.error(f"Failed to log task history: {e}")
                finally:
                    session.close()

        return wrapper

    def _get_next_run_time(self, job_id):
        job = self.scheduler.get_job(job_id)
        if job and job.next_run_time:
             return job.next_run_time.isoformat()
        return None

    def get_tasks(self):
        """Returns the current status of all tracked tasks."""
        tasks = []
        # Defined tasks and their readable names
        defined_tasks = {
            'check_updates': {'name': 'Check for Updates', 'interval': f"{config_manager.get('update_interval_hours', 1)} hours"},
            'download_queue': {'name': 'Process Download Queue', 'interval': f"{config_manager.get('worker_sleep_min', 30.0)} seconds"},
            'check_metadata': {'name': 'Check Missing Metadata', 'interval': '12 hours'},
            'check_discord': {'name': 'Check Discord for Updates', 'interval': f"{config_manager.get('discord_check_interval_hours', 1)} hours"}
        }

        for task_id, info in defined_tasks.items():
            status = self.task_status.get(task_id, {})
            # Get next run time from scheduler if not in status (e.g. before first run)
            next_run = status.get('next_run') or self._get_next_run_time(task_id)

            tasks.append({
                "id": task_id,
                "name": info['name'],
                "interval": info['interval'],
                "last_run": status.get("last_run", "Never"),
                "duration": status.get("duration", "0s"),
                "status": status.get("status", "Pending"),
                "next_run": next_run
            })
        return tasks

    def trigger_task(self, task_id):
        """Manually triggers a task."""
        job = self.scheduler.get_job(task_id)
        if job:
            job.modify(next_run_time=datetime.now())
            return True
        return False

    def start(self):
        """Starts the scheduler with configured jobs."""
        init_db()
        self.running = True
        self.update_jobs()
        self.scheduler.start()

        # Schedule immediate run of metadata check on startup
        from datetime import datetime, timedelta
        self.scheduler.add_job(
            self._track_job('check_metadata', self.check_missing_metadata),
            'date',
            run_date=datetime.now() + timedelta(seconds=10),
            id='check_metadata_startup'
        )

        # Schedule immediate run of updates check on startup
        self.scheduler.add_job(
            self._track_job('check_updates', self.check_for_updates),
            'date',
            run_date=datetime.now() + timedelta(seconds=20),
            id='check_updates_startup'
        )

        # Schedule immediate run of Discord check on startup
        if config_manager.get('discord_token'):
            self.scheduler.add_job(
                self._track_job('check_discord', self.check_discord_updates),
                'date',
                run_date=datetime.now() + timedelta(seconds=30),
                id='check_discord_startup'
            )

        logger.info("JobManager started.")

    def stop(self):
        """Stops the scheduler."""
        self.running = False
        if self.scheduler.running:
            self.scheduler.shutdown()
        logger.info("JobManager stopped.")

    def pause(self):
        """Pauses the scheduler and stops running jobs."""
        self.running = False
        if self.scheduler.running:
            self.scheduler.pause()
        logger.info("JobManager paused.")

    def resume(self):
        """Resumes the scheduler."""
        self.running = True
        if self.scheduler.running:
            self.scheduler.resume()
        else:
            self.start()
        logger.info("JobManager resumed.")

    def update_jobs(self):
        """Updates or adds jobs based on current configuration."""
        # Update Job
        update_interval = config_manager.get("update_interval_hours", 1)
        # APScheduler handles replace_existing=True gracefully
        self.scheduler.add_job(
            self._track_job('check_updates', self.check_for_updates),
            'interval',
            hours=update_interval,
            id='check_updates',
            replace_existing=True
        )

        # Download Job
        # worker.py slept random(min, max). We'll use min as the base interval.
        download_interval = config_manager.get("worker_sleep_min", 30.0)

        self.scheduler.add_job(
            self._track_job('download_queue', self.process_download_queue),
            'interval',
            seconds=download_interval,
            id='download_queue',
            max_instances=1, # Prevent overlap
            replace_existing=True
        )

        # Metadata Check Job
        # Run infrequently, e.g., every 12 hours
        self.scheduler.add_job(
            self._track_job('check_metadata', self.check_missing_metadata),
            'interval',
            hours=12,
            id='check_metadata',
            replace_existing=True
        )

        # Discord Check Job
        discord_token = config_manager.get('discord_token')
        if discord_token:
            discord_interval = config_manager.get('discord_check_interval_hours', 1)
            self.scheduler.add_job(
                self._track_job('check_discord', self.check_discord_updates),
                'interval',
                hours=discord_interval,
                id='check_discord',
                replace_existing=True
            )
            logger.info(f"Jobs updated: check_updates (every {update_interval}h), download_queue (every {download_interval}s), check_metadata (every 12h), check_discord (every {discord_interval}h)")
        else:
            # Remove job if token was removed
            if self.scheduler.get_job('check_discord'):
                self.scheduler.remove_job('check_discord')
            logger.info(f"Jobs updated: check_updates (every {update_interval}h), download_queue (every {download_interval}s), check_metadata (every 12h)")

        for job in self.scheduler.get_jobs():
            logger.info(f"Scheduled job: {job}")

    def check_missing_metadata(self):
        """
        Checks for missing metadata in stories and attempts to retrieve it.
        """
        logger.info("Running scheduled metadata check...")
        self.story_manager.fill_missing_metadata()

    def check_for_updates(self):
        """
        Checks for updates for all monitored stories.
        Fetches the latest chapter list and adds new chapters to the database.
        """
        logger.info("Checking for updates...")
        session = SessionLocal()

        try:
            # Only get IDs to close session early and avoid holding it during network requests
            monitored_story_ids = [s.id for s in session.query(Story).filter(Story.is_monitored == True).all()]
        except Exception as e:
            logger.error(f"Error fetching monitored stories: {e}")
            monitored_story_ids = []
        finally:
            session.close()

        for story_id in monitored_story_ids:
            if not self.running:
                logger.info("Stopping update check due to shutdown signal.")
                break

            try:
                self.story_manager.check_story_updates(story_id)
            except Exception as e:
                logger.error(f"Error updating story {story_id}: {e}")

    def check_discord_updates(self):
        """
        Checks configured Discord channels for new EPUB attachments
        and adds them as chapters to the corresponding stories.
        """
        token = config_manager.get('discord_token')
        if not token:
            logger.info("Discord token not configured. Skipping Discord check.")
            return

        logger.info("Checking Discord for updates...")
        session = SessionLocal()

        try:
            # Get monitored stories that have a discord channel set
            stories = session.query(Story).filter(
                Story.is_monitored == True,
                Story.discord_channel_id != None,
                Story.discord_channel_id != ""
            ).all()

            # Group stories by channel ID to minimize API calls
            channels_to_stories = {}
            for story in stories:
                channel_id = story.discord_channel_id
                if channel_id not in channels_to_stories:
                    channels_to_stories[channel_id] = []
                channels_to_stories[channel_id].append(story)
        except Exception as e:
            logger.error(f"Error fetching Discord-monitored stories: {e}")
            return
        finally:
            session.close()

        for channel_id, channel_stories in channels_to_stories.items():
            if not self.running:
                logger.info("Stopping Discord check due to shutdown signal.")
                break

            try:
                logger.info(f"Fetching recent messages for Discord channel {channel_id}")
                recent_epubs = fetch_discord_epub_metadata(channel_id, token)

                if not recent_epubs:
                    logger.debug(f"No new EPUBs found in channel {channel_id}")
                    continue

                for epub_info in recent_epubs:
                    filename = epub_info['filename']
                    # Use filename without extension as the chapter title to match traditional sources better,
                    # or keep it as filename. The standard is to compare based on what the source provides.
                    # We'll pass the filename, but story manager will check duplicates.

                    # 1. Determine which stories need this EPUB
                    stories_needing_epub = []
                    session = SessionLocal()
                    try:
                        for story in channel_stories:
                            # Re-fetch story to get current chapters
                            db_story = session.query(Story).filter(Story.id == story.id).first()
                            if not db_story: continue

                            # Check for duplicates. Strip .epub for checking against traditional sources which usually
                            # don't have .epub in the chapter title.
                            clean_title = filename
                            if clean_title.lower().endswith('.epub'):
                                clean_title = clean_title[:-5]

                            existing = next((c for c in db_story.chapters if c.title == clean_title or c.title == filename), None)
                            if not existing:
                                stories_needing_epub.append(db_story)
                    finally:
                        session.close()

                    # 2. Download ONCE if at least one story needs it
                    if stories_needing_epub:
                        logger.info(f"EPUB '{filename}' is new for {len(stories_needing_epub)} stories. Downloading...")
                        downloaded_path = None
                        try:
                            downloaded_path = download_discord_epub(epub_info['url'], filename)

                            # 3. Import into each story
                            for db_story in stories_needing_epub:
                                logger.info(f"Importing {filename} into story '{db_story.title}'")
                                self.story_manager.import_discord_epub(db_story.id, downloaded_path, filename)

                        except Exception as e:
                            logger.error(f"Failed to download or import {filename}: {e}")
                        finally:
                            # 4. Cleanup the temporary file ONCE after all imports are done
                            if downloaded_path and os.path.exists(downloaded_path):
                                try:
                                    os.remove(downloaded_path)
                                    logger.debug(f"Cleaned up temporary file {downloaded_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to clean up {downloaded_path}: {e}")
            except Exception as e:
                logger.error(f"Error processing Discord channel {channel_id}: {e}")

    def process_download_queue(self):
        """
        Downloads pending chapters until queue is empty.
        """
        logger.info("Checking download queue for pending chapters...")

        # Track downloaded chapters per story for batch compilation
        downloaded_chapters = {} # {story_id: [chapter_obj, ...]}

        while self.running:
            session = SessionLocal()
            try:
                # Prioritize stories with fewer pending chapters
                # 1. Count pending chapters per story
                subquery = (
                    session.query(Chapter.story_id, func.count(Chapter.id).label('pending_count'))
                    .filter(Chapter.status == 'pending')
                    .group_by(Chapter.story_id)
                    .subquery()
                )

                # 2. Find the story with the fewest pending chapters
                best_story_row = (
                    session.query(subquery.c.story_id)
                    .order_by(subquery.c.pending_count.asc())
                    .first()
                )

                chapter = None
                if best_story_row:
                    # 3. Get the oldest pending chapter for that story
                    chapter = (
                        session.query(Chapter)
                        .filter(Chapter.story_id == best_story_row.story_id, Chapter.status == 'pending')
                        .order_by(Chapter.id.asc())
                        .with_for_update()
                        .first()
                    )

                # Fallback to global oldest if priority selection fails (e.g. race condition)
                if not chapter:
                    # Query the database for the single oldest chapter where status == 'pending'
                    # Use with_for_update() to lock the row if possible
                    chapter = session.query(Chapter).filter(Chapter.status == 'pending').order_by(Chapter.id.asc()).with_for_update().first()

                if not chapter:
                    # No more chapters
                    logger.debug("No pending chapters found.")
                    break

                story = chapter.story
                logger.info(f"Processing chapter: {chapter.title} (ID: {chapter.id}) from story: {story.title}")

                try:
                    # The Download: Use the provider to get the content.
                    provider = self.story_manager.source_manager.get_provider_for_url(story.source_url)
                    if not provider:
                         raise ValueError(f"No provider found for story URL: {story.source_url}")

                    content = provider.get_chapter_content(chapter.source_url)

                    # Use LibraryManager for path
                    filepath = self.library_manager.get_chapter_absolute_path(story, chapter)
                    self.library_manager.ensure_directories(filepath.parent)

                    # Process images
                    content = self.story_manager._process_chapter_images(content, story, filepath)

                    # Write file to disk
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)

                    # The Update: Once the file is written to disk, update the status from pending to downloaded.
                    chapter.local_path = str(filepath)
                    chapter.is_downloaded = True
                    chapter.status = 'downloaded'

                    history = DownloadHistory(
                        chapter_id=chapter.id,
                        story_id=story.id,
                        status='downloaded',
                        details=f"Downloaded successfully to {os.path.basename(filepath)}"
                    )
                    session.add(history)

                    session.commit()
                    logger.info(f"Successfully downloaded: {chapter.title}")

                    # Track for batch compilation (using detached object attributes)
                    # We create a simple copy to avoid session issues
                    from types import SimpleNamespace
                    chapter_info = SimpleNamespace(
                        id=chapter.id,
                        title=chapter.title,
                        index=chapter.index,
                        volume_number=chapter.volume_number,
                        volume_title=chapter.volume_title,
                        local_path=chapter.local_path
                    )

                    if story.id not in downloaded_chapters:
                        downloaded_chapters[story.id] = []
                    downloaded_chapters[story.id].append(chapter_info)

                    # Check for remaining pending/failed chapters for this story
                    remaining_count = session.query(Chapter).filter(
                        Chapter.story_id == story.id,
                        Chapter.status.in_(['pending', 'failed'])
                    ).count()

                    if remaining_count == 0:
                        logger.info(f"Story {story.title} download complete (no pending/failed chapters). Compiling ebook...")

                        try:
                            # Compile ebook
                            from .ebook_builder import EbookBuilder
                            builder = EbookBuilder()

                            batch = downloaded_chapters.get(story.id, [])
                            batch.sort(key=lambda x: x.index if hasattr(x, 'index') and x.index is not None else -1)

                            total_chapters = session.query(Chapter).filter(Chapter.story_id == story.id).count()

                            # Determine type
                            file_type = 'group'
                            msg_title = "New Chapters"
                            ebook_path = ""

                            # If batch covers almost all chapters (allow small margin for retries?), treat as full
                            if len(batch) >= total_chapters:
                                file_type = 'full'
                                msg_title = "Full Story Download"
                                ebook_path = builder.compile_full_story(story.id)
                            else:
                                if len(batch) == 1:
                                    file_type = 'single'
                                    msg_title = f"New Chapter: {batch[0].title}"
                                else:
                                    file_type = 'group'
                                    msg_title = f"New Chapters ({len(batch)})"

                                if batch:
                                    ebook_path = builder.compile_custom_range(story.id, batch, file_type=file_type)
                                else:
                                    # Fallback if batch empty (should not happen in normal flow)
                                    logger.warning("Batch empty but remaining count 0. Compiling full story.")
                                    file_type = 'full'
                                    ebook_path = builder.compile_full_story(story.id)

                            logger.info(f"Ebook compiled at {ebook_path} (Type: {file_type})")

                            # Notify success
                            self.notification_manager.dispatch('on_download', {
                                'story_title': story.title,
                                'chapter_title': msg_title,
                                'chapter_id': chapter.id,
                                'story_id': story.id,
                                'file_path': ebook_path,
                                'new_chapters_count': len(batch)
                            })

                            # Clear batch for this story
                            if story.id in downloaded_chapters:
                                del downloaded_chapters[story.id]

                        except Exception as e:
                            logger.error(f"Failed to compile ebook: {e}")
                            self.notification_manager.dispatch('on_failure', {
                                'story_title': story.title,
                                'chapter_title': "Ebook Compilation",
                                'story_id': story.id,
                                'error': f"Failed to compile ebook: {str(e)}"
                            })
                    else:
                        logger.debug(f"Story {story.title} has {remaining_count} remaining items. Skipping notification.")

                except Exception as e:
                    logger.error(f"Failed to download chapter {chapter.title}: {e}")
                    # Error Handling: If the download fails, change the status to failed so we can track it.
                    chapter.status = 'failed'

                    history = DownloadHistory(
                        chapter_id=chapter.id,
                        story_id=story.id,
                        status='failed',
                        details=str(e)
                    )
                    session.add(history)

                    session.commit()

                    # Notify failure
                    self.notification_manager.dispatch('on_failure', {
                        'story_title': story.title,
                        'chapter_title': chapter.title,
                        'chapter_id': chapter.id,
                        'story_id': story.id,
                        'error': str(e)
                    })

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                session.rollback()
                # Break to avoid infinite loop on DB error
                break
            finally:
                session.close()

        logger.info("Download queue empty or processing stopped.")
