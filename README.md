# Discord Brawl Stars Club Registration Bot

A Discord bot for verifying and managing Brawl Stars club members using the Supercell API. Supports slash commands, role assignment, and nickname updates based on club roles.

## Features
- Slash command `/setupregister` for registration panel
- Modal for Brawl Stars player tag input
- Verifies club membership using Supercell API
- Assigns Discord roles based on club role (President, Vice President, Senior, Member, Guest, Club Member, Unverified)
- Updates member nickname with Brawl Stars name and role emoji
- Removes old club roles before assigning new ones
- Works with dropdown UI for easy member status selection

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/BharathASL/discord-bot-for-bs-club.git
   cd discord-bot-for-bs-club
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   - Copy `.env.sample` to `.env` and fill in your credentials (see below).
4. **Set up Discord roles:**
   - Create roles in your server matching the names and emojis in `bot.py` (e.g., `👑 President`, `❓ Unverified`).
   - Ensure the bot's role is above these roles in the server role hierarchy and has permission to manage roles and nicknames.
5. **Run the bot:**
   ```sh
   python bot.py
   ```

## Environment Variables
Create a `.env` file in the project root with the following keys:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
SUPERCELL_API_TOKEN=your_supercell_api_token
GUILD_ID=your_discord_guild_id
CLUB_HASH_TAG=#YourClubTag
BS_ROOT_URL=api.brawlstars.com
```

See `.env.sample` for a template.

## Usage
- Use `/setupregister` to post the registration panel in your server. **You do not need to be an admin to use this command; it is for new members to register themselves.**
- Members select their status and enter their Brawl Stars tag to get verified and assigned the correct role.

## License
MIT License