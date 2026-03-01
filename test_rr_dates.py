from scrollarr.sources.royalroad import RoyalRoadSource

source = RoyalRoadSource()
url = "https://www.royalroad.com/fiction/92144/the-legend-of-william-oh"

print("Fetching chapters...")
chapters = source.get_chapter_list(url)

print(f"Found {len(chapters)} chapters.")
if chapters:
    print("First 3 chapters:")
    for c in chapters[:3]:
        print(f" - {c['title']}: {c['published_date']} (Type: {type(c['published_date'])})")

    print("\nLast 3 chapters:")
    for c in chapters[-3:]:
        print(f" - {c['title']}: {c['published_date']} (Type: {type(c['published_date'])})")
else:
    print("No chapters found or failed to parse.")
