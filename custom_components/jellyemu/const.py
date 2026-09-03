"""Constants for the JellyEmu Home Assistant integration."""
from datetime import timedelta

DOMAIN = "jellyemu"
CONF_URL = "url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USER_ID = "user_id"

DEFAULT_SCAN_INTERVAL = 15  # seconds
SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

PLATFORMS = ["sensor", "media_player"]

# Sensor Types
SENSOR_ACTIVE_PLAYERS = "active_players"
SENSOR_TOTAL_GAMES = "total_games"
SENSOR_SYSTEMS = "systems"
SENSOR_TOTAL_PLAYTIME = "total_playtime"

# Services
SERVICE_LAUNCH_GAME = "launch_game"
ATTR_ITEM_ID = "item_id"
ATTR_USER_ID = "user_id"
ATTR_GAME_TITLE = "game_title"
ATTR_PLATFORM = "platform"

# Console theme colors for lovelace and automations
PLATFORM_COLORS = {
    "nes": "#E52521",
    "snes": "#7B52AB",
    "n64": "#009E49",
    "gb": "#8B956D",
    "gba": "#2E3192",
    "nds": "#333333",
    "segaMD": "#0055A5",
    "segaSaturn": "#222222",
    "psx": "#003791",
    "psp": "#1E2A38",
    "arcade": "#FFAA00",
}

SYSTEM_ALIASES = {
    # NES
    "nes": "NES", "famicom": "NES", "nintendo": "NES", "nintendo entertainment system": "NES",
    # SNES
    "snes": "SNES", "super nintendo": "SNES", "super famicom": "SNES", "super nintendo entertainment system": "SNES",
    # N64
    "n64": "Nintendo 64", "nintendo 64": "Nintendo 64", "nintendo64": "Nintendo 64",
    # Game Boy / GBC
    "gb": "Game Boy", "game boy": "Game Boy", "gameboy": "Game Boy",
    "gbc": "Game Boy Color", "game boy color": "Game Boy Color", "gameboy color": "Game Boy Color",
    # GBA
    "gba": "Game Boy Advance", "game boy advance": "Game Boy Advance", "gameboy advance": "Game Boy Advance",
    # NDS / 3DS
    "nds": "Nintendo DS", "nintendo ds": "Nintendo DS",
    "3ds": "Nintendo 3DS", "nintendo 3ds": "Nintendo 3DS",
    # Virtual Boy
    "vb": "Virtual Boy", "virtual boy": "Virtual Boy",
    # Sega
    "sms": "Master System", "master system": "Master System", "sega master system": "Master System",
    "gg": "Game Gear", "game gear": "Game Gear", "sega game gear": "Game Gear",
    "genesis": "Sega Genesis", "sega genesis": "Sega Genesis", "megadrive": "Sega Genesis", "mega drive": "Sega Genesis", "sega mega drive": "Sega Genesis", "md": "Sega Genesis",
    "sega cd": "Sega CD", "segacd": "Sega CD", "mega cd": "Sega CD",
    "32x": "Sega 32X", "sega 32x": "Sega 32X",
    "ss": "Sega Saturn", "saturn": "Sega Saturn", "sega saturn": "Sega Saturn",
    "dreamcast": "Dreamcast", "dc": "Dreamcast", "sega dreamcast": "Dreamcast",
    # PlayStation
    "psx": "PlayStation", "ps1": "PlayStation", "playstation": "PlayStation", "playstation 1": "PlayStation",
    "ps2": "PlayStation 2", "playstation 2": "PlayStation 2",
    "ps3": "PlayStation 3", "playstation 3": "PlayStation 3",
    "psp": "PSP", "playstation portable": "PSP",
    "psvita": "PlayStation Vita", "ps vita": "PlayStation Vita", "playstation vita": "PlayStation Vita",
    # Nintendo Consoles
    "gamecube": "GameCube", "nintendo gamecube": "GameCube", "gc": "GameCube",
    "wii": "Wii", "nintendo wii": "Wii",
    "wii u": "Wii U", "wiiu": "Wii U",
    "switch": "Nintendo Switch", "nintendo switch": "Nintendo Switch",
    # Atari
    "atari 2600": "Atari 2600", "2600": "Atari 2600", "atari 7800": "Atari 7800", "7800": "Atari 7800",
    "atari 5200": "Atari 5200", "5200": "Atari 5200",
    "lynx": "Atari Lynx", "atari lynx": "Atari Lynx", "jaguar": "Atari Jaguar", "atari jaguar": "Atari Jaguar",
    # Others
    "wonderswan": "WonderSwan", "ws": "WonderSwan",
    "pce": "TurboGrafx-16", "turbografx": "TurboGrafx-16", "turbografx-16": "TurboGrafx-16", "pc engine": "TurboGrafx-16",
    "colecovision": "ColecoVision", "coleco": "ColecoVision",
    "neogeo pocket": "NeoGeo Pocket", "ngp": "NeoGeo Pocket", "ngpc": "NeoGeo Pocket",
    "arcade": "Arcade", "fbneo": "Arcade", "mame": "Arcade", "neogeo": "Arcade",
    "dos": "DOS", "ms-dos": "DOS",
    "3do": "3DO",
    "amiga": "Commodore Amiga", "commodore amiga": "Commodore Amiga",
    "c64": "Commodore 64", "commodore 64": "Commodore 64",
    "pc-fx": "PC-FX", "pico-8": "PICO-8", "pico8": "PICO-8",
    "xbox": "Xbox", "xbox 360": "Xbox 360",
}

IGNORED_TAGS = {
    "jellyemu", "game", "games", "rom", "roms", "usa", "europe", "japan", "world",
    "australia", "brazil", "canada", "china", "france", "germany", "italy", "korea",
    "netherlands", "russia", "spain", "sweden", "asia", "scandinavia", "unlicensed",
    "prototype", "demo", "sample", "disc 1", "disc 2", "disc 3", "disc 4",
}


def resolve_system_platform(tags: list[str]) -> str:
    """Resolve the canonical retro system name from item tags, filtering out generic/region tags."""
    if not tags:
        return "Retro"

    # 1. Match against known system aliases first
    for t in tags:
        normalized = t.strip().lower()
        if normalized in SYSTEM_ALIASES:
            return SYSTEM_ALIASES[normalized]

    # 2. Filter out generic/region/metadata tags
    valid_tags = [t for t in tags if t.strip().lower() not in IGNORED_TAGS]
    if valid_tags:
        return valid_tags[0]

    return "Retro"

