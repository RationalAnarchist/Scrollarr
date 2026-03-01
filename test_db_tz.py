from sqlalchemy import create_engine, Column, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import json

Base = declarative_base()

class TestModel(Base):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    published_date = Column(DateTime)

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

session = SessionLocal()

# Simulate Royal Road parsing (timezone aware)
dt_aware = datetime.fromisoformat('2026-02-23T19:38:58Z'.replace('Z', '+00:00'))

# Insert
obj = TestModel(published_date=dt_aware)
session.add(obj)
session.commit()

# Retrieve
retrieved = session.query(TestModel).first()

print(f"Retrieved Type: {type(retrieved.published_date)}")
print(f"Retrieved Value: {retrieved.published_date}")
print(f"Isoformat: {retrieved.published_date.isoformat()}")

try:
    events = [{'start': retrieved.published_date.isoformat()}]
    print("JSON serialize:", json.dumps(events))
except Exception as e:
    print(f"JSON Error: {e}")

session.close()
