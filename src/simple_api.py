#!/usr/bin/env python3
"""
Simple API server for the enhanced web scraper UI
Works without external dependencies - provides mock data for development
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        # Add CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        try:
            response_data = self.handle_get_request(path)
            self.wfile.write(json.dumps(response_data).encode())
        except Exception as e:
            logger.error(f"Error handling GET request {path}: {e}")
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Add CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(request_body) if request_body else {}
            
            response_data = self.handle_post_request(path, request_data)
            self.wfile.write(json.dumps(response_data).encode())
        except Exception as e:
            logger.error(f"Error handling POST request {path}: {e}")
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def handle_get_request(self, path):
        """Handle GET requests"""
        if path == '/health':
            return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
        else:
            return {'error': f'Unknown GET endpoint: {path}'}
    
    def handle_post_request(self, path, request_data):
        """Handle POST requests"""
        if path == '/scrape-enhanced':
            return self.create_mock_enhanced_result(request_data)
        else:
            return {'error': f'Unknown POST endpoint: {path}'}
    
    def create_mock_enhanced_result(self, request_data):
        """Create realistic mock data for the enhanced scraper"""
        url = request_data.get('url', 'https://example.com')
        include_ml_analysis = request_data.get('include_ml_analysis', True)
        
        # Generate realistic mock pages
        mock_pages = []
        page_count = random.randint(1, 3)
        
        for i in range(page_count):
            # Generate realistic content based on URL
            domain = urlparse(url).netloc or 'example.com'
            
            if 'news' in domain or 'blog' in domain:
                titles = [
                    f"Breaking: Major Development in Technology Sector",
                    f"Industry Analysis: Market Trends for 2024",
                    f"Expert Opinion: Future of Digital Innovation"
                ]
                content_type = 'news'
                sentiment = random.choice(['positive', 'neutral', 'negative'])
            elif 'shop' in domain or 'store' in domain or 'buy' in domain:
                titles = [
                    f"Premium Products - Shop Now",
                    f"Best Deals and Offers Available",
                    f"Product Catalog - Browse Collection"
                ]
                content_type = 'commercial'
                sentiment = 'positive'
            elif 'edu' in domain or 'learn' in domain or 'course' in domain:
                titles = [
                    f"Complete Guide to Web Development",
                    f"Advanced Programming Concepts",
                    f"Professional Skills Training"
                ]
                content_type = 'educational'
                sentiment = 'neutral'
            else:
                titles = [
                    f"Welcome to {domain}",
                    f"About Our Services",
                    f"Contact Information"
                ]
                content_type = 'informational'
                sentiment = 'neutral'
            
            # Generate content based on type
            if content_type == 'news':
                headings = [
                    f"Latest Updates",
                    f"Market Analysis",
                    f"Industry Impact",
                    f"Expert Commentary",
                    f"Looking Forward"
                ]
                paragraphs = [
                    "Recent developments in the technology sector have shown significant growth and innovation across multiple industries.",
                    "Market analysts report strong performance indicators suggesting continued expansion in the coming quarters.",
                    "Industry leaders are optimistic about future prospects and investment opportunities in emerging technologies.",
                    "Experts emphasize the importance of strategic planning and sustainable development practices.",
                    "The outlook remains positive with several breakthrough innovations expected to reshape the landscape."
                ]
            elif content_type == 'commercial':
                headings = [
                    f"Featured Products",
                    f"Special Offers",
                    f"Customer Reviews",
                    f"Shipping Info",
                    f"Support"
                ]
                paragraphs = [
                    "Discover our premium collection of products designed to meet your needs and exceed expectations.",
                    "Take advantage of limited-time offers and exclusive deals available for our valued customers.",
                    "Read testimonials from satisfied customers who have experienced the quality of our products.",
                    "We offer fast, reliable shipping options to ensure your order arrives safely and on time.",
                    "Our dedicated support team is available to assist with any questions or concerns you may have."
                ]
            elif content_type == 'educational':
                headings = [
                    f"Course Overview",
                    f"Learning Objectives",
                    f"Prerequisites",
                    f"Course Content",
                    f"Certification"
                ]
                paragraphs = [
                    "This comprehensive course provides in-depth knowledge and practical skills for professional development.",
                    "Students will gain hands-on experience through interactive exercises and real-world projects.",
                    "The curriculum is designed by industry experts to ensure relevant and up-to-date content.",
                    "Upon completion, participants will have mastered essential concepts and best practices.",
                    "Graduates receive recognized certification to validate their newly acquired expertise."
                ]
            else:
                headings = [
                    f"About Us",
                    f"Our Mission",
                    f"Services",
                    f"Team",
                    f"Contact"
                ]
                paragraphs = [
                    "We are committed to providing exceptional services and solutions that deliver real value to our clients.",
                    "Our mission is to drive innovation and excellence through collaborative partnerships and cutting-edge technology.",
                    "We offer a comprehensive range of services tailored to meet diverse business requirements.",
                    "Our experienced team brings together expertise from various disciplines to tackle complex challenges.",
                    "Get in touch with us to learn more about how we can help achieve your goals."
                ]
            
            # Create realistic links
            links = [
                {"url": f"{url}/page{i+1}", "text": f"Learn More"},
                {"url": f"{url}/contact", "text": "Contact Us"},
                {"url": f"{url}/about", "text": "About"},
            ]
            
            # Create realistic images
            images = [
                {"src": f"{url}/images/hero.jpg", "alt": "Hero Image", "title": "Main Banner"},
                {"src": f"{url}/images/content.jpg", "alt": "Content Image", "title": "Supporting Visual"},
            ]
            
            page = {
                "url": f"{url}" if i == 0 else f"{url}/page-{i+1}",
                "title": titles[i % len(titles)],
                "headings": headings[:random.randint(3, 5)],
                "paragraphs": paragraphs[:random.randint(3, 5)],
                "links": links,
                "images": images[:random.randint(1, 2)],
                "meta": {
                    "description": f"Page description for {titles[i % len(titles)]}",
                    "keywords": f"technology, innovation, {content_type}",
                    "author": "Content Team"
                },
                "content_length": random.randint(1500, 4000),
                "headings_count": len(headings[:random.randint(3, 5)]),
                "paragraphs_count": len(paragraphs[:random.randint(3, 5)]),
                "links_count": len(links),
                "images_count": len(images[:random.randint(1, 2)]),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
            mock_pages.append(page)
        
        # Create summary
        summary = {
            "total_pages": len(mock_pages),
            "total_headings": sum(p["headings_count"] for p in mock_pages),
            "total_paragraphs": sum(p["paragraphs_count"] for p in mock_pages),
            "total_links": sum(p["links_count"] for p in mock_pages),
            "total_images": sum(p["images_count"] for p in mock_pages),
            "total_content_length": sum(p["content_length"] for p in mock_pages)
        }
        
        result = {
            "pages": mock_pages,
            "summary": summary
        }
        
        # Add ML analysis if requested
        if include_ml_analysis:
            result["ml_analysis"] = self.generate_realistic_ml_analysis(mock_pages, content_type, sentiment)
        
        return {
            "status": "success",
            "result": result
        }
    
    def generate_realistic_ml_analysis(self, pages, content_type, sentiment):
        """Generate realistic ML analysis based on content"""
        
        # Determine sentiment score based on type
        if sentiment == 'positive':
            sentiment_score = random.uniform(0.2, 0.7)
        elif sentiment == 'negative':
            sentiment_score = random.uniform(-0.7, -0.2)
        else:
            sentiment_score = random.uniform(-0.1, 0.1)
        
        # Generate topics based on content type
        if content_type == 'news':
            topics = [
                {'topic': 'Technology', 'confidence': random.uniform(0.8, 0.9), 'keyword_matches': random.randint(10, 20)},
                {'topic': 'Business', 'confidence': random.uniform(0.7, 0.8), 'keyword_matches': random.randint(8, 15)},
                {'topic': 'Innovation', 'confidence': random.uniform(0.6, 0.7), 'keyword_matches': random.randint(5, 12)}
            ]
        elif content_type == 'commercial':
            topics = [
                {'topic': 'Products', 'confidence': random.uniform(0.8, 0.9), 'keyword_matches': random.randint(12, 25)},
                {'topic': 'Shopping', 'confidence': random.uniform(0.7, 0.8), 'keyword_matches': random.randint(8, 18)},
                {'topic': 'Customer Service', 'confidence': random.uniform(0.6, 0.7), 'keyword_matches': random.randint(5, 10)}
            ]
        elif content_type == 'educational':
            topics = [
                {'topic': 'Education', 'confidence': random.uniform(0.8, 0.9), 'keyword_matches': random.randint(15, 30)},
                {'topic': 'Learning', 'confidence': random.uniform(0.7, 0.8), 'keyword_matches': random.randint(10, 20)},
                {'topic': 'Skills', 'confidence': random.uniform(0.6, 0.7), 'keyword_matches': random.randint(8, 15)}
            ]
        else:
            topics = [
                {'topic': 'Information', 'confidence': random.uniform(0.7, 0.8), 'keyword_matches': random.randint(8, 15)},
                {'topic': 'Services', 'confidence': random.uniform(0.6, 0.7), 'keyword_matches': random.randint(5, 12)},
                {'topic': 'Company', 'confidence': random.uniform(0.5, 0.6), 'keyword_matches': random.randint(3, 8)}
            ]
        
        # Generate keywords
        keywords = [
            {'word': topics[0]['topic'].lower(), 'frequency': random.randint(8, 15), 'importance': random.uniform(0.8, 1.0)},
            {'word': 'solution', 'frequency': random.randint(5, 12), 'importance': random.uniform(0.7, 0.9)},
            {'word': 'quality', 'frequency': random.randint(4, 10), 'importance': random.uniform(0.6, 0.8)},
            {'word': 'professional', 'frequency': random.randint(3, 8), 'importance': random.uniform(0.5, 0.7)},
            {'word': 'experience', 'frequency': random.randint(3, 7), 'importance': random.uniform(0.5, 0.7)}
        ]
        
        # Calculate total words from content
        total_words = sum(len(' '.join(page['paragraphs']).split()) for page in pages)
        unique_words = int(total_words * random.uniform(0.3, 0.6))
        
        mock_analysis = {
            'basic_stats': {
                'total_words': total_words,
                'unique_words': unique_words,
                'avg_word_length': random.uniform(4.8, 5.5),
                'avg_sentence_length': random.uniform(12.0, 18.0),
                'most_common_words': [['the', 45], ['and', 32], ['to', 28], ['of', 25], ['a', 22]],
                'vocabulary_diversity': random.uniform(0.6, 0.8)
            },
            'readability': {
                'flesch_reading_ease': random.uniform(45, 75),
                'flesch_kincaid_grade': random.uniform(8, 12),
                'readability_level': random.choice(['Easy to read', 'Standard', 'Fairly easy to read'])
            },
            'sentiment': {
                'score': sentiment_score,
                'label': sentiment,
                'confidence': random.uniform(0.75, 0.92),
                'positive_words': random.randint(8, 25),
                'negative_words': random.randint(2, 8)
            },
            'topics': topics,
            'keywords': keywords,
            'content_type': {
                'primary_type': content_type,
                'confidence': random.uniform(0.85, 0.95),
                'all_scores': {
                    'informational': random.uniform(0.1, 0.9),
                    'commercial': random.uniform(0.1, 0.9),
                    'educational': random.uniform(0.1, 0.9),
                    'news': random.uniform(0.1, 0.9)
                }
            },
            'language_detection': {
                'detected_language': 'English',
                'confidence': random.uniform(0.95, 0.99)
            },
            'duplicate_score': {
                'is_duplicate': False,
                'duplicate_score': random.uniform(0.05, 0.25),
                'first_seen': None
            },
            'summary': {
                'summary': pages[0]['paragraphs'][0][:200] + '...' if pages else 'No content available for summary.',
                'summary_length': 200,
                'compression_ratio': random.uniform(0.12, 0.18)
            },
            'entities': {
                'emails': ['contact@example.com'] if random.random() > 0.5 else [],
                'urls': [page['url'] for page in pages[:2]],
                'phone_numbers': ['+1-555-0123'] if random.random() > 0.7 else [],
                'dates': [datetime.now().strftime('%Y-%m-%d')] if random.random() > 0.6 else []
            }
        }
        
        return {
            'individual_analyses': [mock_analysis for _ in pages],
            'combined_analysis': mock_analysis,
            'cross_page_insights': {
                'dominant_topics': [[topic['topic'], {'count': len(pages), 'total_confidence': topic['confidence']}] for topic in topics[:3]],
                'average_sentiment': sentiment_score,
                'content_type_distribution': {content_type: len(pages)},
                'total_pages_analyzed': len(pages)
            }
        }

def run_server(port=8000):
    """Run the simple API server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleAPIHandler)
    logger.info(f"🚀 Simple API server running on http://localhost:{port}")
    logger.info(f"📊 Enhanced scraper endpoint: POST http://localhost:{port}/scrape-enhanced")
    logger.info(f"💡 UI should connect to this server for scraping functionality")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️  Shutting down server")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()