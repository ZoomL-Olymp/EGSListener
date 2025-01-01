import logging
import sys
import time
import os
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

import sqlite3
import asyncio
import aioschedule
import telegram
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, Application, JobQueue
from dateutil import parser
import pytz

# --- Logging ---
log_filename = f"epic_games_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.ERROR)
stderr_handler.setFormatter(formatter)

logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if BOT_TOKEN is None:
    logger.error("BOT_TOKEN wasn't found!")
    exit(1)
DATABASE_FILE = "free_games.db"

# --- Database Functions ---
async def create_database(application: Application):
    """
    Creates/connects to a SQLite database to store scraped data and subscribers.

    The database will be created if it doesn't exist, otherwise it will be connected to.

    Two tables are created: "free_games" and "subscribers".

    "free_games" table stores the scraped data with the following columns:

        id INTEGER PRIMARY KEY AUTOINCREMENT
        title TEXT
        free_until TEXT

    "subscribers" table stores the subscribers' chat IDs with the following columns:

        chat_id INTEGER PRIMARY KEY

    :param application: Telegram Application instance
    :type application: Application
    """
    logger.info("Creating/connecting to database...")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS free_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                free_until TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Subscribers table initialized successfully.")

    except Exception as e:
        logger.error(f"Error initializing subscribers table: {e}")


def save_game_info(title, free_until):
    """
    Saves game information into the database.

    This function inserts the title and free_until date of a game into
    the free_games table in the database. It logs the process and 
    handles exceptions if there are any errors during the database 
    operation.

    :param title: The title of the game.
    :type title: str
    :param free_until: The date until which the game is free.
    :type free_until: str
    """

    logger.info(f"Saving game info: {title} - {free_until}")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO free_games (title, free_until) VALUES (?, ?)", (title, free_until))
        conn.commit()
        conn.close()
        logger.info("Game info saved successfully.")
    except Exception as e:
        logger.error(f"Error saving game info: {e}")


def get_last_saved_game():
    """
    Retrieves the last saved game from the database.

    This function connects to the SQLite database and fetches the most
    recent entry from the "free_games" table, ordered by the primary key
    in descending order. It returns a tuple containing the title and
    free_until date of the last saved game. If an error occurs during
    the database operation, it logs the error and returns None.

    :return: Tuple containing the title and free_until date of the last 
             saved game, or None if an error occurs.
    :rtype: tuple or None
    """

    logger.info("Retrieving last saved game...")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT title, free_until FROM free_games ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        logger.info(f"Last saved game retrieved: {result}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving last saved game: {e}")
        return None
    
def add_subscriber(chat_id):
    """
    Adds a chat_id to the subscribers table in the database.

    This function takes a chat_id as an argument and adds it to the
    subscribers table in the database. If the chat_id is already in
    the table, it does nothing. If an error occurs during the database
    operation, it logs the error and returns False.

    :param chat_id: The chat_id to be added to the subscribers table.
    :type chat_id: int
    :return: True if the chat_id was successfully added, False if an
             error occurred.
    :rtype: bool
    """
    logger.info(f"Adding subscriber: {chat_id}")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        conn.close()
        logger.info("Subscriber added successfully.")
        return True
    except Exception as e:
        logger.error(f"Error adding subscriber: {e}")
        return False

def remove_subscriber(chat_id):
    """
    Removes a chat_id from the subscribers table in the database.

    This function takes a chat_id as an argument and removes it from
    the subscribers table in the database. If the chat_id is not found,
    it does nothing. If an error occurs during the database operation,
    it logs the error and returns False.

    :param chat_id: The chat_id to be removed from the subscribers table.
    :type chat_id: int
    :return: True if the chat_id was successfully removed, False if an
             error occurred.
    :rtype: bool
    """

    logger.info(f"Removing subscriber: {chat_id}")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        logger.info("Subscriber removed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error removing subscriber: {e}")
        return False

