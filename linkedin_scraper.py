import time
import random
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.driver = None
        self.scraped_profiles = set() # Use a set to store unique profiles (name, role)
        self.is_logged_in = False

    def extract_company_username(self, company_input: str) -> str:
        """
        Extract LinkedIn company username from URL or return the input as is.
        Handles URLs like: https://www.linkedin.com/company/ausco-modular/
        """
        if company_input.startswith('http'):
            # Extract username from LinkedIn company URL
            pattern = r'linkedin\.com/company/([^/?]+)'
            match = re.search(pattern, company_input)
            if match:
                return match.group(1)
            else:
                logger.warning(f"Could not extract username from URL: {company_input}")
                return company_input
        else:
            # If it's not a URL, return as is (assuming it's already a username)
            return company_input

    def setup_driver(self):
        if self.driver is not None:
            return
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Uncomment for headless
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--lang=en-US")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup successful for LinkedIn")
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise

    def human_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))

    def check_if_logged_in(self):
        """Check if we're already logged into LinkedIn"""
        try:
            # Check if we're on the feed page or if there's a profile menu
            current_url = self.driver.current_url
            if "linkedin.com/feed" in current_url or "linkedin.com/mynetwork" in current_url:
                return True
            
            # Check for profile menu or logout button
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label*='profile']"))
                )
                return True
            except TimeoutException:
                pass
            
            return False
        except Exception:
            return False

    def login(self):
        """Login to LinkedIn with improved error handling and human-like behavior"""
        self.setup_driver()
        
        # Check if already logged in
        if self.check_if_logged_in():
            logger.info("Already logged into LinkedIn")
            self.is_logged_in = True
            return
        
        # Navigate to login page
        self.driver.get("https://www.linkedin.com/login")
        self.human_delay(2, 4)
        
        try:
            # Wait for page to load and find email field
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Human-like typing for email
            for char in self.email:
                email_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            self.human_delay(1, 2)
            
            # Find and fill password field
            password_input = self.driver.find_element(By.ID, "password")
            for char in self.password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            self.human_delay(1, 2)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            login_button.click()
            
            # Wait for login to complete
            self.human_delay(3, 6)
            
            # Check if login was successful
            if self.check_if_logged_in():
                logger.info("Successfully logged in to LinkedIn")
                self.is_logged_in = True
            else:
                # Check for common login issues
                try:
                    error_message = self.driver.find_element(By.CSS_SELECTOR, ".alert-error, .error-message")
                    logger.error(f"Login failed: {error_message.text}")
                    raise Exception(f"Login failed: {error_message.text}")
                except NoSuchElementException:
                    logger.error("Login failed: Unknown error")
                    raise Exception("Login failed: Unknown error")
                    
        except TimeoutException:
            logger.error("Timeout waiting for login page to load")
            raise Exception("Timeout waiting for login page to load")
        except Exception as e:
            logger.error(f"LinkedIn login failed: {str(e)}")
            raise

    def scroll_to_element(self, by_locator):
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(by_locator)
            )
            # Scroll the element into view using JavaScript
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            self.human_delay(1, 2)
            logger.info(f"Scrolled to element located by {by_locator}")
            return True
        except TimeoutException:
            logger.warning(f"Timeout while waiting for element to scroll: {by_locator}")
            return False
        except NoSuchElementException:
            logger.warning(f"Element not found for scrolling: {by_locator}")
            return False
        except Exception as e:
            logger.error(f"Error while scrolling to element {by_locator}: {str(e)}")
            return False

    def scroll_to_bottom(self):
        # This function continuously scrolls to the very bottom of the page
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.human_delay(2, 4) # Longer delay for full page scroll
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logger.info("Scrolled to the bottom of the page.")


    def extract_profiles(self):
        profiles = []
        try:
            # Find all profile cards within the "People you may know" section or similar list items
            # Using a more general XPath to catch various list item structures for profiles
            profile_cards = self.driver.find_elements(By.XPATH, '//ul[contains(@class, "display-flex")]/li[contains(@class, "org-people-profile-card__profile-card-spacing")]')

            for card in profile_cards:
                name = "N/A"
                role = "N/A"
                profile_url = ""
                try:
                    # Extract name from the element with class 'IbXSFTBYTyznEViQKLhnyJdaNacpfgWZHYkE link-without-visited-state'
                    # and then get the text from its child div
                    name_element = card.find_element(By.CSS_SELECTOR, '.IbXSFTBYTyznEViQKLhnyJdaNacpfgWZHYkE.link-without-visited-state div.lt-line-clamp--single-line')
                    name = name_element.text.strip()
                    
                    # Try to extract profile URL from the link element
                    try:
                        link_element = card.find_element(By.CSS_SELECTOR, '.IbXSFTBYTyznEViQKLhnyJdaNacpfgWZHYkE.link-without-visited-state')
                        profile_url = link_element.get_attribute('href') or ""
                    except NoSuchElementException:
                        profile_url = ""
                        
                except NoSuchElementException:
                    logger.warning("Name element not found for a profile card.")
                except StaleElementReferenceException:
                    logger.warning("Stale element reference for name, skipping this card for now.")
                    continue # Skip to the next card if this element is stale

                try:
                    # Extract role from the element with class 'ember-view lt-line-clamp lt-line-clamp--multi-line'
                    role_element = card.find_element(By.CSS_SELECTOR, 'div.artdeco-entity-lockup__subtitle .lt-line-clamp--multi-line')
                    role = role_element.text.strip()
                except NoSuchElementException:
                    logger.warning(f"Role element not found for profile: {name}.")
                except StaleElementReferenceException:
                    logger.warning("Stale element reference for role, skipping this card for now.")
                    continue # Skip to the next card if this element is stale
                
                # Add to set to handle duplicates (tuple for immutability)
                profile_key = (name, role)
                if profile_key not in self.scraped_profiles:
                    profiles.append({
                        "name": name, 
                        "subtitle": role, 
                        "profile_url": profile_url
                    })
                    self.scraped_profiles.add(profile_key)

        except Exception as e:
            logger.error(f"Error during profile extraction: {str(e)}")
        return profiles


    async def scrape_company_employees(self, company_input: str):
        # Extract company username from URL or use input directly
        company_username = self.extract_company_username(company_input)
        logger.info(f"Using company username: {company_username}")
        
        # Login only once at the beginning
        if not self.is_logged_in:
            self.login()
        
        # Navigate to company people page
        people_url = f"https://www.linkedin.com/company/{company_username}/people/"
        logger.info(f"Navigating to {people_url}")
        self.driver.get(people_url)
        self.human_delay(3, 6)
        
        # Wait for the page to load and check if it's accessible
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.org-people-profile-card__card-spacing"))
            )
        except TimeoutException:
            logger.warning(f"Could not find profile cards for {company_username}. Company page might not exist or be private.")
            return []

        # Scroll to the container with class org-people-profile-card__card-spacing
        self.scroll_to_element((By.CSS_SELECTOR, "div.org-people-profile-card__card-spacing"))
        self.human_delay(2, 3)

        all_employees = []
        previous_number_of_employees = 0

        while True:
            # Scroll to the bottom to load more content, especially important after initial section scroll
            self.scroll_to_bottom()
            self.human_delay(2, 3) # Give some time for new content to load

            # Extract currently visible profiles
            current_profiles = self.extract_profiles()
            all_employees.extend(current_profiles)
            
            logger.info(f"Found {len(all_employees)} unique profiles so far.")

            # Try to click the "Show more results" button
            try:
                show_more_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.scaffold-finite-scroll__load-button'))
                )
                self.driver.execute_script("arguments[0].click();", show_more_button)
                self.human_delay(3, 5) # Longer delay after clicking to allow new content to load
                
                # Check if new profiles were added after clicking "Show more"
                if len(all_employees) == previous_number_of_employees:
                    logger.info("No new profiles loaded after clicking 'Show more results'. Assuming end of list.")
                    break
                previous_number_of_employees = len(all_employees)

            except TimeoutException:
                logger.info(" 'Show more results' button not found or not clickable. Assuming all results are loaded.")
                break
            except NoSuchElementException:
                logger.info(" 'Show more results' button not found. Assuming all results are loaded.")
                break
            except StaleElementReferenceException:
                logger.info(" 'Show more results' button became stale, attempting to re-find and click.")
                self.human_delay(1,2)
                continue # Try again in the next loop iteration

        logger.info(f"Completed scraping {len(all_employees)} profiles for {company_username}")
        return all_employees # Return the profiles as a list of dictionaries

    def cleanup(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False
            logger.info("WebDriver has been closed.")

