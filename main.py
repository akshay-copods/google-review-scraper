from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper import GoogleReviewsScraper
from linkedin_scraper import LinkedInScraper
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Business Data Scraper API",
    description="API to scrape Google Reviews and LinkedIn profiles for businesses",
    version="1.0.0"
)

class BusinessRequest(BaseModel):
    business_names: List[str]

class LinkedInRequest(BusinessRequest):
    email: str
    password: str

class ReviewResponse(BaseModel):
    author: str
    rating: str
    text: str
    date: str

class BusinessReviews(BaseModel):
    business_name: str
    reviews: List[ReviewResponse]

class APIResponse(BaseModel):
    status: str
    data: List[BusinessReviews]
    error: Optional[str] = None

class LinkedInProfileResponse(BaseModel):
    """
    Pydantic model to validate the structure of a scraped LinkedIn profile.
    This model reflects all the fields scraped by the latest version of the script.
    """
    name: str
    subtitle: Optional[str] = None
    profile_url: str
    location: Optional[str] = None
    about: Optional[str] = None
    latest_job_title: Optional[str] = None
    latest_job_company: Optional[str] = None

class CompanyProfiles(BaseModel):
    company_name: str
    profiles: List[LinkedInProfileResponse]

class LinkedInAPIResponse(BaseModel):
    status: str
    data: List[CompanyProfiles]
    error: Optional[str] = None

@app.post("/reviews", response_model=APIResponse)
async def get_reviews(request: BusinessRequest):
    scraper = None
    try:
        logger.info(f"Received request for businesses: {request.business_names}")
        scraper = GoogleReviewsScraper()
        all_business_reviews = []
        
        for business_name in request.business_names:
            try:
                reviews = await scraper.scrape_reviews(business_name)
                all_business_reviews.append({
                    "business_name": business_name,
                    "reviews": reviews
                })
            except Exception as e:
                logger.error(f"Error scraping reviews for {business_name}: {str(e)}")
                all_business_reviews.append({
                    "business_name": business_name,
                    "reviews": []
                })
        
        if not any(reviews["reviews"] for reviews in all_business_reviews):
            return APIResponse(
                status="success",
                data=all_business_reviews,
                error="No reviews found for any of the businesses"
            )
            
        return APIResponse(
            status="success",
            data=all_business_reviews
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        if scraper:
            scraper.cleanup()

@app.post("/linkedin-profiles", response_model=LinkedInAPIResponse)
async def get_linkedin_profiles(request: LinkedInRequest):
    scraper = None
    try:
        logger.info(f"Received LinkedIn request for businesses: {request.business_names}")
        scraper = LinkedInScraper(email=request.email, password=request.password)
        all_company_profiles = []
        
        for business_name in request.business_names:
            try:
                profiles = await scraper.scrape_company_employees(business_name)
                all_company_profiles.append({
                    "company_name": business_name,
                    "profiles": profiles
                })
            except Exception as e:
                logger.error(f"Error scraping LinkedIn profiles for {business_name}: {str(e)}")
                all_company_profiles.append({
                    "company_name": business_name,
                    "profiles": []
                })
        
        if not any(profiles["profiles"] for profiles in all_company_profiles):
            return LinkedInAPIResponse(
                status="success",
                data=all_company_profiles,
                error="No LinkedIn profiles found for any of the businesses"
            )
            
        return LinkedInAPIResponse(
            status="success",
            data=all_company_profiles
        )
    except Exception as e:
        logger.error(f"Error processing LinkedIn request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        if scraper:
            scraper.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 