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

chapters = session.query(Chapter).filter_by(story_id=999).all()
for c in chapters:
    c.status = "pending"
    c.is_downloaded = False
    c.local_path = None
session.commit()

print("Downloading missing chapters...")
manager.download_missing_chapters(999)

c = session.query(Chapter).filter_by(story_id=999).first()
with open(c.local_path, "r") as f:
    print("HTML HEAD:", f.read()[:1000])

import os
images_dir = f"/app/library/Reaching the Apex (999)/images"
if os.path.exists(images_dir):
    print("Images directory exists!")
    print(os.listdir(images_dir))
else:
    print("NO IMAGES DIRECTORY AT:", images_dir)
    print("Base library:")
    print(os.listdir("/app/library"))

session.close()