def get_subscribers():
    """
    Retrieves a list of chat_ids from the subscribers table in the database.

    This function connects to the SQLite database and fetches all the
    chat_ids from the "subscribers" table. It returns a list of integers
    representing the chat_ids of the subscribers. If an error occurs during
    the database operation, it logs the error and returns an empty list.

    :return: List of integers representing the chat_ids of the subscribers, or
             an empty list if an error occurs.
    :rtype: list
    """
    logger.info("Retrieving subscribers...")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM subscribers")
        subscribers = [row[0] for row in cursor.fetchall()]
        conn.close()
        logger.info(f"Subscribers retrieved: {subscribers}")
        return subscribers
    except Exception as e:
        logger.error(f"Error retrieving subscribers: {e}")
        return []

# --- Scraping Function ---
def scrape_epic_games():
    """
    Scrapes the Epic Games Store for the current free game details.

    This function initiates a headless Chrome browser session and navigates 
    to the Epic Games Store. It retrieves the title and the "free until" 
    date of the currently featured free game. The function uses a random 
    user agent to mimic a real browser session. Any exceptions during the 
    scraping process are logged, and the function returns None, None in 
    such cases.

    Returns:
        tuple: A tuple containing the free game's title and the "free until" 
               date as a datetime object. Returns (None, None) if an error 
               occurs.
    """

    start_time = time.time()
    logger.info("Starting scraping process...")

    try:
        options = Options()
        options.add_argument("--headless=new")
        ua = UserAgent()
        user_agent = ua.random
        options.add_argument(f'user-agent={user_agent}')
        logger.info(f"Using User-Agent: {user_agent}")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        with webdriver.Chrome(options=options) as driver:
            logger.info("Navigating to Epic Games Store...")
            driver.get("https://store.epicgames.com/en-US/")

            try:
                title_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h6.eds_1ypbntd0.eds_1ypbntd7.eds_1ypbntdq"))
                )
                title = title_element.text
                logger.info(f"Found game title: {title}")

                date_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time")) 
                )
                
                date_str = date_element.get_attribute("datetime")

                try:
                    free_until = datetime.fromisoformat(date_str.replace(" UTC", "+00:00").replace("Z", "+00:00"))
                    logger.info(f"Found free until date (UTC): {free_until}")

                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    logger.info(f"Scraping completed in {elapsed_time:.2f} seconds.")
                    return free_until, title

                except ValueError as e:
                     logger.error(f"Error parsing date: {e}. Date string: {date_str}")
                     return None, None
            except Exception as e:
                logger.error(f"Error finding elements: {e}")
                return None, None

    except Exception as e:
        logger.exception(f"An unexpected error occurred during scraping: {e}")
        return None, None



# --- Telegram Bot Functions ---
async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton(text="Free Game", callback_data="freegame"),
            InlineKeyboardButton(text="Subscribe", callback_data="subscribe"),
            InlineKeyboardButton(text="Unsubscribe", callback_data="unsubscribe"),
        ],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to the Epic Games Store Free Game Bot:", reply_markup=reply_markup)


async def freegame(update, context):
    game_info = get_last_saved_game()
    if game_info:
        title, free_until_str = game_info
        try:
            free_until = datetime.fromisoformat(free_until_str)
            free_until_formatted = free_until.strftime("%Y-%m-%d %H:%M %Z")
            await update.message.reply_text(f"Current free game:\n{title}\nFree until: {free_until_formatted}")

        except ValueError:
            await update.message.reply_text(f"Current free game:\n{title}\nFree until: {free_until_str} (Invalid date format)")

async def subscribe(update, context):
    chat_id = update.effective_chat.id
    if add_subscriber(chat_id):
        await update.message.reply_text("You have been subscribed to free game notifications!")
    else:
        await update.message.reply_text("Failed to subscribe. Please try again later.")

async def unsubscribe(update, context):
    chat_id = update.effective_chat.id
    if remove_subscriber(chat_id):
        await update.message.reply_text("You have been unsubscribed from free game notifications.")
    else:
        await update.message.reply_text("Failed to unsubscribe. Please try again later.")

