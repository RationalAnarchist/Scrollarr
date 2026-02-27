from scrollarr.database import SessionLocal, Story, Chapter
from datetime import datetime

def seed_db():
    session = SessionLocal()
    try:
        # Check if story exists
        story = session.query(Story).filter_by(title="Verification Story").first()
        if not story:
            story = Story(
                title="Verification Story",
                author="Test Author",
                source_url="http://example.com/test",
                status="Ongoing",
                description="A test story for verification."
            )
            session.add(story)
            session.commit()

            # Add chapters
            c1 = Chapter(
                story_id=story.id,
                title="Chapter 1",
                source_url="http://example.com/test/1",
                index=1,
                status="downloaded",
                local_path="verification/dummy_c1.html" # Dummy path
            )
            c2 = Chapter(
                story_id=story.id,
                title="Chapter 2",
                source_url="http://example.com/test/2",
                index=2,
                status="failed"
            )
            session.add(c1)
            session.add(c2)
            session.commit()
            print(f"Seeded story ID: {story.id}")

            # Create dummy content file
            import os
            os.makedirs("verification", exist_ok=True)
            with open("verification/dummy_c1.html", "w") as f:
                f.write("<p>This is the <strong>content</strong> of Chapter 1.</p>")

    except Exception as e:
        print(f"Seeding failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_db()
