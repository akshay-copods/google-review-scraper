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
    "business_name": "Your Business Name"
}
```

Response:
```json
{
    "status": "success",
    "data": [
        {
            "author": "Reviewer Name",
            "rating": "5 stars",
            "text": "Review text",
            "date": "Review date"
        },
        ...
    ]
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 