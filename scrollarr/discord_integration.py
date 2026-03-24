import requests
import logging
import os
import tempfile
import uuid
from typing import List, Dict

logger = logging.getLogger(__name__)

def lookup_discord_channel_id(channel_name: str, token: str) -> str:
    """
    Looks up a Discord channel ID given its name by checking all guilds the bot is in.
    Returns the channel ID as a string, or None if not found.
    """
    headers = {"Authorization": f"Bot {token}"}

    # Clean up channel name (Discord channel names are lowercase, no spaces usually, but we'll just exact match or lower match)
    search_name = channel_name.strip().lower()
    if search_name.startswith('#'):
        search_name = search_name[1:]

    try:
        # 1. Get guilds the bot is in
        guilds_url = "https://discord.com/api/v10/users/@me/guilds"
        guilds_resp = requests.get(guilds_url, headers=headers, timeout=10)
        guilds_resp.raise_for_status()
        guilds = guilds_resp.json()

        # 2. Iterate through guilds and get channels
        for guild in guilds:
            guild_id = guild['id']
            channels_url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
            channels_resp = requests.get(channels_url, headers=headers, timeout=10)

            if channels_resp.status_code != 200:
                logger.warning(f"Failed to get channels for guild {guild_id}: {channels_resp.status_code}")
                continue

            channels = channels_resp.json()
            for channel in channels:
                # Check for text channels (type 0) or announcement channels (type 5)
                # and matching name
                if channel.get('type') in [0, 5] and channel.get('name', '').lower() == search_name:
                    logger.info(f"Found Discord channel ID {channel['id']} for name '{channel_name}'")
                    return str(channel['id'])

        logger.warning(f"Could not find a Discord channel named '{channel_name}'")
        return None

    except Exception as e:
        logger.error(f"Error looking up Discord channel ID for '{channel_name}': {e}")
        return None

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
