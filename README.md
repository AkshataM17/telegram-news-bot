# CryptoPanic Telegram Bot

A Python bot that fetches cryptocurrency news sentiment from the CryptoPanic API, generates creative AI summaries using OpenAI, and sends regular updates to a Telegram channel.

## Features

- 📊 Fetches news sentiment data (bullish/bearish/neutral) from CryptoPanic API
- 🤖 Generates creative summaries using OpenAI with crypto slang and memes
- 📈 Categorizes and counts articles by sentiment
- 🔔 Sends regular updates to a Telegram channel
- 🎮 Includes manual command to trigger immediate updates
- 🔍 Filters news by cryptocurrency (BTC, ETH, etc.)

## Setup Instructions

### Prerequisites
- Python 3.8+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Telegram channel where your bot is an admin
- A CryptoPanic API key (from [CryptoPanic Developers](https://cryptopanic.com/developers/api/))
- An OpenAI API key (optional, for AI-generated summaries)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/cryptopanic-bot.git
   cd cryptopanic-bot
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the template:
   ```bash
   cp .env.template .env
   ```

4. Edit the `.env` file with your credentials:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token
   CHANNEL_ID=@your_channel_name_or_id
   CRYPTOPANIC_API_KEY=your_cryptopanic_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

### Getting a CryptoPanic API Key

1. Go to [https://cryptopanic.com/developers/api/](https://cryptopanic.com/developers/api/)
2. Sign up or log in
3. Generate an API key from your dashboard
4. Copy the key to your `.env` file

### Getting an OpenAI API Key (Optional)

1. Go to [https://platform.openai.com/](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to the API keys section
4. Create a new API key
5. Copy the key to your `.env` file

Note: The OpenAI API key is optional. If not provided, the bot will still work but won't include AI-generated summaries.

### Running the Bot

Run the bot with:

```bash
python cryptopanic_bot.py
```

For production use, consider running it with a process manager like `systemd`, `supervisor`, or in a Docker container.

## How It Works

1. The bot fetches news from the CryptoPanic API using your API key
2. It categorizes news as bullish, bearish, or neutral based on the sentiment
3. If OpenAI is configured, it generates a creative summary of the market sentiment
4. Every 30 minutes, it checks for new articles
5. When significant new content is found (at least 3 new articles), it sends an update to your Telegram channel
6. The message includes a count of articles by sentiment, an AI-generated summary, and links to the top stories

## Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/news` - Manually trigger a news update

## Customization

You can modify the following variables in the code:

- `CRYPTOCURRENCIES` - List of cryptocurrencies to monitor (default: ["BTC", "ETH", "SOL", "XRP", "DOGE"])
- `UPDATE_INTERVAL` - How often to check for updates (default: 30 minutes)

## API Usage Limits

- The free tier of the CryptoPanic API has a limit of 60 calls per hour. The bot makes 3 API calls per update cycle (one for each sentiment type), so the default 30-minute update interval will use 6 calls per hour, which is well within the limits.
- If using OpenAI, be aware that their API has pricing based on token usage. The bot uses a very minimal amount of tokens per update, so costs should be very low.

## Disclaimer

This bot provides cryptocurrency news analysis for informational purposes only. It is not financial advice. Always do your own research (DYOR) before making investment decisions.

## License

MIT