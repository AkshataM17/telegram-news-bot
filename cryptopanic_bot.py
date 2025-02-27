import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

import httpx
import telegram
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Telegram bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure cryptocurrencies to monitor
CRYPTOCURRENCIES = ["BTC", "ETH", "SOL", "XRP", "DOGE"]  # Add or remove as needed
UPDATE_INTERVAL = 60 * 60 * 12  # Check every 12 hours (60 seconds * 60 minutes * 12 hours)

class CryptoPanicBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        self.last_sent_news = {}  # Keep track of what we've already sent
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
    def setup_handlers(self):
        """Set up command handlers for the bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("news", self.news_command))
        
    async def start_command(self, update, context):
        """Handle the /start command"""
        await update.message.reply_text(
            "🚀 CryptoPanic Bot is active! 🚀\n"
            "I'll send crypto news sentiment analysis to the configured channel.\n"
            "Use /help to see available commands."
        )
        
    async def help_command(self, update, context):
        """Handle the /help command"""
        await update.message.reply_text(
            "📊 CryptoPanic Bot Commands 📊\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/news - Get immediate news update\n\n"
            "The bot will automatically post news updates every 12 hours."
        )
    
    async def news_command(self, update, context):
        """Handle the /news command to manually trigger news update"""
        await update.message.reply_text("🔍 Fetching latest crypto news, please wait...")
        try:
            await self.send_news_update()
            await update.message.reply_text("✅ News update sent to the channel!")
        except Exception as e:
            logger.error(f"Error sending news update: {e}")
            await update.message.reply_text(f"❌ Error generating news update: {str(e)}")
    
    async def fetch_cryptopanic_api(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch the latest news from CryptoPanic API"""
        news_data = {
            "bullish": [],
            "bearish": [],
            "neutral": []
        }
        
        try:
            if not CRYPTOPANIC_API_KEY:
                logger.warning("No CryptoPanic API key provided. Set CRYPTOPANIC_API_KEY in your .env file.")
                return news_data
            
            # Build currency filter if CRYPTOCURRENCIES is set
            currency_filter = ""
            if CRYPTOCURRENCIES:
                currency_filter = f"&currencies={','.join(CRYPTOCURRENCIES)}"
            
            # Create httpx client with redirection following enabled
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Fetch bullish news
                bullish_response = await client.get(
                    f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&filter=bullish{currency_filter}",
                    timeout=10.0
                )
                
                # Fetch bearish news
                bearish_response = await client.get(
                    f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&filter=bearish{currency_filter}",
                    timeout=10.0
                )
                
                # Fetch important (neutral) news
                neutral_response = await client.get(
                    f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&filter=important{currency_filter}",
                    timeout=10.0
                )
                
                # Process bullish news
                if bullish_response.status_code == 200:
                    data = bullish_response.json()
                    for item in data.get("results", []):
                        news_data["bullish"].append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", {}).get("title", "Unknown"),
                            "published_at": item.get("published_at", ""),
                            "currencies": [c.get("code") for c in item.get("currencies", [])],
                            "sentiment": "bullish"
                        })
                else:
                    logger.error(f"Failed to fetch bullish news: {bullish_response.status_code} - {bullish_response.text}")
                
                # Process bearish news
                if bearish_response.status_code == 200:
                    data = bearish_response.json()
                    for item in data.get("results", []):
                        news_data["bearish"].append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", {}).get("title", "Unknown"),
                            "published_at": item.get("published_at", ""),
                            "currencies": [c.get("code") for c in item.get("currencies", [])],
                            "sentiment": "bearish"
                        })
                else:
                    logger.error(f"Failed to fetch bearish news: {bearish_response.status_code} - {bearish_response.text}")
                
                # Process neutral news
                if neutral_response.status_code == 200:
                    data = neutral_response.json()
                    for item in data.get("results", []):
                        news_data["neutral"].append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", {}).get("title", "Unknown"),
                            "published_at": item.get("published_at", ""),
                            "currencies": [c.get("code") for c in item.get("currencies", [])],
                            "sentiment": "neutral"
                        })
                else:
                    logger.error(f"Failed to fetch neutral news: {neutral_response.status_code} - {neutral_response.text}")
            
            return news_data
                
        except Exception as e:
            logger.error(f"Error fetching from CryptoPanic API: {e}")
            return news_data
    
    async def generate_fud_analysis(self, news_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate FUD analysis using OpenAI API based on news data"""
        if not self.openai_client:
            return ""
            
        try:
            # Count articles by sentiment
            bullish_count = len(news_data["bullish"])
            bearish_count = len(news_data["bearish"])
            neutral_count = len(news_data["neutral"])
            
            # Prepare news summary for OpenAI
            news_summary = ""
            
            # Add bullish news
            if news_data["bullish"]:
                news_summary += "\nBULLISH NEWS:\n"
                for i, item in enumerate(news_data["bullish"][:3], 1):
                    currencies = ", ".join(item["currencies"]) if item["currencies"] else "general market"
                    news_summary += f"{i}. {item['title']} ({currencies})\n"
            
            # Add bearish news
            if news_data["bearish"]:
                news_summary += "\nBEARISH NEWS:\n"
                for i, item in enumerate(news_data["bearish"][:3], 1):
                    currencies = ", ".join(item["currencies"]) if item["currencies"] else "general market"
                    news_summary += f"{i}. {item['title']} ({currencies})\n"
            
            # Add neutral news
            if news_data["neutral"]:
                news_summary += "\nNEUTRAL NEWS:\n"
                for i, item in enumerate(news_data["neutral"][:2], 1):
                    currencies = ", ".join(item["currencies"]) if item["currencies"] else "general market"
                    news_summary += f"{i}. {item['title']} ({currencies})\n"
            
            # Create prompt for OpenAI
            system_message = """
            You are a high-energy, meme-loving cryptocurrency analyst. Your mission is to analyze market news with a combination of technical knowledge and crypto-culture humor.
            
            Provide a brief, entertaining summary of the crypto market sentiment based on the news articles.
            Use crypto slang, emojis, and meme references in your analysis.
            Keep it concise (2-3 sentences max) but make it entertaining and informative.
            Focus on the overall sentiment and any standout news items.
            """
            
            user_message = f"""
            Based on the following crypto news, create a brief, entertaining crypto market sentiment summary:
            
            Bullish News Count: {bullish_count}
            Bearish News Count: {bearish_count}
            Neutral News Count: {neutral_count}
            
            {news_summary}
            
            The top cryptocurrencies mentioned in these news articles are: {', '.join(CRYPTOCURRENCIES)}
            
            Please provide a brief FUD (Fear, Uncertainty, Doubt) analysis with crypto humor and memes. Keep it to 2-3 sentences maximum.
            """
            
            # Call the OpenAI API
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # or gpt-3.5-turbo if preferred
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7  # Slightly higher for more creative responses
            )
            
            # Extract the response
            fud_analysis = response.choices[0].message.content.strip()
            
            return fud_analysis
            
        except Exception as e:
            logger.error(f"Error generating FUD analysis: {e}")
            return ""
    
    def format_telegram_message(self, news_data: Dict[str, List[Dict[str, Any]]], fud_analysis: str = "") -> str:
        """Format the news data into a nicely formatted Telegram message"""
        try:
            # Format the message with improved formatting
            message = f"🔔 *CRYPTO NEWS SENTIMENT UPDATE* 🔔\n\n"
            
            # Add AI-generated FUD analysis if available
            if fud_analysis:
                message += f"*AI SENTIMENT ANALYSIS*\n{fud_analysis}\n\n"
            
            # Add bullish news
            if news_data["bullish"]:
                message += "📈 *BULLISH NEWS*\n\n"
                for i, item in enumerate(news_data["bullish"][:5], 1):
                    # Format currencies
                    currencies = ""
                    if item["currencies"]:
                        currencies = f" [{', '.join(item['currencies'])}]"
                    
                    # Clean up title - truncate if too long
                    title = item["title"]
                    if len(title) > 100:
                        title = title[:97] + "..."
                        
                    message += f"{i}. [{title}]({item['url']}){currencies}\n"
                    message += f"   *Source:* {item['source']}\n\n"
            
            # Add bearish news
            if news_data["bearish"]:
                message += "📉 *BEARISH NEWS*\n\n"
                for i, item in enumerate(news_data["bearish"][:5], 1):
                    # Format currencies
                    currencies = ""
                    if item["currencies"]:
                        currencies = f" [{', '.join(item['currencies'])}]"
                    
                    # Clean up title - truncate if too long
                    title = item["title"]
                    if len(title) > 100:
                        title = title[:97] + "..."
                        
                    message += f"{i}. [{title}]({item['url']}){currencies}\n"
                    message += f"   *Source:* {item['source']}\n\n"
            
            # Add neutral news if we have any
            if news_data["neutral"]:
                message += "⚖️ *NEUTRAL NEWS*\n\n"
                for i, item in enumerate(news_data["neutral"][:5], 1):
                    # Format currencies
                    currencies = ""
                    if item["currencies"]:
                        currencies = f" [{', '.join(item['currencies'])}]"
                    
                    # Clean up title - truncate if too long
                    title = item["title"]
                    if len(title) > 100:
                        title = title[:97] + "..."
                        
                    message += f"{i}. [{title}]({item['url']}){currencies}\n"
                    message += f"   *Source:* {item['source']}\n\n"
            
            # Add timestamp and disclaimer
            message += f"_Updated on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC_\n"
            message += "_This is not financial advice. DYOR!_ 🧠"
            
            return message
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"Error formatting news: {str(e)}"
    
    def should_send_update(self, news_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Determine if we should send an update based on new content"""
        try:
            # If we haven't sent anything yet, definitely send
            if not self.last_sent_news:
                return True
            
            # Check if we have new items
            new_items = 0
            
            for sentiment in ["bullish", "bearish", "neutral"]:
                current_titles = {item["title"] for item in news_data[sentiment]}
                previous_titles = {item["title"] for item in self.last_sent_news.get(sentiment, [])}
                
                new_titles = current_titles - previous_titles
                new_items += len(new_titles)
            
            # If we have at least 3 new items, send an update
            return new_items >= 3
        
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return True  # When in doubt, send the update
    
    async def send_news_update(self):
        """Generate and send news update"""
        logger.info("Fetching news update")
        
        try:
            # Get the latest news
            news_data = await self.fetch_cryptopanic_api()
            
            # Check if we have any news
            total_news = sum(len(items) for items in news_data.values())
            if total_news == 0:
                logger.info("No news found from API")
                return
            
            # Check if we should send an update
            if not self.should_send_update(news_data):
                logger.info("No significant news updates to send")
                return
            
            # Generate FUD analysis if OpenAI is configured
            fud_analysis = ""
            if self.openai_client:
                fud_analysis = await self.generate_fud_analysis(news_data)
            
            # Format the message
            message = self.format_telegram_message(news_data, fud_analysis)
            
            # Send the message
            bot = telegram.Bot(TELEGRAM_TOKEN)
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True  # Disable previews to avoid showing website previews
            )
            
            # Update the last sent news
            self.last_sent_news = news_data
            
            logger.info("News update sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending news update: {e}")
    
    async def schedule_updates(self):
        """Run the scheduler in the background"""
        while True:
            try:
                await self.send_news_update()
            except Exception as e:
                logger.error(f"Error in scheduled update: {e}")
            
            # Wait for the next interval
            await asyncio.sleep(UPDATE_INTERVAL)
    
    def run(self):
        """Run the bot"""
        # Start the bot
        async def main():
            # Start the scheduler
            scheduler_task = asyncio.create_task(self.schedule_updates())
            
            # Start the bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Bot started!")
            
            # Keep the bot running until interrupted
            try:
                # This will keep the bot running until Ctrl+C is pressed
                await asyncio.Event().wait()  # Wait forever
            except asyncio.CancelledError:
                # Proper shutdown
                await self.app.stop()
                scheduler_task.cancel()
        
        # Run the bot
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("Bot stopped by user")


if __name__ == "__main__":
    # Create and run the bot
    bot = CryptoPanicBot()
    bot.run()
