#!/usr/bin/env python3
"""
Test runner for the Web Scraper Test API
"""

import sys
import os
import uvicorn
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from test_api import app

def main():
    """Main function to run the test API"""
    print("🎯 Web Scraper Test API")
    print("This API runs without database for testing scraping functionality")
    print()
    print("🚀 Starting server...")
    print("🌐 API will be available at: http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("=" * 50)
    
    uvicorn.run(
        "src.test_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 