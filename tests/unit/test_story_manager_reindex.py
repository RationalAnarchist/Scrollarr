import unittest
from datetime import datetime
from scrollarr.database import Base, Story, Chapter
from scrollarr.story_manager import StoryManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestStoryManagerReindex(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()
        
        # Instantiate StoryManager
        self.sm = StoryManager()

    def tearDown(self):
        self.session.close()

    def test_reindex_chapters_fallback_sorting(self):
        # Create a test story
        story = Story(
            title="Test Story",
            author="Author",
            source_url="https://www.fanfiction.net/s/9138187/1/Fixations"
        )
        self.session.add(story)
        self.session.commit()

        # Insert chapters out of order (simulating the FFN sorting bug)
        # We put Chapter 2 to 5 first with None dates, then Chapter 1 with a date
        chapters = [
            Chapter(title="Chapter 2", source_url="https://www.fanfiction.net/s/9138187/2", story_id=story.id, index=1, published_date=None),
            Chapter(title="Chapter 3", source_url="https://www.fanfiction.net/s/9138187/3", story_id=story.id, index=2, published_date=None),
            Chapter(title="Chapter 1", source_url="https://www.fanfiction.net/s/9138187/1", story_id=story.id, index=3, published_date=datetime(2013, 3, 26)),
            Chapter(title="Chapter 4", source_url="https://www.fanfiction.net/s/9138187/4", story_id=story.id, index=4, published_date=None)
        ]
        
        for c in chapters:
            self.session.add(c)
        self.session.commit()

        # Run reindexing
        self.sm._reindex_chapters(story.id, self.session)
        self.session.commit()

        # Fetch chapters and verify they are correctly indexed in order: 1, 2, 3, 4
        db_chapters = self.session.query(Chapter).filter(Chapter.story_id == story.id).order_by(Chapter.index).all()
        
        self.assertEqual(len(db_chapters), 4)
        self.assertEqual(db_chapters[0].title, "Chapter 1")
        self.assertEqual(db_chapters[0].index, 1)
        
        self.assertEqual(db_chapters[1].title, "Chapter 2")
        self.assertEqual(db_chapters[1].index, 2)
        
        self.assertEqual(db_chapters[2].title, "Chapter 3")
        self.assertEqual(db_chapters[2].index, 3)
        
        self.assertEqual(db_chapters[3].title, "Chapter 4")
        self.assertEqual(db_chapters[3].index, 4)
