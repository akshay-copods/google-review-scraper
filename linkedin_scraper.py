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

# --- Basic Configuration ---
# Sets up logging to display informational messages during the scraping process.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInScraper:
    """
    A class to scrape employee profiles from a LinkedIn company page,
    including details like location, about section, and latest job from individual profiles.
    This version includes more human-like delays and scrolling to avoid detection.
    """
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.driver = None
        self.scraped_profiles = set() # Use a set of tuples (name, role) to track unique profiles.
        self.is_logged_in = False

    def extract_company_username(self, company_input: str) -> str:
        """
        Extracts the LinkedIn company username from a full URL.
        If the input is not a URL, it's assumed to be the username already.
        Example: 'https://www.linkedin.com/company/google/' -> 'google'
        """
        if company_input.startswith('http'):
            pattern = r'linkedin\.com/company/([^/?]+)'
            match = re.search(pattern, company_input)
            if match:
                return match.group(1)
            else:
                logger.warning(f"Could not extract a valid company username from URL: {company_input}")
                return company_input
        else:
            # Assumes the input is already a username if it's not a URL.
            return company_input

    def setup_driver(self):
        """Initializes the Selenium Chrome WebDriver with appropriate options."""
        if self.driver is not None:
            return
        try:
            chrome_options = Options()
            # Recommended options for running in a containerized or headless environment.
            # chrome_options.add_argument("--headless=new") # Commented out as per user request
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--lang=en-US")
            # Options to make the browser appear more like a regular user's browser.
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver setup complete.")
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {e}")
            raise

    def human_delay(self, min_sec=2, max_sec=5):
        """
        Pauses execution for a random duration to mimic human behavior.
        Increased default delay for more realistic interactions.
        """
        time.sleep(random.uniform(min_sec, max_sec))

    def check_if_logged_in(self):
        """Checks if the current session is already logged into LinkedIn."""
        try:
            self.driver.find_element(By.CSS_SELECTOR, "button[id^='ember'][aria-label*='Account']")
            return True
        except NoSuchElementException:
            return "linkedin.com/feed" in self.driver.current_url
        except Exception:
            return False

    def login(self):
        """Logs into LinkedIn using the provided credentials with human-like typing."""
        self.setup_driver()
        
        self.driver.get("https://www.linkedin.com/login")
        
        if self.check_if_logged_in():
            logger.info("Already logged into LinkedIn.")
            self.is_logged_in = True
            return
        
        logger.info("Attempting to log in to LinkedIn...")
        self.human_delay(3, 6) # Longer initial delay on login page
        
        try:
            email_input = WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
            for char in self.email:
                email_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3)) # Randomized typing speed
            
            self.human_delay(1, 2)
            
            password_input = self.driver.find_element(By.ID, "password")
            for char in self.password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            self.human_delay(2, 4) # Pause before clicking login
            
            self.driver.find_element(By.XPATH, '//button[@type="submit"]').click()
            
            WebDriverWait(self.driver, 25).until(EC.url_contains("linkedin.com/feed"))
            logger.info("Successfully logged in to LinkedIn.")
            self.is_logged_in = True
                    
        except TimeoutException:
            logger.error("Timeout during login. The page might have a CAPTCHA or the login flow has changed.")
            raise Exception("Timeout during login. A manual check might be required.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during LinkedIn login: {e}")
            raise

    def scroll_like_human(self):
        """
        Scrolls the page down in random increments to mimic human scrolling behavior.
        """
        logger.info("Scrolling page with human-like behavior...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down by a random fraction of the window height
            scroll_increment = random.uniform(0.4, 0.8)
            self.driver.execute_script(f"window.scrollBy(0, window.innerHeight * {scroll_increment});")
            self.human_delay(1, 3) # Wait after a scroll
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # If height hasn't changed, try one last scroll to the absolute bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.human_delay(2, 4)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break # Exit if we're truly at the bottom
            last_height = new_height
        logger.info("Finished human-like scrolling.")


    def scrape_profile_details(self, profile_url: str) -> dict:
        """
        Navigates to an individual profile URL and scrapes details with human-like pauses.
        """
        self.driver.get(profile_url)
        self.human_delay(4, 7) # Longer delay for profile page to load fully
        details = {
            "location": "N/A", 
            "about": "N/A",
            "latest_job_title": "N/A",
            "latest_job_company": "N/A"
        }

        try:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        except TimeoutException:
            logger.warning(f"Timeout waiting for profile page to load: {profile_url}")
            return details

        # --- Scrape Location ---
        try:
            location_element = self.driver.find_element(By.XPATH, "//a[contains(@href, '/contact-info/')]/ancestor::div[1]/span[1]")
            details["location"] = location_element.text.strip()
            logger.info(f"  [SUCCESS] Found Location: {details['location']}")
        except NoSuchElementException:
            try:
                location_element = self.driver.find_element(By.XPATH, "//div[contains(@class, 'mt2')]/span[contains(@class, 'text-body-small')]")
                details["location"] = location_element.text.strip()
                logger.info(f"  [SUCCESS-FALLBACK] Found Location: {details['location']}")
            except NoSuchElementException:
                 logger.warning(f"  [INFO] Location not found for {profile_url}")
        
        self.human_delay(1, 2)

        # --- Scrape About Section ---
        try:
            about_section = self.driver.find_element(By.XPATH, "//div[@id='about']/ancestor::section")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", about_section)
            self.human_delay(2, 4)
            logger.info("  [INFO] Scrolled to 'About' section.")

            text_container = about_section.find_element(By.XPATH, ".//div[contains(@class, 'inline-show-more-text')]")
            
            try:
                see_more_button = text_container.find_element(By.CSS_SELECTOR, "button.inline-show-more-text__button")
                if see_more_button.is_displayed():
                    self.driver.execute_script("arguments[0].click();", see_more_button)
                    self.human_delay(1, 3)
                    logger.info("  [INFO] Clicked '…see more' in About section.")
            except NoSuchElementException:
                logger.info("  [INFO] '…see more' button not found, scraping visible text.")

            about_text_element = text_container.find_element(By.CSS_SELECTOR, "span[aria-hidden='true']")
            details["about"] = about_text_element.text.strip()
            logger.info(f"  [SUCCESS] Found About section content.")
        except NoSuchElementException:
            logger.warning(f"  [INFO] About section not found for {profile_url}")
        except Exception as e:
            logger.error(f"  [ERROR] An unexpected error occurred while scraping About section: {e}")
        
        self.human_delay(1, 3)

        # --- Scrape Most Recent Job ---
        try:
            experience_section = self.driver.find_element(By.XPATH, "//div[@id='experience']/ancestor::section")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", experience_section)
            self.human_delay(2, 4)
            
            latest_job_element = experience_section.find_element(By.XPATH, ".//ul/li[1]")
            
            job_title_element = latest_job_element.find_element(By.XPATH, ".//div[contains(@class, 'display-flex') and contains(@class, 'align-items-center') and contains(@class, 'mr1')]/span[@aria-hidden='true']")
            details["latest_job_title"] = job_title_element.text.strip()

            company_element = latest_job_element.find_element(By.XPATH, ".//span[contains(@class, 't-normal')]/span[@aria-hidden='true']")
            details["latest_job_company"] = company_element.text.strip()
            
            logger.info(f"  [SUCCESS] Found Latest Job: {details['latest_job_title']} at {details['latest_job_company']}")
        except NoSuchElementException:
            logger.warning(f"  [INFO] Most recent job not found for {profile_url}")
        except Exception as e:
            logger.error(f"  [ERROR] An unexpected error occurred while scraping latest job: {e}")

        logger.info(f"  [DETAILS] Returning details for {profile_url}: {details}")
        return details

    def extract_profiles(self):
        """
        Extracts all visible employee profiles from the current company "People" page view.
        """
        profiles = []
        try:
            profile_cards = self.driver.find_elements(By.XPATH, '//li[contains(@class, "org-people-profile-card")]')
            
            for card in profile_cards:
                name, role, profile_url = "N/A", "N/A", ""
                try:
                    link_element = card.find_element(By.CSS_SELECTOR, 'div.artdeco-entity-lockup__title a[data-test-app-aware-link]')
                    profile_url = link_element.get_attribute('href') or ""
                    name = link_element.find_element(By.CSS_SELECTOR, 'div').text.strip()
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

                try:
                    role_element = card.find_element(By.CSS_SELECTOR, 'div.artdeco-entity-lockup__subtitle div.lt-line-clamp--multi-line')
                    role = role_element.text.strip()
                except NoSuchElementException:
                    pass
                
                profile_key = (name, role)
                if name != "N/A" and (name, role) not in self.scraped_profiles:
                    profiles.append({
                        "name": name, 
                        "subtitle": role, 
                        "profile_url": profile_url
                    })
                    self.scraped_profiles.add(profile_key)

        except Exception as e:
            logger.error(f"An unexpected error occurred during profile extraction: {e}")
        return profiles

    async def scrape_company_employees(self, company_input: str):
        """
        Main method to orchestrate the scraping of a company's employee list.
        """
        company_username = self.extract_company_username(company_input)
        logger.info(f"Starting scrape for company: {company_username}")
        
        if not self.is_logged_in:
            self.login()
        
        people_url = f"https://www.linkedin.com/company/{company_username}/people/"
        logger.info(f"Navigating to people page: {people_url}")
        self.driver.get(people_url)
        self.human_delay(4, 7) # Wait longer for the initial people page to load
        
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//li[contains(@class, "org-people-profile-card")]'))
            )
            logger.info("People page loaded successfully.")
        except TimeoutException:
            logger.warning(f"Could not find any profile cards for '{company_username}'. The page may be private or have no listed employees.")
            return []

        # This list will hold the dict for each unique profile found
        all_employees_on_page = []
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            # Store the number of unique profiles found so far
            count_before = len(self.scraped_profiles)
            
            # Scroll to the bottom to load profiles
            self.scroll_like_human()
            
            # Extract new profiles and add them to our main list
            new_profiles = self.extract_profiles()
            all_employees_on_page.extend(new_profiles)
            
            # Try to find and click the "Show more results" button
            try:
                show_more_button = WebDriverWait(self.driver, 7).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Show more results']] | //button[text()='Show more results']"))
                )
                self.driver.execute_script("arguments[0].click();", show_more_button)
                logger.info(f"Clicked 'Show more results' button. (Attempt {retry_count + 1}/{max_retries})")
                self.human_delay(4, 6) # Wait for new profiles to load
                retry_count += 1
            except TimeoutException:
                logger.info("'Show more results' button not found. No more profiles to load.")
                break
            except Exception as e:
                logger.warning(f"An error occurred while trying to click 'Show more': {e}")
                retry_count += 1
                continue

            # If no new unique profiles were found in this iteration, increment retry count
            if len(self.scraped_profiles) == count_before:
                logger.info(f"No new profiles found in this iteration. (Attempt {retry_count}/{max_retries})")
                retry_count += 1
            else:
                # Reset retry count if we found new profiles
                retry_count = 0

        if retry_count >= max_retries:
            logger.info(f"Reached maximum retries ({max_retries}). Finalizing list.")

        logger.info(f"Initial scan complete. Found {len(all_employees_on_page)} unique profiles for '{company_username}'.")
        logger.info("Now scraping individual profile details (location, about, and latest job)...")
        
        final_employee_list = []
        # for i, employee in enumerate(all_employees_on_page):
        #     logger.info(f"--- Processing profile {i + 1}/{len(all_employees_on_page)}: {employee.get('name', 'N/A')} ---")
        #     profile_url = employee.get("profile_url")
        #     # if profile_url:
        #     #     clean_url = profile_url.split('?')[0]
        #     #     details = self.scrape_profile_details(clean_url)
        #     #     employee.update(details)
        #     final_employee_list.append(employee)
        #     logger.info(f"  [MERGED] Updated employee data: {employee}")
        #     self.human_delay(3, 6) # Longer, more human-like pause between visiting profiles

        logger.info(f"Scraping complete. Processed details for {len(final_employee_list)} profiles.")
        return all_employees_on_page

    def cleanup(self):
        """Closes the WebDriver and resets the state."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False
            logger.info("WebDriver has been closed and resources released.")