#!/usr/bin/env python3
"""
Simple monitoring API server for development mode
Provides mock data for the frontend monitoring components
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import logging
import asyncio
import sys
import os

# Add the current directory to the path so we can import the enhanced scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_scraper import EnhancedWebScraper, ScrapingConfig

# Try to import psutil, fall back to mock data if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("psutil not available, using mock system metrics")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringHandler(BaseHTTPRequestHandler):
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
            response_data = self.handle_request(path)
            self.wfile.write(json.dumps(response_data).encode())
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
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
    
    def handle_request(self, path):
        """Route GET requests and return appropriate mock data"""
        
        if path == '/api/metrics/system':
            return self.get_system_metrics()
            
        elif path == '/api/metrics/performance':
            return self.get_performance_metrics()
            
        elif path.startswith('/api/analytics/visualization/'):
            viz_type = path.split('/')[-1]
            return self.get_visualization_data(viz_type)
            
        elif path == '/api/health/detailed':
            return self.get_detailed_health()
            
        elif path == '/api/metrics/tasks':
            return self.get_task_metrics()
            
        elif path == '/health':
            return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
            
        else:
            return {'error': f'Unknown endpoint: {path}'}
    
    def handle_post_request(self, path, request_data):
        """Route POST requests and return appropriate responses"""
        
        if path == '/scrape-enhanced':
            return self.run_enhanced_scraper(request_data)
        else:
            return {'error': f'Unknown POST endpoint: {path}'}
    
    def run_enhanced_scraper(self, request_data):
        """Run the enhanced scraper with the provided parameters"""
        try:
            url = request_data.get('url', '')
            depth = request_data.get('depth', 1)
            max_pages = request_data.get('max_pages', 5)
            include_ml_analysis = request_data.get('include_ml_analysis', True)
            
            if not url:
                return {'error': 'URL is required'}
            
            # Configure the scraper
            config = ScrapingConfig(
                timeout=30,
                delay_between_requests=1.0,
                max_retries=2
            )
            
            # Run the scraper (simulate the enhanced scraper response)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._scrape_with_enhanced_scraper(url, config))
                return {
                    'status': 'success',
                    'result': self._format_enhanced_result(result, include_ml_analysis)
                }
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in enhanced scraper: {e}")
            return {'error': f'Scraping failed: {str(e)}'}
    
    async def _scrape_with_enhanced_scraper(self, url, config):
        """Actually run the enhanced scraper"""
        async with EnhancedWebScraper(config) as scraper:
            result = await scraper.scrape_url(url)
            return result
    
    def _format_enhanced_result(self, scraper_result, include_ml_analysis=True):
        """Format the scraper result to match the frontend expectations"""
        if "error" in scraper_result:
            return scraper_result
        
        # Convert single page result to multi-page format
        formatted_result = {
            'pages': [{
                'url': scraper_result['url'],
                'title': scraper_result['title'],
                'headings': [h['text'] for h in scraper_result['headings']],
                'paragraphs': scraper_result['paragraphs'],
                'links': [{'url': link['url'], 'text': link['text']} for link in scraper_result['links']],
                'images': [{'src': img['src'], 'alt': img['alt'], 'title': img['title']} 
                          for img in scraper_result['media']['images']],
                'meta': scraper_result['meta'],
                'content_length': scraper_result['content_length'],
                'headings_count': scraper_result['headings_count'],
                'paragraphs_count': scraper_result['paragraphs_count'],
                'links_count': scraper_result['links_count'],
                'images_count': scraper_result['images_count'],
                'scraped_at': scraper_result['scraped_at']
            }],
            'summary': {
                'total_pages': 1,
                'total_headings': scraper_result['headings_count'],
                'total_paragraphs': scraper_result['paragraphs_count'],
                'total_links': scraper_result['links_count'],
                'total_images': scraper_result['images_count'],
                'total_content_length': scraper_result['content_length']
            }
        }
        
        # Add mock ML analysis if requested
        if include_ml_analysis:
            formatted_result['ml_analysis'] = self._generate_mock_ml_analysis(scraper_result)
        
        return formatted_result
    
    def _generate_mock_ml_analysis(self, scraper_result):
        """Generate mock ML analysis data for the frontend"""
        # Mock sentiment analysis
        sentiment_score = random.uniform(-0.5, 0.5)
        sentiment_label = 'positive' if sentiment_score > 0.1 else 'negative' if sentiment_score < -0.1 else 'neutral'
        
        # Mock topics
        mock_topics = [
            {'topic': 'Technology', 'confidence': random.uniform(0.7, 0.9), 'keyword_matches': random.randint(5, 15)},
            {'topic': 'Business', 'confidence': random.uniform(0.6, 0.8), 'keyword_matches': random.randint(3, 10)},
            {'topic': 'Education', 'confidence': random.uniform(0.5, 0.7), 'keyword_matches': random.randint(2, 8)}
        ]
        
        # Mock keywords
        mock_keywords = [
            {'word': 'technology', 'frequency': random.randint(5, 20), 'importance': random.uniform(0.8, 1.0)},
            {'word': 'solution', 'frequency': random.randint(3, 15), 'importance': random.uniform(0.7, 0.9)},
            {'word': 'service', 'frequency': random.randint(2, 12), 'importance': random.uniform(0.6, 0.8)},
            {'word': 'customer', 'frequency': random.randint(2, 10), 'importance': random.uniform(0.5, 0.7)}
        ]
        
        mock_analysis = {
            'basic_stats': {
                'total_words': len(scraper_result['main_content'].split()),
                'unique_words': len(set(scraper_result['main_content'].lower().split())),
                'avg_word_length': 5.2,
                'avg_sentence_length': 15.3,
                'most_common_words': [['the', 45], ['and', 32], ['to', 28], ['of', 25], ['a', 22]],
                'vocabulary_diversity': 0.75
            },
            'readability': {
                'flesch_reading_ease': random.uniform(40, 80),
                'flesch_kincaid_grade': random.uniform(8, 12),
                'readability_level': random.choice(['Easy to read', 'Standard', 'Difficult to read'])
            },
            'sentiment': {
                'score': sentiment_score,
                'label': sentiment_label,
                'confidence': random.uniform(0.7, 0.9),
                'positive_words': random.randint(5, 20),
                'negative_words': random.randint(2, 10)
            },
            'topics': mock_topics,
            'keywords': mock_keywords,
            'content_type': {
                'primary_type': random.choice(['informational', 'commercial', 'educational', 'news']),
                'confidence': random.uniform(0.8, 0.95),
                'all_scores': {
                    'informational': random.uniform(0.6, 0.9),
                    'commercial': random.uniform(0.3, 0.7),
                    'educational': random.uniform(0.4, 0.8),
                    'news': random.uniform(0.2, 0.6)
                }
            },
            'language_detection': {
                'detected_language': 'English',
                'confidence': random.uniform(0.9, 0.99)
            },
            'duplicate_score': {
                'is_duplicate': False,
                'duplicate_score': random.uniform(0.1, 0.3),
                'first_seen': None
            },
            'summary': {
                'summary': scraper_result['main_content'][:200] + '...',
                'summary_length': 200,
                'compression_ratio': 0.15
            },
            'entities': {
                'emails': [],
                'urls': [link['url'] for link in scraper_result['links'][:3]],
                'phone_numbers': [],
                'dates': []
            }
        }
        
        return {
            'individual_analyses': [mock_analysis],
            'combined_analysis': mock_analysis,
            'cross_page_insights': {
                'dominant_topics': [['Technology', {'count': 1, 'total_confidence': 0.85}]],
                'average_sentiment': sentiment_score,
                'content_type_distribution': {'informational': 1},
                'total_pages_analyzed': 1
            }
        }
    
    def get_system_metrics(self):
        """Get system metrics using psutil if available, otherwise mock data"""
        try:
            if HAS_PSUTIL:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used': memory.used,
                    'memory_total': memory.total,
                    'disk_percent': disk.percent,
                    'disk_used': disk.used,
                    'disk_total': disk.total,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # Mock data when psutil is not available
                return {
                    'cpu_percent': random.randint(10, 70),
                    'memory_percent': random.randint(30, 80),
                    'memory_used': random.randint(2000000000, 8000000000),
                    'memory_total': 16000000000,
                    'disk_percent': random.randint(20, 60),
                    'disk_used': random.randint(50000000000, 200000000000),
                    'disk_total': 500000000000,
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                'cpu_percent': random.randint(10, 70),
                'memory_percent': random.randint(30, 80),
                'disk_percent': random.randint(20, 60),
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def get_performance_metrics(self):
        """Get mock performance metrics"""
        total_tasks = random.randint(50, 200)
        successful_tasks = int(total_tasks * random.uniform(0.75, 0.95))
        failed_tasks = total_tasks - successful_tasks
        
        return {
            'total_tasks': total_tasks,
            'success_rate': round((successful_tasks / total_tasks * 100), 2),
            'error_rate': round((failed_tasks / total_tasks * 100), 2),
            'average_duration': round(random.uniform(2, 15), 2),
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'response_times': {
                'mean': round(random.uniform(1, 5), 2),
                'median': round(random.uniform(1, 4), 2),
                'p95': round(random.uniform(5, 15), 2)
            }
        }
    
    def get_visualization_data(self, viz_type):
        """Get mock visualization data"""
        if viz_type == 'task_status_pie':
            completed = random.randint(50, 80)
            failed = random.randint(5, 15)
            pending = random.randint(3, 10)
            
            return {
                'data': [{
                    'type': 'pie',
                    'labels': ['Completed', 'Failed', 'Pending'],
                    'values': [completed, failed, pending],
                    'hoverinfo': 'label+percent',
                    'textinfo': 'value'
                }],
                'layout': {
                    'title': 'Task Status Distribution',
                    'showlegend': True,
                    'height': 400
                },
                'config': {
                    'displayModeBar': False
                }
            }
        
        elif viz_type == 'hourly_activity':
            hours = list(range(24))
            values = [random.randint(2, 20) for _ in hours]
            
            return {
                'data': [{
                    'type': 'bar',
                    'x': hours,
                    'y': values,
                    'name': 'Tasks per Hour'
                }],
                'layout': {
                    'title': 'Hourly Task Activity',
                    'xaxis': {'title': 'Hour of Day'},
                    'yaxis': {'title': 'Number of Tasks'},
                    'height': 400
                }
            }
        
        else:
            return {
                'data': [],
                'layout': {
                    'title': f'Mock {viz_type} visualization',
                    'showlegend': True
                },
                'config': {}
            }
    
    def get_detailed_health(self):
        """Get detailed health information"""
        try:
            system_metrics = self.get_system_metrics()
            performance_metrics = self.get_performance_metrics()
            
            # Determine health status
            health_status = "healthy"
            issues = []
            
            if system_metrics.get('cpu_percent', 0) > 80:
                health_status = "warning"
                issues.append("High CPU usage")
            
            if system_metrics.get('memory_percent', 0) > 85:
                health_status = "warning" 
                issues.append("High memory usage")
            
            if system_metrics.get('disk_percent', 0) > 90:
                health_status = "critical"
                issues.append("High disk usage")
            
            if performance_metrics.get('error_rate', 0) > 10:
                health_status = "warning"
                issues.append("High error rate")
            
            return {
                'status': health_status,
                'timestamp': system_metrics.get('timestamp'),
                'system_metrics': system_metrics,
                'performance_summary': performance_metrics,
                'issues': issues,
                'active_connections': random.randint(1, 5)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_task_metrics(self):
        """Get mock task metrics"""
        metrics = []
        for i in range(20):
            status = random.choice(['completed', 'failed', 'pending'])
            metrics.append({
                'task_id': f'task-{i}',
                'status': status,
                'duration': random.uniform(1, 10) if status == 'completed' else None,
                'created_at': (datetime.utcnow() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
                'response_time': random.uniform(0.5, 5.0)
            })
        return metrics

def run_server(port=8000):
    """Run the monitoring API server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MonitoringHandler)
    logger.info(f"Starting monitoring API server on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()