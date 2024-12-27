import logging
import sys
import time
import os
from datetime import datetime, timedelta

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
from telegram.ext import ApplicationBuilder, CommandHandler, Application, JobQueue
from dateutil import parser

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
    exit(1) # Прекращаем выполнение программы, если токен не найден
DATABASE_FILE = "free_games.db"
SCRAPE_TIME = "19:00"  # Time to scrape every day (24-hour format)

# --- Database Functions ---
async def create_database(application: Application):
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


def save_game_info(title, free_until):
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


# --- Scraping Function ---
def scrape_epic_games():
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

                date_elements = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "time"))
                )
                date1 = date_elements[0].text
                date2 = date_elements[1].text
                date_str = f"{date1} {date2}" # Combine date and time string

                try:
                    free_until = parser.parse(date_str) # Parse the date string
                    logger.info(f"Found free until date: {free_until}")

                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    logger.info(f"Scraping completed in {elapsed_time:.2f} seconds.")
                    return free_until, title # Return datetime object

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
    await update.message.reply_text("Welcome! Use /freegame to get the current free game.")

async def freegame(update, context):
    game_info = get_last_saved_game()
    if game_info:
        title, free_until = game_info
        await update.message.reply_text(f"Current free game:\n{title}\nFree until: {free_until}")
    else:
        await update.message.reply_text("No free game information available yet.")

async def scrape_and_update(application: Application):
    logger.info("Starting scheduled scrape and update...")
    try:
        free_until, title = scrape_epic_games()
        if free_until and title:
            save_game_info(title, free_until.strftime("%Y-%m-%d %H:%M"))
            logger.info(f"New free game found and saved: {title}")
            await application.bot.send_message(chat_id=CHAT_ID, text=f"New free game found!\n{title}\nFree until: {free_until}") # Send notification
            # Schedule next scrape here:
            now = datetime.now()
            time_diff = free_until - now

            if time_diff > timedelta(0):
                logger.info(f"Scheduling next scrape in {time_diff}")
                aioschedule.clear()  # Clear any existing schedules

                application.job_queue.run_once(lambda c: scrape_and_update(application), when=free_until)
            else: # free_until is in the past
               tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
               logger.info(f"Scheduling for tomorrow at 10:00")
               application.job_queue.run_once(lambda c: scrape_and_update(application), when=tomorrow)
               aioschedule.every().day.at("10:00").do(lambda: scrape_and_update(application)) # Fallback to daily schedule
        else:
            tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
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


    application.job_queue.run_once(first_scrape_and_update(application) , when=0)

    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    application = (ApplicationBuilder()
               .token(BOT_TOKEN)
               .post_init(create_database)
               .job_queue(JobQueue())
               .build())

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("freegame", freegame))

    run_bot(application)