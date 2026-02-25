import os
import unittest
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scrollarr.database import Base, EbookProfile, Chapter, Story
from scrollarr.story_manager import StoryManager

class TestManualInteraction(unittest.TestCase):
    def setUp(self):
        # Create a clean in-memory database for this test
        self.test_engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=self.test_engine)
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)

        # Patch SessionLocal in story_manager so it uses our test DB
        self.sm_session_patcher = patch('scrollarr.story_manager.SessionLocal', self.TestSessionLocal)
        self.sm_session_patcher.start()

        # Create default profile (ID=1) using our test session
        session = self.TestSessionLocal()
        try:
            profile = EbookProfile(name="Standard", output_format="epub")
            session.add(profile)
            session.commit()
        finally:
            session.close()

        # Patch init_db to avoid migration errors/re-init in test environment
        with patch('scrollarr.story_manager.init_db'):
            self.manager = StoryManager()

        # Mock provider
        self.mock_provider = MagicMock()
        self.mock_provider.get_metadata.return_value = {
            'title': 'Test Story',
            'author': 'Test Author',
            'cover_url': 'http://example.com/cover.jpg'
        }
        self.mock_provider.get_chapter_list.return_value = [
            {'title': 'Chapter 1', 'url': 'http://example.com/1'},
            {'title': 'Chapter 2', 'url': 'http://example.com/2'}
        ]

        # Inject mock provider
        self.manager.source_manager.get_provider_for_url = MagicMock(return_value=self.mock_provider)

    def tearDown(self):
        self.sm_session_patcher.stop()

    def test_check_story_updates(self):
        # 1. Add story with 2 chapters
        story_id = self.manager.add_story("http://example.com/story")

        # 2. Update provider to have 3 chapters
        self.mock_provider.get_chapter_list.return_value = [
            {'title': 'Chapter 1', 'url': 'http://example.com/1'},
            {'title': 'Chapter 2', 'url': 'http://example.com/2'},
            {'title': 'Chapter 3', 'url': 'http://example.com/3'}
        ]

        # 3. Call check_story_updates
        new_count = self.manager.check_story_updates(story_id)

        # 4. Verify
        self.assertEqual(new_count, 1)

        session = self.TestSessionLocal()
        chapters = session.query(Chapter).filter(Chapter.story_id == story_id).all()
        self.assertEqual(len(chapters), 3)
        session.close()

    def test_retry_failed_chapters(self):
        # 1. Add story
        story_id = self.manager.add_story("http://example.com/story")

        # 2. Mark a chapter as failed
        session = self.TestSessionLocal()
        chapter = session.query(Chapter).filter(Chapter.story_id == story_id, Chapter.index == 1).first()
        chapter.status = 'failed'
        session.commit()
        session.close()

        # 3. Call retry
        count = self.manager.retry_failed_chapters(story_id)

        # 4. Verify
        self.assertEqual(count, 1)

        session = self.TestSessionLocal()
        chapter = session.query(Chapter).filter(Chapter.story_id == story_id, Chapter.index == 1).first()
        self.assertEqual(chapter.status, 'pending')
        session.close()

if __name__ == '__main__':
    unittest.main()
