from pathlib import Path
import os
import urllib.parse
from fastapi import HTTPException

def test_endpoint(chapter_local_path, src):
    decoded_src = urllib.parse.unquote(src)
    chapter_dir = Path(chapter_local_path).parent
    try:
        abs_img_path = (chapter_dir / decoded_src).resolve()
        print("abs_img_path:", abs_img_path)
    except Exception as e:
        print("Resolve error:", e)
        return

    lib_root = Path("/app/library").resolve()
    print("lib_root:", lib_root)

    if not str(abs_img_path).startswith(str(lib_root)):
        print("403 Access denied")
        return

    if not abs_img_path.exists():
        print("404 Image not found")
        return

    print("200 OK FileResponse")

os.makedirs("/app/library/Reaching the Apex (1)/chapters/Volume 1", exist_ok=True)
os.makedirs("/app/library/Reaching the Apex (1)/images", exist_ok=True)
with open("/app/library/Reaching the Apex (1)/images/img_eb990a0b_1.jpg", "w") as f:
    f.write("test")

test_endpoint("/app/library/Reaching the Apex (1)/chapters/Volume 1/1.html", "../../images/img_eb990a0b_1.jpg")
