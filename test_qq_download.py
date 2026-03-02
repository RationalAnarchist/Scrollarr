import logging
from scrollarr.database import SessionLocal, Story, Chapter
from scrollarr.story_manager import StoryManager

logging.basicConfig(level=logging.DEBUG)

manager = StoryManager()
session = SessionLocal()

# Mock story
story = session.query(Story).filter_by(id=999).first()
if not story:
    story = Story(id=999, title="Reaching the Apex", author="Author", source_url="https://forum.questionablequesting.com/threads/reaching-the-apex-pok%C3%A9mon-si.37130/")
    session.add(story)
    session.commit()

# Test check story updates
print("Checking updates...")
manager.check_story_updates(999)

# Test process images
print("Downloading missing chapters...")
manager.download_missing_chapters(999)

session.close()
