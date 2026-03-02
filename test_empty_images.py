from bs4 import BeautifulSoup
content = '<b>Disclaimer:</b> Pokémon...<img alt="Reaching the Apex, Cover" class="bbImage" data-url="https://i.postimg.cc/rp1DM4sv/cover.png" data-zoom-target="1" height="" src="/proxy.php?image=https%3A%2F%2Fi.postimg.cc%2Frp1DM4sv%2Fcover.png&amp;hash=33ae29f01619800ecbdaff4b5d6d717e" style="width: 283px" title="Reaching the Apex, Cover" width=""/>'
soup = BeautifulSoup(content, 'html.parser')
images = soup.find_all('img')
print(f"Found {len(images)} images.")