async def send_notification(application: Application, title, free_until):
    subscribers = get_subscribers()
    if subscribers:
      free_until_formatted = free_until.strftime("%Y-%m-%d %H:%M %Z")
      for chat_id in subscribers:
          try:
              await application.bot.send_message(chat_id=chat_id, text=f"New free game available!\n{title}\nFree until: {free_until_formatted}")
              logger.info(f"Notification sent to {chat_id}")
          except Exception as e:
              logger.error(f"Failed to send message to {chat_id}: {e}")

async def scrape_and_update(application: Application):
    """
    Scrapes the Epic Games Store for the current free game details and updates the database,
    notifies subscribers if a new game is found, and schedules the next scrape based on the
    "free until" date of the game. If the "free until" date is in the past, it schedules the next
    scrape for 10:00 the next day.

    Args:
        application (Application): The Telegram Application instance.

    Returns:
        None
    """
    logger.info("Starting scheduled scrape and update...")
    try:
        now = datetime.now(timezone.utc)
        free_until, title = scrape_epic_games()
        if free_until and title:
            last_game = get_last_saved_game()
            if not last_game or last_game[0] != title:
              save_game_info(title, free_until.isoformat())
              logger.info(f"New free game found and saved: {title}")
              await send_notification(application, title, free_until)

              time_diff = free_until - now

              if time_diff > timedelta(0):
                  logger.info(f"Scheduling next scrape in {time_diff}")
                  aioschedule.clear()  # Clear any existing schedules
                  application.job_queue.run_once(lambda c: scrape_and_update(application), when=free_until)
              else: # free_until is in the past
                 tomorrow = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
                 logger.info(f"Scheduling for tomorrow at 10:00")
                 application.job_queue.run_once(lambda c: scrape_and_update(application), when=tomorrow)
                 aioschedule.every().day.at("10:00").do(lambda: scrape_and_update(application)) # Fallback to daily schedule
            else:
                logger.info(f"Game hasn't changed")
                time_diff = free_until - now
                if time_diff > timedelta(0):
                    logger.info(f"Scheduling next scrape in {time_diff}")
                    aioschedule.clear()  # Clear any existing schedules
                    application.job_queue.run_once(lambda c: scrape_and_update(application), when=free_until)
                else:
                    tomorrow = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
                    logger.info(f"Scheduling for tomorrow at 10:00")
                    application.job_queue.run_once(lambda c: scrape_and_update(application), when=tomorrow)
                    aioschedule.every().day.at("10:00").do(lambda: scrape_and_update(application)) # Fallback to daily schedule
        else:
            tomorrow = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
            logger.warning(f"Scraping failed, scheduling for tomorrow at 10:00")
            application.job_queue.run_once(lambda c: scrape_and_update(application), when=tomorrow)
            aioschedule.every().day.at("10:00").do(lambda: scrape_and_update(application)) # Fallback to daily schedule
    except Exception as e:
        logger.error(f"Error during scraping and update: {e}")


async def scheduler(application: Application):
    logger.info("Scheduler started.")
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def shutdown(application: Application):
    logger.info("Shutting down bot...")
    await application.bot.send_message(chat_id=CHAT_ID, text="Shutting down")
    await application.stop()
    await application.shutdown()


def run_bot(application: Application):
    application.add_handler(CommandHandler("stop", lambda u,c: asyncio.create_task(shutdown(application))))

    async def first_scrape_and_update(app): # Pass application to first_scrape_and_update
        await scrape_and_update(app)


    application.job_queue.run_once(lambda c: first_scrape_and_update(application), when=0)

    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    application = (ApplicationBuilder()
               .token(BOT_TOKEN)
               .post_init(create_database)
               .job_queue(JobQueue())
               .build())
    commands = [

    ]
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("freegame", freegame))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))

    run_bot(application)