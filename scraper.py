from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import asyncio
from typing import List, Dict, Optional
import logging

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
    def __init__(self):
        self.driver = None
        self.setup_driver()
        self.max_reviews = 50

    def setup_driver(self):
        """Setup Chrome WebDriver with necessary options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup successful")
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise Exception(f"Failed to initialize Chrome WebDriver: {str(e)}")

    async def scrape_reviews(self, business_name: str) -> List[Dict]:
        """
        Scrape reviews for a given business name
        """
        if not self.driver:
            raise Exception("WebDriver not initialized")
            
        try:
            # Format the search URL
            search_url = f"https://www.google.com/maps/search/{business_name.replace(' ', '+')}"
            logger.info(f"Accessing URL: {search_url}")
            
            self.driver.get(search_url)
            
            # Wait for the reviews section to load with increased timeout
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for reviews section. Trying alternative selectors...")
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-review-id]"))
                    )
                except TimeoutException:
                    raise Exception("Could not find reviews section. The business might not have any reviews.")
            
            # Click on reviews tab if not already selected
            self._click_reviews_tab()
            
            # Load more reviews
            self._load_more_reviews()
            
            # Parse the reviews
            reviews = self._parse_reviews()
            if not reviews:
                logger.warning("No reviews found after parsing")
                return []
                
            return [review.to_dict() for review in reviews]
            
        except WebDriverException as e:
            logger.error(f"WebDriver error: {str(e)}")
            raise Exception(f"Error accessing Google Maps: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Error scraping reviews: {str(e)}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.error(f"Error closing WebDriver: {str(e)}")

    def _click_reviews_tab(self):
        """Click on the reviews tab if it exists"""
        try:
            # Try different selectors for the reviews tab
            review_tab_selectors = [
                "button[data-tab-index='1']",  # Common selector for reviews tab
                "button[aria-label*='Reviews']",  # Alternative selector
                "button[jsaction*='reviews']"  # Another alternative
            ]
            
            for selector in review_tab_selectors:
                try:
                    review_tab = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    review_tab.click()
                    logger.info("Clicked on reviews tab")
                    time.sleep(2)  # Wait for reviews to load
                    return
                except:
                    continue
                    
            logger.info("Reviews tab not found or already selected")
        except Exception as e:
            logger.warning(f"Error clicking reviews tab: {str(e)}")

    def _load_more_reviews(self):
        """Load more reviews by clicking the 'More reviews' button and scrolling"""
        try:
            # First scroll to load initial reviews
            self._scroll_reviews()
            
            # Try to find and click the "More reviews" button
            more_reviews_selectors = [
                "button[jsaction*='more-reviews']",
                "button[aria-label*='More reviews']",
                "button:contains('More reviews')"
            ]
            
            reviews_loaded = 0
            max_attempts = 10  # Maximum number of attempts to load more reviews
            
            while reviews_loaded < self.max_reviews and max_attempts > 0:
                # Try to find and click the "More reviews" button
                button_found = False
                for selector in more_reviews_selectors:
                    try:
                        more_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        self.driver.execute_script("arguments[0].click();", more_button)
                        button_found = True
                        logger.info("Clicked 'More reviews' button")
                        time.sleep(2)  # Wait for new reviews to load
                        break
                    except:
                        continue
                
                if not button_found:
                    # If no button found, try scrolling to load more
                    self._scroll_reviews()
                
                # Count current reviews
                current_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, "div[role='article']"))
                if current_reviews > reviews_loaded:
                    reviews_loaded = current_reviews
                    logger.info(f"Loaded {reviews_loaded} reviews so far")
                else:
                    max_attempts -= 1
                
                if reviews_loaded >= self.max_reviews:
                    logger.info(f"Reached maximum review limit of {self.max_reviews}")
                    break
                    
        except Exception as e:
            logger.warning(f"Error loading more reviews: {str(e)}")

    def _scroll_reviews(self):
        """Scroll through reviews to load more content"""
        try:
            # Try different selectors for the scrollable container
            scrollable_selectors = [
                "div[role='feed']",
                "div[data-review-id]",
                "div[class*='review']"
            ]
            
            for selector in scrollable_selectors:
                try:
                    scrollable_div = self.driver.find_element(By.CSS_SELECTOR, selector)
                    for i in range(3):
                        self.driver.execute_script(
                            "arguments[0].scrollTop = arguments[0].scrollHeight", 
                            scrollable_div
                        )
                        time.sleep(2)
                        logger.info(f"Scrolled reviews section {i+1}/3 times")
                    return
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error while scrolling reviews: {str(e)}")

    def _parse_reviews(self) -> List[Review]:
        """Parse the reviews from the page"""
        reviews = []
        try:
            # Try multiple possible selectors for review elements
            selectors = [
                "div[role='article']",
                "div[data-review-id]",
                "div[class*='review']"
            ]
            
            review_elements = []
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    review_elements = elements
                    break
            
            for element in review_elements[:self.max_reviews]:  # Limit to max_reviews
                try:
                    # Extract review data with multiple possible selectors
                    author = self._safe_find_text(element, ["div.d4r55", "div[class*='author']"])
                    rating = self._safe_find_attribute(element, "span[role='img']", "aria-label")
                    text = self._safe_find_text(element, ["span.wiI7pd", "div[class*='review-text']"])
                    date = self._safe_find_text(element, ["span.rsqaWe", "span[class*='date']"])
                    
                    if author and rating and text:  # Only add if we have the essential data
                        # Check for owner response
                        owner_response = self._parse_owner_response(element)
                        
                        review = Review(
                            author=author,
                            rating=rating,
                            text=text,
                            date=date or "Unknown date",
                            owner_response=owner_response
                        )
                        reviews.append(review)
                except Exception as e:
                    logger.warning(f"Error parsing individual review: {str(e)}")
                    continue
                    
            logger.info(f"Successfully parsed {len(reviews)} reviews")
            return reviews
            
        except Exception as e:
            logger.error(f"Error parsing reviews: {str(e)}")
            return []

    def _parse_owner_response(self, review_element) -> Optional[OwnerResponse]:
        """Parse owner response if it exists"""
        try:
            # Try different selectors for owner response
            response_selectors = [
                "div[class*='owner-response']",
                "div[class*='response']",
                "div[class*='reply']"
            ]
            
            for selector in response_selectors:
                try:
                    response_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    response_text = self._safe_find_text(response_element, [
                        "div[class*='text']",
                        "div[class*='content']",
                        "span"
                    ])
                    response_date = self._safe_find_text(response_element, [
                        "span[class*='date']",
                        "span[class*='time']"
                    ])
                    
                    if response_text:
                        return OwnerResponse(
                            text=response_text,
                            date=response_date or "Unknown date"
                        )
                except:
                    continue
                    
            return None
        except Exception as e:
            logger.warning(f"Error parsing owner response: {str(e)}")
            return None

    def _safe_find_text(self, element, selectors: List[str]) -> str:
        """Safely find text content using multiple possible selectors"""
        for selector in selectors:
            try:
                found = element.find_element(By.CSS_SELECTOR, selector)
                return found.text.strip()
            except:
                continue
        return ""

    def _safe_find_attribute(self, element, selector: str, attribute: str) -> str:
        """Safely find attribute value"""
        try:
            found = element.find_element(By.CSS_SELECTOR, selector)
            return found.get_attribute(attribute)
        except:
            return "" 