# Google Reviews Scraper API

This API allows you to scrape Google Reviews for any business by providing the business name.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have Chrome browser installed on your system.

## Running the API

Start the API server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Usage

### Endpoint: POST /reviews

Request body:
```json
{
    "business_names": ["Your Business Name"]
}
```

Response:
```json
{
    "status": "success",
    "data": [
        {
            "business_name": "Your Business Name",
            "reviews": [
                {
                    "author": "Reviewer Name",
                    "rating": "5 stars",
                    "text": "Review text",
                    "date": "Review date"
                }
            ]
        }
    ]
}
```

---

### Endpoint: POST /linkedin-profiles

Scrape employee profiles from a LinkedIn company page. You must provide your LinkedIn credentials.

Request body example:
```json
{
    "business_names": [
        "https://www.linkedin.com/company/ausco-modular/"
    ],
    "email": "your_email@example.com",
    "password": "your_linkedin_password"
}
```

Response example:
```json
{
    "status": "success",
    "data": [
        {
            "company_name": "ausco-modular",
            "profiles": [
                {
                    "name": "John Doe",
                    "subtitle": "Project Manager",
                    "profile_url": "https://www.linkedin.com/in/johndoe/",
                    "location": "Sydney, Australia",
                    "about": "Experienced project manager...",
                    "latest_job_title": "Project Manager",
                    "latest_job_company": "Ausco Modular"
                }
            ]
        },
        {
            "company_name": "atco-structures",
            "profiles": [
                // ... more profiles ...
            ]
        }
    ]
}
```

## Brightdata API usage: 

Use the response from /linkedin-profiles and update payload for following curl.

```
curl -H "Authorization: Bearer <BRIGHTDATA API_KEY>" -H "Content-Type: application/json" -d '[{"url":"https://www.linkedin.com/in/gadgetfather/"}]' "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_l1viktl72bvl7bjuj0&include_errors=true"
```

You can use below prompt with gemini 2.5 flash faster conversion - 
```
Here is my curl update it with following urls from my payload

curl 
curl -H "Authorization: Bearer <BRIGHTDATA API_KEY>" -H "Content-Type: application/json" -d '[{"url":"https://www.linkedin.com/in/gadgetfather/"}]' "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_l1viktl72bvl7bjuj0&include_errors=true"

my payload -
<RESPONSE RECEIVED FROM API CALL>

```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 