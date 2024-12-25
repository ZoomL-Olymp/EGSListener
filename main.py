import logging
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(filename='epic_games_scraper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_free_games():
    start_time = time.time()  # Record start time

    options = Options()
    options.add_argument("--headless=new")
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'user-agent={user_agent}')

    logging.info(f"Starting scraping with User-Agent: {user_agent}")

    try:
        with webdriver.Chrome(options=options) as driver:
            driver.get("https://store.epicgames.com/en-US/")

            try:  # Use a shorter timeout if possible
                title_element = WebDriverWait(driver, 2).until( # Reduced timeout
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h6.eds_1ypbntd0.eds_1ypbntd7.eds_1ypbntdq"))
                )
                title = title_element.text

                date_elements = WebDriverWait(driver, 2).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "time"))
                )

                date1 = date_elements[0].text
                date2 = date_elements[1].text
                date = f"{date1} {date2}"

                end_time = time.time()
                elapsed_time = end_time - start_time

                logging.info(f"Scraping completed successfully in {elapsed_time:.2f} seconds.")
                return date, title

            except Exception as e:
                logging.error(f"Error finding elements: {e}")
                return None, None

    except Exception as e:  # Catch WebDriver exceptions
        logging.exception(f"An unexpected error occurred during web driver initialization: {e}") # Log and re-raise exception so program exists on critical error
        raise # re-raise to stop execution

if __name__ == "__main__":
    try:
        date, title = get_free_games()
        if date and title:
            print(f"Free until: {date}")
            print(f"Title: {title}")
    except Exception as e:
        print(f"A critical error occurred: {e}")
    input("End of program. Press enter to exit...")