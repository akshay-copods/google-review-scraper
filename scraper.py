from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import asyncio
from typing import List, Dict, Optional
import logging
import os
import platform
import subprocess
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OwnerResponse:
    def __init__(self, text: str, date: str):
        self.text = text
        self.date = date

class Review:
    def __init__(self, author: str, rating: str, text: str, date: str, owner_response: Optional[OwnerResponse] = None):
        self.author = author
        self.rating = rating
        self.text = text
        self.date = date
        self.owner_response = owner_response

    def to_dict(self) -> Dict:
        return {
            "author": self.author,
            "rating": self.rating,
            "text": self.text,
            "date": self.date,
            "owner_response": {
                "text": self.owner_response.text,
                "date": self.owner_response.date
            } if self.owner_response else None
        }

class GoogleReviewsScraper:
    def __init__(self, max_reviews=500):
        self.driver = None
        self.max_reviews = max_reviews

    def _find_chromedriver_binary(self, base_path: str) -> str:
        """Find the actual chromedriver binary in the downloaded directory"""
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"ChromeDriver path does not exist: {base_path}")
        
        # Common chromedriver binary names
        binary_names = ['chromedriver', 'chromedriver.exe']
        
        # Search in the base directory first
        for binary_name in binary_names:
            binary_path = os.path.join(base_path, binary_name)
            if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
                logger.info(f"Found chromedriver binary at: {binary_path}")
                return binary_path
        
        # Search in subdirectories (for ARM64 Mac issues)
        for root, dirs, files in os.walk(base_path):
            for binary_name in binary_names:
                if binary_name in files:
                    binary_path = os.path.join(root, binary_name)
                    if os.access(binary_path, os.X_OK):
                        logger.info(f"Found chromedriver binary at: {binary_path}")
                        return binary_path
        
        raise FileNotFoundError(f"Could not find executable chromedriver binary in {base_path}")

    def setup_driver(self):
        """Setup Chrome WebDriver with necessary options"""
        if self.driver is not None:
            return

        try:
            chrome_options = Options()
            # Uncomment the next line to run in headless mode for faster execution
            # chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--lang=en-US") # Set language to English
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

            # Try to get chromedriver path and fix ARM64 macOS issues
            try:
                # Get the base path from ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriverManager returned path: {driver_path}")
                
                # Check if the returned path is actually the chromedriver binary
                if not os.access(driver_path, os.X_OK) or "THIRD_PARTY_NOTICES" in driver_path:
                    logger.warning(f"Invalid chromedriver path: {driver_path}. Searching for actual binary...")
                    # Get the directory containing the download
                    base_dir = os.path.dirname(driver_path)
                    driver_path = self._find_chromedriver_binary(base_dir)
                
                # Make sure the binary is executable
                os.chmod(driver_path, 0o755)
                
            except Exception as manager_error:
                logger.warning(f"ChromeDriverManager failed: {manager_error}")
                
                # Fallback: try to find chromedriver in system PATH
                chromedriver_system = shutil.which('chromedriver')
                if chromedriver_system:
                    driver_path = chromedriver_system
                    logger.info(f"Using system chromedriver at: {driver_path}")
                else:
                    raise Exception("Could not find chromedriver. Please install it manually or ensure Chrome is properly installed.")

            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup successful")
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise

    def _is_google_maps_url(self, input_str: str) -> bool:
        """Check if the input string is a Google Maps URL."""
        return input_str.startswith("https://www.google.com/maps/")

    async def scrape_reviews(self, business_name_or_url: str) -> List[Dict]:
        """
        Scrapes reviews for a given business name or Google Maps URL, handling scrolling, 'More' buttons, and duplicates.
        """
        self.setup_driver()

        try:
            if self._is_google_maps_url(business_name_or_url):
                search_url = business_name_or_url
            else:
                search_url = f"https://www.google.com/maps/search/{business_name_or_url.replace(' ', '+')}"
            logger.info(f"Accessing URL: {search_url}")
            self.driver.get(search_url)

            # Wait for and click the main "Reviews" tab to open the reviews panel
            try:
                reviews_button_selector = "button[aria-label*='Reviews']"
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, reviews_button_selector))
                ).click()
                logger.info("Clicked on the 'Reviews' tab.")
            except TimeoutException:
                raise Exception("Could not find or click the 'Reviews' tab. The page layout may have changed.")
            
            # Wait for the review panel to be visible
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium"))
            )
            
            # --- SCROLLING AND PARSING LOGIC ---
            reviews = []
            processed_review_ids = set()
            time.sleep(5)
            # Find the main scrollable reviews panel with class only m6QErb XiKgde and not any other class
            scrollable_div = self.driver.find_element(By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde")
            logger.info(f"scrollable_div----------------: {scrollable_div}")

            while len(reviews) < self.max_reviews:
                previous_reviews_count = len(reviews)
                
                # Find all review elements currently loaded in the DOM
                review_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium")

                for element in review_elements:
                    # Stop if we have reached the max number of reviews
                    if len(reviews) >= self.max_reviews:
                        break
                        
                    try:
                        # Use data-review-id for robust de-duplication
                        review_id = element.get_attribute("data-review-id")
                        if review_id in processed_review_ids:
                            continue

                        # --- PARSE A SINGLE REVIEW ---
                        author_name = element.find_element(By.CSS_SELECTOR, "div.d4r55").text
                        
                        # Get rating: Try primary selector, then fallback
                        try:
                            stars = element.find_element(By.CSS_SELECTOR, 'span[role="img"][aria-label*="stars"]').get_attribute("aria-label")
                        except NoSuchElementException:
                            stars = element.find_element(By.CSS_SELECTOR, "span.fzvQIb").text

                        # Get date: Try primary selector, then fallback
                        try:
                            review_date = element.find_element(By.CSS_SELECTOR, "span.rsqaWe").text
                        except NoSuchElementException:
                            review_date = element.find_element(By.CSS_SELECTOR, "span.xRkPPb").text

                        # Get text: Click "More" button if it exists
                        review_container = element.find_element(By.CSS_SELECTOR, "div.MyEned")
                        try:
                            more_button = review_container.find_element(By.CSS_SELECTOR, 'button[aria-label="See more"]')
                            self.driver.execute_script("arguments[0].click();", more_button)
                            time.sleep(0.5) # Wait for content to load
                        except NoSuchElementException:
                            pass # No "More" button, proceed
                        review_text = review_container.find_element(By.CSS_SELECTOR, "span.wiI7pd").text

                        # Get owner response (optional)
                        owner_response_obj = None
                        try:
                            response_container = element.find_element(By.CSS_SELECTOR, "div.CDe7pd")
                            response_text = response_container.find_element(By.CSS_SELECTOR, "div.wiI7pd").text
                            response_date = response_container.find_element(By.CSS_SELECTOR, "span.DZSIDd").text
                            owner_response_obj = OwnerResponse(text=response_text, date=response_date)
                        except NoSuchElementException:
                            pass

                        # Add the new, unique review
                        reviews.append(
                            Review(
                                author=author_name,
                                rating=stars,
                                text=review_text,
                                date=review_date,
                                owner_response=owner_response_obj
                            )
                        )
                        processed_review_ids.add(review_id)

                    except Exception as e:
                        logger.warning(f"Skipping a review due to parsing error: {str(e)}")
                        continue
                
                # Check if we should stop scrolling
                if len(reviews) >= self.max_reviews or len(reviews) == previous_reviews_count:
                    logger.info(f"Stopping scrape. Reached max reviews ({self.max_reviews}) or no new reviews loaded.")
                    break
                
                # Scroll the panel to load more reviews
                logger.info(f"Scrolling to load more reviews. Found {len(reviews)} so far.")
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(2) # Wait for new reviews to load

            logger.info(f"Successfully scraped {len(reviews)} reviews.")
            return [review.to_dict() for review in reviews]

        except Exception as e:
            logger.error(f"An unexpected error occurred during scraping: {str(e)}")
            raise

    def cleanup(self):
        """Clean up the WebDriver instance"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver has been closed.")