# Web Scraper Test API

A simplified web scraping API that runs without database dependencies for testing purposes.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r test_requirements.txt
```

### 2. Run the Test API
```bash
python test_scraper.py
```

Or directly:
```bash
python -m uvicorn test_api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test the API
```bash
python test_client.py
```

## 🌐 API Endpoints

- **GET /** - API information and documentation
- **POST /scrape** - Start a scraping task
- **GET /task/{task_id}** - Check task status
- **GET /result/{task_id}** - Get scraping results
- **GET /tasks** - List all tasks
- **GET /health** - Health check

## 📖 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Example Usage

### Start Scraping
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "depth": 1,
    "max_pages": 5,
    "include_images": false,
    "include_links": true
  }'
```

### Check Task Status
```bash
curl "http://localhost:8000/task/{task_id}"
```

### Get Results
```bash
curl "http://localhost:8000/result/{task_id}"
```

## 📊 What Gets Scraped

The API extracts the following data from web pages:

- **Title** - Page title
- **Headings** - H1, H2, H3, H4, H5, H6 tags
- **Paragraphs** - Meaningful text content
- **Links** - External and internal links
- **Images** - Image sources and alt text
- **Meta Data** - Meta tags and descriptions

## 🔧 Configuration Options

- **depth** - How deep to crawl (default: 1)
- **max_pages** - Maximum pages to scrape (default: 10)
- **include_images** - Whether to extract images (default: false)
- **include_links** - Whether to extract links (default: true)

## 🎯 Test URLs

Try these URLs for testing:

1. **https://httpbin.org/html** - Simple HTML test page
2. **https://example.com** - Basic website
3. **https://quotes.toscrape.com** - Quotes website with good content

## 📝 Sample Response

```json
{
  "base_url": "https://example.com",
  "pages_scraped": 1,
  "total_time": 2.34,
  "depth": 1,
  "max_pages": 5,
  "pages": [
    {
      "url": "https://example.com",
      "title": "Example Domain",
      "headings": ["Example Domain"],
      "paragraphs": ["This domain is for use in illustrative examples..."],
      "links": [...],
      "images": [...],
      "meta": {...},
      "content_length": 1256,
      "headings_count": 1,
      "paragraphs_count": 1,
      "links_count": 1,
      "images_count": 0,
      "scraped_at": "2024-01-15T10:30:00"
    }
  ],
  "summary": {
    "total_headings": 1,
    "total_paragraphs": 1,
    "total_links": 1,
    "total_images": 0,
    "total_content_length": 1256
  }
}
```

## 🚨 Important Notes

- **No Database**: This API stores data in memory only
- **No Authentication**: No login required for testing
- **No Persistence**: Data is lost when server restarts
- **Rate Limiting**: Be respectful of websites you scrape
- **Legal Compliance**: Only scrape websites you have permission to scrape

## 🔍 Troubleshooting

### Common Issues

1. **Port already in use**: Change port in `test_scraper.py`
2. **Import errors**: Make sure all dependencies are installed
3. **Network errors**: Check your internet connection
4. **Timeout errors**: Increase timeout in the client

### Debug Mode

Run with debug logging:
```bash
python -m uvicorn test_api:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## 🎉 Success Indicators

When everything is working:
- ✅ API starts without errors
- ✅ Health check returns "healthy"
- ✅ Scraping tasks complete successfully
- ✅ Results contain extracted data
- ✅ No database connection errors

Happy scraping! 🕷️ 