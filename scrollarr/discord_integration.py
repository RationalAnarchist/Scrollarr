import requests
import logging
import os
import tempfile
import uuid
from typing import List, Dict

logger = logging.getLogger(__name__)

def fetch_discord_epub_metadata(channel_id: str, token: str, after_message_id: str = None) -> List[Dict]:
    """
    Fetches recent messages from a Discord channel using the REST API
    and looks for .epub attachments.
    Returns a list of dictionaries with 'url', 'filename', and 'message_id' (does not download).
    """
    headers = {"Authorization": f"Bot {token}"}
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    params = {"limit": 50}
    if after_message_id:
        params["after"] = after_message_id

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 401:
            logger.error("Discord API unauthorized. Check your bot token.")
            return []
        if response.status_code == 403:
            logger.error(f"Discord API forbidden. Ensure the bot is in the server and has read permissions for channel {channel_id}.")
            return []

        response.raise_for_status()
        messages = response.json()
    except Exception as e:
        logger.error(f"Error fetching Discord messages for channel {channel_id}: {e}")
        return []

    epubs_found = []

    # Process messages
    for message in messages:
        attachments = message.get("attachments", [])
        for attachment in attachments:
            filename = attachment.get("filename", "")
            if filename.lower().endswith(".epub"):
                file_url = attachment.get("url")
                if not file_url:
                    continue

                epubs_found.append({
                    "url": file_url,
                    "filename": filename,
                    "message_id": message.get("id"),
                    "timestamp": message.get("timestamp")
                })

    return epubs_found

def download_discord_epub(file_url: str, filename: str) -> str:
    """
    Downloads the EPUB at file_url to a temporary file.
    Returns the path to the downloaded file.
    """
    logger.info(f"Downloading Discord attachment: {filename}")
    file_resp = requests.get(file_url, timeout=30)
    file_resp.raise_for_status()

    temp_dir = tempfile.gettempdir()
    safe_name = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(temp_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_resp.content)

    return file_path
