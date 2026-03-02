# Image Diagnostic Script

If you are experiencing issues with images not downloading or rendering (specifically with Questionable Questing or other XenForo proxies), please run this script directly inside your ScribDB Docker container.

This script will force the application to re-scan the HTML for the "Reaching the Apex" story, attempt the image download with `DEBUG` logging enabled, and tell us exactly which line is failing.

Run the following command from your host machine (replace `<your_container_name>` with your actual container name or ID):

```bash
docker exec -it <your_container_name> python3 -c "
import logging
from pathlib import Path
from scrollarr.database import SessionLocal, Story, Chapter
from scrollarr.story_manager import StoryManager

logging.basicConfig(level=logging.DEBUG)

# Initialize Manager
m = StoryManager()
session = SessionLocal()

# Find the Questionable Questing test story
story = session.query(Story).filter(Story.title.like('%Reaching the Apex%')).first()
if not story:
    print('Story not found. Have you added it to this container?')
    exit(1)

print(f'\nFound Story: {story.title} ({story.id})')
print('Forcing an image re-scan with DEBUG logging enabled...\n')

# Force a rescan of images
updated = m.scan_story_images(story.id)
print(f'\nDone. Updated {updated} chapters.')

# Check if the images directory was populated
images_dir = m.library_manager.get_images_dir(story)
print(f'Checking {images_dir}...')
if images_dir.exists():
    files = list(images_dir.iterdir())
    if files:
        print('SUCCESS! Found Images:', [f.name for f in files])
    else:
        print('FAILED: Images directory exists but is empty.')
else:
    print('FAILED: Images directory does not exist at all.')
"
```

### What to look for:
- If the output says `DEBUG: Downloaded image...` and `SUCCESS! Found Images...`, then the download logic is working perfectly in your environment, and the issue is likely that the web viewer is caching old HTML or the chapter wasn't redownloaded.
- If it prints a `WARNING:` or `ERROR:` trace, that output will tell us exactly why your specific network or Docker environment is rejecting the bypass.
