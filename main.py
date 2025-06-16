from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper import GoogleReviewsScraper
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Reviews Scraper API",
    description="API to scrape Google Reviews for businesses",
    version="1.0.0"
)

class BusinessRequest(BaseModel):
    business_name: str

class ReviewResponse(BaseModel):
    author: str
    rating: str
    text: str
    date: str

class APIResponse(BaseModel):
    status: str
    data: List[ReviewResponse]
    error: Optional[str] = None

@app.post("/reviews", response_model=APIResponse)
async def get_reviews(request: BusinessRequest):
    try:
        logger.info(f"Received request for business: {request.business_name}")
        scraper = GoogleReviewsScraper()
        reviews = await scraper.scrape_reviews(request.business_name)
        
        if not reviews:
            return APIResponse(
                status="success",
                data=[],
                error="No reviews found for this business"
            )
            
        return APIResponse(
            status="success",
            data=reviews
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 