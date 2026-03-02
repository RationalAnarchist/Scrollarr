import urllib.parse
from bs4 import BeautifulSoup

content = '<img alt="Reaching the Apex, Cover" class="bbImage" data-url="https://i.postimg.cc/rp1DM4sv/cover.png" data-zoom-target="1" height="" src="/proxy.php?image=https%3A%2F%2Fi.postimg.cc%2Frp1DM4sv%2Fcover.png&amp;hash=33ae29f01619800ecbdaff4b5d6d717e" style="width: 283px" title="Reaching the Apex, Cover" width=""/>'
chapter_id = 1

soup = BeautifulSoup(content, 'html.parser')
images = soup.find_all('img')
modified = False

if images:
    for img in images:
        src = img.get('src')
        if not src:
            continue
        if not src.startswith('http') and not src.startswith('data:'):
            encoded_src = urllib.parse.quote(src)
            img['src'] = f"/api/chapter/{chapter_id}/image?src={encoded_src}"
            modified = True

if modified:
    print("Modified HTML:")
    print(str(soup))
else:
    print("Not modified!")
