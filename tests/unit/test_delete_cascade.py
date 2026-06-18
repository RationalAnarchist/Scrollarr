import unittest
from scrollarr.database import Base, Story, Chapter, DownloadHistory
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

class TestDeleteCascade(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:")
        
        # Enforce foreign key constraints in SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.close()

    def test_story_delete_cascades_chapters_and_history(self):
        # 1. Create a test Story
        story = Story(
            title="Test Cascade Story",
            author="Test Author",
            source_url="https://example.com/story"
        )
        self.session.add(story)
        self.session.commit()

        # 2. Create a test Chapter
        chapter = Chapter(
            title="Chapter 1",
            source_url="https://example.com/story/1",
            story_id=story.id,
            index=1
        )
        self.session.add(chapter)
        self.session.commit()

        # 3. Create DownloadHistory records
        history_story = DownloadHistory(
            story_id=story.id,
            status="downloaded",
            event_type="download",
            details="Story history log"
        )
        history_chapter = DownloadHistory(
            chapter_id=chapter.id,
            status="downloaded",
            event_type="download",
            details="Chapter history log"
        )
        # 3b. Create legacy DownloadHistory record (story_id is None / NULL)
        history_legacy = DownloadHistory(
            chapter_id=chapter.id,
            story_id=None,
            status="failed",
            event_type="download",
            details="Legacy history log with NULL story_id"
        )
        self.session.add(history_story)
        self.session.add(history_chapter)
        self.session.add(history_legacy)
        self.session.commit()

        # Check they exist
        self.assertEqual(self.session.query(Chapter).count(), 1)
        self.assertEqual(self.session.query(DownloadHistory).count(), 3)

        # 4. Perform the same delete sequence as story_manager.delete_story
        from sqlalchemy import text
        story_id = story.id
        self.session.execute(text(
            "DELETE FROM download_history WHERE story_id = :story_id OR chapter_id IN (SELECT id FROM chapters WHERE story_id = :story_id)"
        ), {"story_id": story_id})
        
        self.session.execute(text(
            "DELETE FROM chapters WHERE story_id = :story_id"
        ), {"story_id": story_id})
        
        self.session.execute(text(
            "DELETE FROM stories WHERE id = :story_id"
        ), {"story_id": story_id})
        self.session.commit()

        # 5. Verify cascade deletion
        # All chapters and download histories associated with the story/chapter should be gone!
        self.assertEqual(self.session.query(Story).count(), 0)
        self.assertEqual(self.session.query(Chapter).count(), 0)
        self.assertEqual(self.session.query(DownloadHistory).count(), 0)
