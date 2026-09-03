/**
 * JellyEmu Home Assistant Custom Card
 */
const SYSTEM_ALIASES = {
    "nes": "NES", "famicom": "NES", "nintendo": "NES", "nintendo entertainment system": "NES",
    "snes": "SNES", "super nintendo": "SNES", "super famicom": "SNES", "super nintendo entertainment system": "SNES",
    "n64": "Nintendo 64", "nintendo 64": "Nintendo 64", "nintendo64": "Nintendo 64",
    "gb": "Game Boy", "game boy": "Game Boy", "gameboy": "Game Boy",
    "gbc": "Game Boy Color", "game boy color": "Game Boy Color", "gameboy color": "Game Boy Color",
    "gba": "Game Boy Advance", "game boy advance": "Game Boy Advance", "gameboy advance": "Game Boy Advance",
    "nds": "Nintendo DS", "nintendo ds": "Nintendo DS", "ds": "Nintendo DS",
    "3ds": "Nintendo 3DS", "nintendo 3ds": "Nintendo 3DS",
    "vb": "Virtual Boy", "virtual boy": "Virtual Boy",
    "sms": "Master System", "master system": "Master System", "sega master system": "Master System",
    "gg": "Game Gear", "game gear": "Game Gear", "sega game gear": "Game Gear",
    "genesis": "Sega Genesis", "sega genesis": "Sega Genesis", "megadrive": "Sega Genesis", "mega drive": "Sega Genesis", "md": "Sega Genesis",
    "sega cd": "Sega CD", "segacd": "Sega CD", "mega cd": "Sega CD",
    "32x": "Sega 32X", "sega 32x": "Sega 32X",
    "ss": "Sega Saturn", "saturn": "Sega Saturn", "sega saturn": "Sega Saturn",
    "dreamcast": "Dreamcast", "dc": "Dreamcast",
    "psx": "PlayStation", "ps1": "PlayStation", "playstation": "PlayStation", "playstation 1": "PlayStation",
    "ps2": "PlayStation 2", "playstation 2": "PlayStation 2",
    "ps3": "PlayStation 3", "playstation 3": "PlayStation 3",
    "psp": "PSP", "playstation portable": "PSP",
    "psvita": "PlayStation Vita", "ps vita": "PlayStation Vita",
    "gamecube": "GameCube", "nintendo gamecube": "GameCube", "gc": "GameCube",
    "wii": "Wii", "nintendo wii": "Wii",
    "wii u": "Wii U", "wiiu": "Wii U",
    "switch": "Nintendo Switch", "nintendo switch": "Nintendo Switch",
    "atari 2600": "Atari 2600", "2600": "Atari 2600", "atari 7800": "Atari 7800",
    "atari 5200": "Atari 5200", "lynx": "Atari Lynx", "jaguar": "Atari Jaguar",
    "wonderswan": "WonderSwan", "ws": "WonderSwan",
    "pce": "TurboGrafx-16", "turbografx": "TurboGrafx-16", "pc engine": "TurboGrafx-16",
    "colecovision": "ColecoVision", "coleco": "ColecoVision",
    "neogeo pocket": "NeoGeo Pocket", "ngp": "NeoGeo Pocket",
    "arcade": "Arcade", "mame": "Arcade", "neogeo": "Arcade",
    "dos": "DOS", "3do": "3DO", "amiga": "Commodore Amiga", "c64": "Commodore 64",
    "pc-fx": "PC-FX", "pico-8": "PICO-8", "xbox": "Xbox", "xbox 360": "Xbox 360"
};

const IGNORED_TAGS = new Set([
    "jellyemu", "game", "games", "rom", "roms", "usa", "europe", "japan", "world",
    "australia", "brazil", "canada", "china", "france", "germany", "italy", "korea",
    "netherlands", "russia", "spain", "sweden", "asia", "scandinavia", "unlicensed",
    "prototype", "demo", "sample", "disc 1", "disc 2", "disc 3", "disc 4"
]);

function resolvePlatform(tags) {
    if (!tags || !Array.isArray(tags)) return "Retro";
    for (const t of tags) {
        const norm = (t || '').trim().toLowerCase();
        if (SYSTEM_ALIASES[norm]) return SYSTEM_ALIASES[norm];
    }
    for (const t of tags) {
        const norm = (t || '').trim().toLowerCase();
        if (!IGNORED_TAGS.has(norm)) return t.trim();
    }
    return "Retro";
}

class JellyEmuCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._selectedPlatform = 'ALL';
        this._searchQuery = '';
        this._games = [];
        this._activeSessions = [];
        this._serverUrl = '';
    }

    static async getConfigElement() {
        return document.createElement('jellyemu-card-editor');
    }

    static getStubConfig() {
        return {
            title: 'JellyEmu',
            max_rows: 1,
            column_width: 132,
            show_search: true,
            show_filters: true,
            show_open_jellyfin: true,
        };
    }

    getLayoutOptions() {
        const maxRows = Math.max(1, parseInt(this._config?.max_rows) || 1);
        let contentHeight = (maxRows * 338) + 130;
        if (this._config?.show_search !== false) contentHeight += 52;
        if (this._config?.show_filters !== false) contentHeight += 44;
        const neededRows = Math.max(8, Math.ceil(contentHeight / 66));

        return {
            grid_columns: 4,
            grid_min_columns: 2,
            grid_rows: neededRows,
            grid_min_rows: neededRows,
        };
    }

    set hass(hass) {
        this._hass = hass;
        this._updateState();
    }

    setConfig(config) {
        this._config = Object.assign({
            title: 'JellyEmu',
            entity_games: 'sensor.jellyemu_total_games',
            entity_active_players: 'sensor.jellyemu_active_players',
            server_url: '',
            max_rows: 1,
            column_width: 132,
            show_search: true,
            show_filters: true,
            show_open_jellyfin: true,
        }, config);
        this._initialRender();
    }

    getCardSize() {
        const maxRows = Math.max(1, parseInt(this._config?.max_rows) || 1);
        let contentHeight = (maxRows * 338) + 130;
        if (this._config?.show_search !== false) contentHeight += 52;
        if (this._config?.show_filters !== false) contentHeight += 44;
        return Math.max(11, Math.ceil(contentHeight / 50));
    }

    _updateState() {
        if (!this._hass || !this._config) return;

        // Resolve Games Sensor (with auto-discovery if configured key isn't found)
        let gamesSensor = this._hass.states[this._config.entity_games];
        if (!gamesSensor) {
            const foundKey = Object.keys(this._hass.states).find(k =>
                k.startsWith('sensor.') && (
                    (k.includes('jellyemu') && (k.includes('game') || k.includes('total'))) ||
                    (this._hass.states[k].attributes && this._hass.states[k].attributes.games)
                )
            );
            if (foundKey) gamesSensor = this._hass.states[foundKey];
        }

        // Resolve Active Players Sensor
        let activeSensor = this._hass.states[this._config.entity_active_players];
        if (!activeSensor) {
            const foundActive = Object.keys(this._hass.states).find(k =>
                k.startsWith('sensor.') && k.includes('jellyemu') && k.includes('active')
            );
            if (foundActive) activeSensor = this._hass.states[foundActive];
        }

        // Retrieve server URL from config entry attributes or user config
        const serverUrl = this._config.server_url ||
            (gamesSensor && gamesSensor.attributes && gamesSensor.attributes.server_url) ||
            (activeSensor && activeSensor.attributes && activeSensor.attributes.server_url) ||
            '';
        this._serverUrl = serverUrl.replace(/\/+$/, '');

        // Retrieve games list from sensor attributes
        if (gamesSensor && gamesSensor.attributes && gamesSensor.attributes.games && gamesSensor.attributes.games.length > 0) {
            this._games = gamesSensor.attributes.games;
        }

        // If card has serverUrl but games list is still empty, fetch directly via standard Jellyfin API
        if ((!this._games || this._games.length === 0) && this._serverUrl && !this._fetchingGames) {
            this._fetchingGames = true;
            fetch(`${this._serverUrl}/Items?IncludeItemTypes=Book&Tags=JellyEmu&Recursive=true&Fields=Tags,PremiereDate&SortBy=SortName`)
                .then(r => r.ok ? r.json() : null)
                .then(data => {
                    if (data && data.Items && data.Items.length > 0) {
                        this._games = data.Items.map(item => {
                            const rawTags = item.Tags || [];
                            const platform = resolvePlatform(rawTags);
                            return {
                                id: item.Id,
                                name: item.Name,
                                platform: platform,
                                year: item.PremiereDate ? item.PremiereDate.substring(0, 4) : '',
                                image: `${this._serverUrl}/Items/${item.Id}/Images/Primary?fillWidth=300&quality=85`,
                                play_url: `${this._serverUrl}/jellyemu/play/${item.Id}`,
                                details_url: `${this._serverUrl}/web/index.html#!/details?id=${item.Id}`,
                            };
                        });
                        this._updateDynamicParts();
                    }
                })
                .catch(() => {})
                .finally(() => { this._fetchingGames = false; });
        }

        this._activeSessions = (activeSensor && activeSensor.attributes && activeSensor.attributes.active_sessions) || [];
        this._updateDynamicParts();
    }

    _initialRender() {
        const maxRows = Math.max(1, parseInt(this._config.max_rows) || 1);
        const colWidth = Math.max(100, parseInt(this._config.column_width) || 132);
        const gridMaxHeight = (325 * maxRows) + (12 * (maxRows - 1)) + 14;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    position: relative;
                    box-sizing: border-box;
                    --mui-primary: var(--primary-color, #1976d2);
                    --mui-primary-dark: #1565c0;
                    --mui-primary-light: #42a5f5;
                    --mui-bg: var(--ha-card-background, var(--card-background-color, #121212));
                    --mui-paper: rgba(255, 255, 255, 0.05);
                    --mui-card-bg: rgba(255, 255, 255, 0.03);
                    --mui-text-primary: var(--primary-text-color, #ffffff);
                    --mui-text-secondary: var(--secondary-text-color, rgba(255, 255, 255, 0.7));
                    --mui-divider: var(--divider-color, rgba(255, 255, 255, 0.12));
                    font-family: Roboto, Helvetica, Arial, sans-serif;
                }

                ha-card {
                    background: var(--mui-bg);
                    border-radius: 8px;
                    border: 1px solid var(--mui-divider);
                    box-shadow: 0px 2px 1px -1px rgba(0,0,0,0.2), 0px 1px 1px 0px rgba(0,0,0,0.14), 0px 1px 3px 0px rgba(0,0,0,0.12);
                    padding: 16px;
                    color: var(--mui-text-primary);
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                }

                /* MUI CardHeader */
                .MuiCardHeader-root {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding-bottom: 14px;
                    border-bottom: 1px solid var(--mui-divider);
                    margin-bottom: 14px;
                }
                .MuiCardHeader-avatarGroup {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                .MuiAvatar-root {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1976d2, #0d47a1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #ffffff;
                    flex-shrink: 0;
                    box-shadow: 0px 3px 5px -1px rgba(0,0,0,0.3);
                }
                .MuiAvatar-root svg {
                    width: 24px;
                    height: 24px;
                }
                .MuiTypography-h6 {
                    font-size: 1.125rem;
                    font-weight: 500;
                    line-height: 1.4;
                    letter-spacing: 0.0075em;
                    color: var(--mui-text-primary);
                    margin: 0;
                }
                .MuiTypography-body2 {
                    font-size: 0.8125rem;
                    font-weight: 400;
                    line-height: 1.43;
                    letter-spacing: 0.01071em;
                    color: var(--mui-text-secondary);
                    margin: 0;
                }

                /* MUI Open Jellyfin Button in Header */
                .MuiButton-root {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    box-sizing: border-box;
                    background-color: transparent;
                    outline: 0;
                    border: 0;
                    margin: 0;
                    cursor: pointer;
                    user-select: none;
                    vertical-align: middle;
                    text-decoration: none;
                    font-family: inherit;
                    font-weight: 500;
                    font-size: 0.8125rem;
                    line-height: 1.75;
                    letter-spacing: 0.02857em;
                    text-transform: uppercase;
                    padding: 5px 14px;
                    border-radius: 4px;
                    transition: background-color 250ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 250ms cubic-bezier(0.4, 0, 0.2, 1), border-color 250ms cubic-bezier(0.4, 0, 0.2, 1);
                    gap: 6px;
                }
                .MuiButton-outlinedPrimary {
                    color: var(--mui-primary);
                    border: 1px solid rgba(25, 118, 210, 0.5);
                }
                .MuiButton-outlinedPrimary:hover {
                    border-color: var(--mui-primary);
                    background-color: rgba(25, 118, 210, 0.08);
                }
                .MuiButton-containedPrimary {
                    color: #ffffff;
                    background-color: var(--mui-primary);
                    box-shadow: 0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12);
                }
                .MuiButton-containedPrimary:hover {
                    background-color: var(--mui-primary-dark);
                    box-shadow: 0px 2px 4px -1px rgba(0,0,0,0.2), 0px 4px 5px 0px rgba(0,0,0,0.14), 0px 1px 10px 0px rgba(0,0,0,0.12);
                }
                .MuiSvgIcon-root {
                    user-select: none;
                    width: 1em;
                    height: 1em;
                    display: inline-block;
                    fill: currentColor;
                    flex-shrink: 0;
                    font-size: 1.125rem;
                }

                /* MUI Alert (Now Playing Active Banner) */
                .MuiAlert-root {
                    display: none;
                    align-items: center;
                    justify-content: space-between;
                    padding: 8px 14px;
                    border-radius: 4px;
                    background-color: rgba(46, 125, 50, 0.12);
                    border: 1px solid rgba(76, 175, 80, 0.4);
                    color: #81c784;
                    margin-bottom: 14px;
                    gap: 12px;
                }
                .MuiAlert-message {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    min-width: 0;
                }
                .MuiAlert-title {
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: var(--mui-text-primary);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .MuiAlert-sub {
                    font-size: 0.75rem;
                    color: var(--mui-text-secondary);
                }

                /* MUI Outlined TextField */
                .MuiFormControl-root {
                    display: ${this._config.show_search !== false ? 'flex' : 'none'};
                    flex-direction: column;
                    margin-bottom: 12px;
                }
                .MuiOutlinedInput-root {
                    display: flex;
                    align-items: center;
                    position: relative;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.23);
                    padding: 0 12px;
                    background: rgba(0, 0, 0, 0.15);
                    transition: border-color 200ms cubic-bezier(0.4, 0, 0.2, 1);
                }
                .MuiOutlinedInput-root:focus-within {
                    border-color: var(--mui-primary);
                    box-shadow: 0 0 0 1px var(--mui-primary);
                }
                .MuiOutlinedInput-input {
                    font: inherit;
                    letter-spacing: inherit;
                    color: var(--mui-text-primary);
                    border: 0;
                    box-sizing: content-box;
                    background: none;
                    margin: 0;
                    display: block;
                    min-width: 0;
                    width: 100%;
                    padding: 9px 0 9px 8px;
                    outline: 0;
                    font-size: 0.875rem;
                }
                .MuiOutlinedInput-input::placeholder {
                    color: var(--mui-text-secondary);
                    opacity: 0.7;
                }

                /* MUI Chips (Filter Row) */
                .MuiChips-container {
                    display: ${this._config.show_filters !== false ? 'flex' : 'none'};
                    gap: 6px;
                    overflow-x: auto;
                    padding-bottom: 6px;
                    margin-bottom: 14px;
                    scrollbar-width: none;
                }
                .MuiChips-container::-webkit-scrollbar {
                    display: none;
                }
                .MuiChip-root {
                    font-family: inherit;
                    font-size: 0.75rem;
                    font-weight: 500;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    height: 28px;
                    color: var(--mui-text-primary);
                    border-radius: 14px;
                    white-space: nowrap;
                    transition: background-color 300ms cubic-bezier(0.4, 0, 0.2, 1), color 300ms cubic-bezier(0.4, 0, 0.2, 1);
                    cursor: pointer;
                    outline: 0;
                    text-decoration: none;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    background-color: transparent;
                    padding: 0 10px;
                }
                .MuiChip-root:hover {
                    background-color: rgba(255, 255, 255, 0.08);
                }
                .MuiChip-root.MuiChip-filledPrimary {
                    color: #ffffff;
                    background-color: var(--mui-primary);
                    border-color: var(--mui-primary);
                    box-shadow: 0px 2px 4px -1px rgba(0,0,0,0.2);
                }

                /* MUI Card Grid: Configurable rows & column widths */
                .MuiGrid-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(${colWidth}px, 1fr));
                    grid-auto-rows: 325px;
                    gap: 12px;
                    max-height: ${gridMaxHeight}px;
                    overflow-y: auto;
                    overflow-x: hidden;
                    padding: 4px 6px 12px 4px;
                    scrollbar-width: thin;
                    box-sizing: border-box;
                }
                .MuiGrid-container::-webkit-scrollbar {
                    width: 6px;
                }
                .MuiGrid-container::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 3px;
                }

                /* MUI Card (Game Tile) */
                .MuiCard-root {
                    background-color: var(--mui-card-bg);
                    border-radius: 6px;
                    border: 1px solid var(--mui-divider);
                    box-shadow: 0px 1px 3px 0px rgba(0,0,0,0.2);
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    height: 325px;
                    box-sizing: border-box;
                    transition: box-shadow 300ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms ease;
                }
                .MuiCard-root:hover {
                    transform: translateY(-2px);
                    box-shadow: 0px 4px 10px 0px rgba(0,0,0,0.35);
                    border-color: rgba(25, 118, 210, 0.4);
                }
                .MuiCardMedia-media {
                    width: 100%;
                    aspect-ratio: 3 / 4;
                    object-fit: cover;
                    background: rgba(0,0,0,0.4);
                    display: block;
                }
                .MuiCardContent-root {
                    padding: 8px 10px;
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
                .MuiCardContent-title {
                    font-size: 0.8125rem;
                    font-weight: 500;
                    line-height: 1.35;
                    margin: 0 0 4px 0;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                    min-height: 2.2em;
                    color: var(--mui-text-primary);
                    text-decoration: none;
                }
                .MuiCardContent-title:hover {
                    color: var(--mui-primary);
                }
                .MuiCardContent-meta {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-top: auto;
                    min-height: 18px;
                    font-size: 0.6875rem;
                    color: var(--mui-text-secondary);
                }
                .MuiCardContent-badge {
                    text-transform: uppercase;
                    font-size: 0.625rem;
                    font-weight: 700;
                    letter-spacing: 0.05em;
                    color: var(--mui-primary-light);
                }
                .MuiCardActions-root {
                    display: flex;
                    align-items: center;
                    padding: 6px 8px 8px 8px;
                    border-top: 1px solid var(--mui-divider);
                }
                .MuiCardActions-root .MuiButton-root {
                    width: 100%;
                    font-size: 0.75rem;
                    padding: 4px 8px;
                }

                .MuiEmpty-root {
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 36px 16px;
                    color: var(--mui-text-secondary);
                    font-size: 0.875rem;
                }
            </style>

            <ha-card>
                <!-- MUI CardHeader -->
                <div class="MuiCardHeader-root">
                    <div class="MuiCardHeader-avatarGroup">
                        <div class="MuiAvatar-root">
                            <!-- Official JellyEmu Icon from assets/jellyemu.svg -->
                            <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M12 2L3 18a2 2 0 0 0 1.7 3h14.6a2 2 0 0 0 1.7-3L12 2z" />
                                <path d="M7.5 15.5h3M9 14v3" stroke-width="1.2" />
                                <circle cx="15.5" cy="14.5" r="0.8" fill="white" stroke="none" />
                                <circle cx="17" cy="16.5" r="0.8" fill="white" stroke="none" />
                            </svg>
                        </div>
                        <div>
                            <h2 class="MuiTypography-h6">${this._config.title || 'JellyEmu'}</h2>
                            <p class="MuiTypography-body2" id="je-game-count">-- Games</p>
                        </div>
                    </div>

                    <!-- Direct Open Jellyfin Button -->
                    <a class="MuiButton-root MuiButton-outlinedPrimary" id="je-btn-open-jellyfin" style="${this._config.show_open_jellyfin !== false ? '' : 'display:none;'}" href="#" target="_blank" title="Open Jellyfin Web">
                        <svg class="MuiSvgIcon-root" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
                        Open Jellyfin
                    </a>
                </div>

                <!-- MUI Alert: Active Emulation Session (No green dot) -->
                <div class="MuiAlert-root" id="je-active-alert">
                    <div class="MuiAlert-message">
                        <div>
                            <div class="MuiAlert-title" id="je-active-title">Playing Retro Game</div>
                            <div class="MuiAlert-sub" id="je-active-sub">by User • Console</div>
                        </div>
                    </div>
                    <a class="MuiButton-root MuiButton-containedPrimary" id="je-active-btn" href="#" target="_blank">
                        ▶ Resume
                    </a>
                </div>

                <!-- MUI Outlined TextField: Search Jellyfin Library -->
                <div class="MuiFormControl-root">
                    <div class="MuiOutlinedInput-root">
                        <svg class="MuiSvgIcon-root" style="color: var(--mui-text-secondary); margin-right: 6px;" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                        <input class="MuiOutlinedInput-input" id="je-search" type="text" placeholder="Search Jellyfin retro games..." />
                    </div>
                </div>

                <!-- MUI Chips: Console Filters -->
                <div class="MuiChips-container" id="je-chips"></div>

                <!-- MUI Card Grid: Owned Games -->
                <div class="MuiGrid-container" id="je-grid"></div>
            </ha-card>
        `;

        // Search Input Listener
        const searchInput = this.shadowRoot.getElementById('je-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this._searchQuery = (e.target.value || '').toLowerCase().trim();
                this._renderGrid();
            });
        }

        this._updateDynamicParts();
    }

    _updateDynamicParts() {
        if (!this.shadowRoot) return;

        // 1. Update Subheader Game Count
        const countEl = this.shadowRoot.getElementById('je-game-count');
        if (countEl) {
            let gamesSensor = this._hass && this._hass.states[this._config.entity_games];
            if (!gamesSensor && this._hass) {
                const foundKey = Object.keys(this._hass.states).find(k =>
                    k.startsWith('sensor.') && k.includes('jellyemu') && (k.includes('game') || k.includes('total'))
                );
                if (foundKey) gamesSensor = this._hass.states[foundKey];
            }
            const sensorCount = gamesSensor ? parseInt(gamesSensor.state) : NaN;
            const count = (!isNaN(sensorCount) && sensorCount > 0) ? sensorCount : this._games.length;
            countEl.textContent = `${count} ${count === 1 ? 'game' : 'games'} in library`;
        }

        // 2. Update Open Jellyfin Button URL
        const openJfBtn = this.shadowRoot.getElementById('je-btn-open-jellyfin');
        if (openJfBtn) {
            openJfBtn.href = this._serverUrl ? `${this._serverUrl}/web/index.html` : '#';
        }

        // 3. Update Now Playing Active Alert
        const alertBox = this.shadowRoot.getElementById('je-active-alert');
        const activeTitle = this.shadowRoot.getElementById('je-active-title');
        const activeSub = this.shadowRoot.getElementById('je-active-sub');
        const activeBtn = this.shadowRoot.getElementById('je-active-btn');

        if (alertBox && activeTitle && activeSub && activeBtn) {
            if (this._activeSessions && this._activeSessions.length > 0) {
                const s = this._activeSessions[0];
                alertBox.style.display = 'flex';
                activeTitle.textContent = s.game_title || 'Playing Retro Game';
                activeSub.textContent = `Played by ${s.user_name || 'User'} • ${s.platform || 'Retro'}`;

                const playUrl = this._serverUrl ? `${this._serverUrl}/jellyemu/play/${s.item_id}` : (s.play_url || '#');
                activeBtn.href = playUrl;
            } else {
                alertBox.style.display = 'none';
            }
        }

        // 4. Render Platform Filter Chips
        this._renderChips();

        // 5. Render Game Grid
        this._renderGrid();
    }

    _renderChips() {
        const chipsContainer = this.shadowRoot.getElementById('je-chips');
        if (!chipsContainer) return;

        const sysSet = new Set();
        this._games.forEach(g => {
            const p = (g.platform || '').trim();
            if (p && !IGNORED_TAGS.has(p.toLowerCase()) && p.toLowerCase() !== 'retro') {
                sysSet.add(p);
            }
        });
        const systems = ['ALL', ...Array.from(sysSet).sort()];

        chipsContainer.innerHTML = '';
        systems.forEach(sys => {
            const chip = document.createElement('button');
            const isActive = this._selectedPlatform.toLowerCase() === sys.toLowerCase();
            chip.className = `MuiChip-root ${isActive ? 'MuiChip-filledPrimary' : ''}`;
            chip.textContent = sys;
            chip.addEventListener('click', () => {
                this._selectedPlatform = sys;
                this._renderChips();
                this._renderGrid();
            });
            chipsContainer.appendChild(chip);
        });
    }

    _renderGrid() {
        const grid = this.shadowRoot.getElementById('je-grid');
        if (!grid) return;

        let filtered = this._games;

        // Filter by platform
        if (this._selectedPlatform && this._selectedPlatform !== 'ALL') {
            filtered = filtered.filter(g => (g.platform || '').toLowerCase() === this._selectedPlatform.toLowerCase());
        }

        // Filter by search query
        if (this._searchQuery) {
            filtered = filtered.filter(g =>
                (g.name || '').toLowerCase().includes(this._searchQuery) ||
                (g.platform || '').toLowerCase().includes(this._searchQuery)
            );
        }

        if (filtered.length === 0) {
            grid.innerHTML = `
                <div class="MuiEmpty-root">
                    ${this._games.length === 0 ? 'No games found in your Jellyfin library.' : 'No games match your search query.'}
                </div>
            `;
            return;
        }

        grid.innerHTML = filtered.map(game => {
            const playUrl = this._serverUrl ? `${this._serverUrl}/jellyemu/play/${game.id}` : (game.play_url || '#');
            const detailsUrl = this._serverUrl ? `${this._serverUrl}/web/index.html#!/details?id=${game.id}` : (game.details_url || '#');

            return `
                <div class="MuiCard-root">
                    <a href="${detailsUrl}" target="_blank" style="text-decoration: none;">
                        <img class="MuiCardMedia-media" src="${game.image}" alt="${game.name}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 100 133\\' fill=\\'%231a1a1a\\'><text x=\\'50%\\' y=\\'50%\\' fill=\\'%23666\\' font-size=\\'11\\' text-anchor=\\'middle\\' dy=\\'.3em\\'>No Art</text></svg>'" />
                    </a>
                    <div class="MuiCardContent-root">
                        <a class="MuiCardContent-title" href="${detailsUrl}" target="_blank" title="View in Jellyfin">${game.name}</a>
                        <div class="MuiCardContent-meta">
                            <span class="MuiCardContent-badge">${game.platform}</span>
                            <span>${game.year || ''}</span>
                        </div>
                    </div>
                    <div class="MuiCardActions-root">
                        <a class="MuiButton-root MuiButton-containedPrimary" href="${playUrl}" target="_blank" title="Play ${game.name}">
                            <svg class="MuiSvgIcon-root" viewBox="0 0 24 24"><path d="M8,5.14V19.14L19,12.14L8,5.14Z"/></svg>
                            Play
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    }
}

/**
 * Visual Card Configuration Editor for Home Assistant UI
 */
class JellyEmuCardEditor extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    setConfig(config) {
        this._config = Object.assign({
            title: 'JellyEmu',
            max_rows: 1,
            column_width: 132,
            show_search: true,
            show_filters: true,
            show_open_jellyfin: true,
        }, config);
        this._render();
    }

    set hass(hass) {
        this._hass = hass;
    }

    _valueChanged(field, value) {
        if (!this._config) return;
        this._config = {
            ...this._config,
            [field]: value
        };

        const event = new CustomEvent('config-changed', {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
        });
        this.dispatchEvent(event);
    }

    _render() {
        if (!this.shadowRoot) return;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: Roboto, sans-serif;
                    color: var(--primary-text-color, #ffffff);
                }
                .je-editor {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    padding: 8px 0;
                }
                .je-field {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .je-label {
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--primary-text-color, #ffffff);
                }
                .je-sublabel {
                    font-size: 11px;
                    color: var(--secondary-text-color, #9e9e9e);
                }
                .je-input {
                    padding: 8px 12px;
                    background: rgba(0, 0, 0, 0.2);
                    border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
                    border-radius: 4px;
                    color: var(--primary-text-color, #ffffff);
                    font-size: 13px;
                    outline: none;
                }
                .je-input:focus {
                    border-color: var(--primary-color, #1976d2);
                }
                .je-row {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 4px 0;
                }
                .je-toggle {
                    position: relative;
                    display: inline-block;
                    width: 44px;
                    height: 24px;
                }
                .je-toggle input {
                    opacity: 0;
                    width: 0;
                    height: 0;
                }
                .je-slider {
                    position: absolute;
                    cursor: pointer;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: rgba(255, 255, 255, 0.2);
                    transition: .3s;
                    border-radius: 24px;
                }
                .je-slider:before {
                    position: absolute;
                    content: "";
                    height: 18px;
                    width: 18px;
                    left: 3px;
                    bottom: 3px;
                    background-color: white;
                    transition: .3s;
                    border-radius: 50%;
                }
                input:checked + .je-slider {
                    background-color: var(--primary-color, #1976d2);
                }
                input:checked + .je-slider:before {
                    transform: translateX(20px);
                }
                .je-grid-2 {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                }
            </style>

            <div class="je-editor">
                <!-- Card Title -->
                <div class="je-field">
                    <label class="je-label">Card Title</label>
                    <input class="je-input" id="cfg-title" type="text" value="${this._config.title || 'JellyEmu'}" />
                </div>

                <!-- Layout & Sizing Settings -->
                <div class="je-grid-2">
                    <div class="je-field">
                        <label class="je-label">Visible Rows</label>
                        <span class="je-sublabel">Rows shown before vertical scroll</span>
                        <input class="je-input" id="cfg-rows" type="number" min="1" max="10" value="${this._config.max_rows || 1}" />
                    </div>
                    <div class="je-field">
                        <label class="je-label">Card Min-Width (px)</label>
                        <span class="je-sublabel">Columns fill width automatically</span>
                        <input class="je-input" id="cfg-colwidth" type="number" min="100" max="300" step="10" value="${this._config.column_width || 132}" />
                    </div>
                </div>

                <!-- UI Element Toggles -->
                <div class="je-row">
                    <div>
                        <div class="je-label">Show Search Bar</div>
                        <div class="je-sublabel">Filter owned games by title or system</div>
                    </div>
                    <label class="je-toggle">
                        <input type="checkbox" id="cfg-search" ${this._config.show_search !== false ? 'checked' : ''}>
                        <span class="je-slider"></span>
                    </label>
                </div>

                <div class="je-row">
                    <div>
                        <div class="je-label">Show Platform Filter Chips</div>
                        <div class="je-sublabel">Chips for consoles (NES, SNES, GBA, etc.)</div>
                    </div>
                    <label class="je-toggle">
                        <input type="checkbox" id="cfg-filters" ${this._config.show_filters !== false ? 'checked' : ''}>
                        <span class="je-slider"></span>
                    </label>
                </div>

                <div class="je-row">
                    <div>
                        <div class="je-label">Show "Open Jellyfin" Button</div>
                        <div class="je-sublabel">Shortcut to open Jellyfin web client</div>
                    </div>
                    <label class="je-toggle">
                        <input type="checkbox" id="cfg-openjf" ${this._config.show_open_jellyfin !== false ? 'checked' : ''}>
                        <span class="je-slider"></span>
                    </label>
                </div>
            </div>
        `;

        // Attach Event Listeners
        const titleInput = this.shadowRoot.getElementById('cfg-title');
        if (titleInput) {
            titleInput.addEventListener('change', (e) => this._valueChanged('title', e.target.value));
        }

        const rowsInput = this.shadowRoot.getElementById('cfg-rows');
        if (rowsInput) {
            rowsInput.addEventListener('change', (e) => this._valueChanged('max_rows', parseInt(e.target.value) || 1));
        }

        const colWidthInput = this.shadowRoot.getElementById('cfg-colwidth');
        if (colWidthInput) {
            colWidthInput.addEventListener('change', (e) => this._valueChanged('column_width', parseInt(e.target.value) || 132));
        }

        const searchToggle = this.shadowRoot.getElementById('cfg-search');
        if (searchToggle) {
            searchToggle.addEventListener('change', (e) => this._valueChanged('show_search', e.target.checked));
        }

        const filtersToggle = this.shadowRoot.getElementById('cfg-filters');
        if (filtersToggle) {
            filtersToggle.addEventListener('change', (e) => this._valueChanged('show_filters', e.target.checked));
        }

        const openJfToggle = this.shadowRoot.getElementById('cfg-openjf');
        if (openJfToggle) {
            openJfToggle.addEventListener('change', (e) => this._valueChanged('show_open_jellyfin', e.target.checked));
        }
    }
}

// Register custom elements
if (!customElements.get('jellyemu-card')) {
    customElements.define('jellyemu-card', JellyEmuCard);
    window.customCards = window.customCards || [];
    window.customCards.push({
        type: 'jellyemu-card',
        name: 'JellyEmu Card',
        description: 'MUI-designed retro game library manager and player for Jellyfin',
        preview: true
    });
    console.info('%c JELLYEMU-CARD %c v2.0.7 Loaded ', 'color: white; background: #1976d2; font-weight: 700;', 'color: #1976d2; background: #121212; font-weight: 700;');
}

if (!customElements.get('jellyemu-card-editor')) {
    customElements.define('jellyemu-card-editor', JellyEmuCardEditor);
}
