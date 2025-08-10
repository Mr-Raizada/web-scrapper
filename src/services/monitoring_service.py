from datetime import datetime
import psutil
import logging
from fastapi import WebSocket
from typing import Dict, List
import asyncio
from collections import deque
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

class MonitoringService:
    def __init__(self):
        self.tasks_history = deque(maxlen=1000)  # Store last 1000 tasks
        self.active_connections: List[WebSocket] = []
        self.system_stats = {
            'cpu_usage': deque(maxlen=60),  # Last 60 readings
            'memory_usage': deque(maxlen=60),
            'disk_usage': deque(maxlen=60)
        }
        
        # Development mode check
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # MongoDB connection for persistent storage (only in production)
        self.client = None
        self.db = None
        
        if not self.dev_mode:
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
            self.db = self.client.scraper_db
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logging.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
    async def broadcast_metrics(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            await self.disconnect(connection)
                
    def get_system_metrics(self) -> Dict:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used': memory.used,
                'memory_total': memory.total,
                'disk_percent': disk.percent,
                'disk_used': disk.used,
                'disk_total': disk.total,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store in history
            self.system_stats['cpu_usage'].append(cpu_percent)
            self.system_stats['memory_usage'].append(memory.percent)
            self.system_stats['disk_usage'].append(disk.percent)
            
            return metrics
        except Exception as e:
            logging.error(f"Error getting system metrics: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
        
    async def log_task_metrics(self, task_id: str, metrics: Dict):
        log_entry = {
            'task_id': task_id,
            'timestamp': datetime.utcnow().isoformat(),
            **metrics
        }
        self.tasks_history.append(log_entry)
        
        # Store in MongoDB for persistence (only in production)
        if not self.dev_mode and self.db:
            try:
                await self.db.task_metrics.insert_one(log_entry)
            except Exception as e:
                logging.error(f"Error storing task metrics in MongoDB: {e}")
        
        logging.info(f"Task metrics logged: {log_entry}")
        
    async def get_task_metrics(self, limit: int = 100) -> List[Dict]:
        """Get task metrics from MongoDB or in-memory storage"""
        try:
            if self.dev_mode or not self.db:
                # Use in-memory storage for development
                return list(self.tasks_history)[-limit:] if self.tasks_history else []
            else:
                cursor = self.db.task_metrics.find().sort("timestamp", -1).limit(limit)
                metrics = []
                async for metric in cursor:
                    metrics.append(metric)
                return metrics
        except Exception as e:
            logging.error(f"Error retrieving task metrics: {e}")
            return []
        
    async def get_system_history(self, hours: int = 24) -> Dict:
        """Get system metrics history"""
        try:
            if self.dev_mode or not self.db:
                # Generate mock data for development
                import random
                from datetime import timedelta
                now = datetime.utcnow()
                
                history = {
                    'cpu': [],
                    'memory': [],
                    'disk': [],
                    'timestamps': []
                }
                
                # Generate hourly data points
                for i in range(hours):
                    timestamp = now - timedelta(hours=hours-i)
                    history['cpu'].append(random.randint(10, 80))
                    history['memory'].append(random.randint(30, 70))
                    history['disk'].append(random.randint(20, 60))
                    history['timestamps'].append(timestamp.isoformat())
                
                return history
            else:
                # Get metrics from the last N hours
                cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
                
                cursor = self.db.system_metrics.find({
                    "timestamp": {"$gte": datetime.fromtimestamp(cutoff_time)}
                }).sort("timestamp", 1)
                
                history = {
                    'cpu': [],
                    'memory': [],
                    'disk': [],
                    'timestamps': []
                }
                
                async for metric in cursor:
                    history['cpu'].append(metric.get('cpu_percent', 0))
                    history['memory'].append(metric.get('memory_percent', 0))
                    history['disk'].append(metric.get('disk_percent', 0))
                    history['timestamps'].append(metric.get('timestamp', ''))
                
                return history
        except Exception as e:
            logging.error(f"Error retrieving system history: {e}")
            return {'cpu': [], 'memory': [], 'disk': [], 'timestamps': []}
        
    async def monitor_system(self):
        """Background task to continuously monitor system"""
        while True:
            try:
                metrics = self.get_system_metrics()
                
                # Store in MongoDB
                await self.db.system_metrics.insert_one(metrics)
                
                # Broadcast to connected clients
                await self.broadcast_metrics({
                    'type': 'system_metrics',
                    'data': metrics
                })
                
                # Clean up old metrics (keep last 7 days)
                week_ago = datetime.utcnow().timestamp() - (7 * 24 * 3600)
                await self.db.system_metrics.delete_many({
                    "timestamp": {"$lt": datetime.fromtimestamp(week_ago)}
                })
                
            except Exception as e:
                logging.error(f"Error in system monitoring: {e}")
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
    async def get_performance_summary(self) -> Dict:
        """Get performance summary statistics"""
        try:
            if self.dev_mode or not self.db:
                # Generate mock performance data for development
                import random
                total_tasks = random.randint(50, 200)
                successful_tasks = int(total_tasks * random.uniform(0.75, 0.95))
                failed_tasks = total_tasks - successful_tasks
                
                return {
                    'total_tasks': total_tasks,
                    'success_rate': round((successful_tasks / total_tasks * 100), 2),
                    'error_rate': round((failed_tasks / total_tasks * 100), 2),
                    'average_duration': round(random.uniform(2, 15), 2),
                    'successful_tasks': successful_tasks,
                    'failed_tasks': failed_tasks
                }
            else:
                # Get recent task metrics
                recent_metrics = await self.get_task_metrics(100)
                
                if not recent_metrics:
                    return {
                        'total_tasks': 0,
                        'success_rate': 0,
                        'average_duration': 0,
                        'error_rate': 0
                    }
                
                total_tasks = len(recent_metrics)
                successful_tasks = len([m for m in recent_metrics if m.get('status') == 'completed'])
                failed_tasks = len([m for m in recent_metrics if m.get('status') == 'failed'])
                
                durations = [m.get('duration', 0) for m in recent_metrics if m.get('duration')]
                avg_duration = sum(durations) / len(durations) if durations else 0
                
                return {
                    'total_tasks': total_tasks,
                    'success_rate': (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    'error_rate': (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    'average_duration': avg_duration,
                    'successful_tasks': successful_tasks,
                    'failed_tasks': failed_tasks
                }
        except Exception as e:
            logging.error(f"Error getting performance summary: {e}")
            return {
                'total_tasks': 0,
                'success_rate': 0,
                'average_duration': 0,
                'error_rate': 0
            }

# Global monitoring service instance
monitoring_service = MonitoringService() 