import pandas as pd
import numpy as np
from typing import Dict, List
from collections import defaultdict
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

class AnalyticsService:
    def __init__(self):
        self.cache = {}
        
        # Development mode check
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # MongoDB connection (only in production)
        self.client = None
        self.db = None
        
        if not self.dev_mode:
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017") 
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
            self.db = self.client.scraper_db
        
    async def calculate_task_statistics(self, tasks: List[Dict]) -> Dict:
        if not tasks:
            return {
                'total_tasks': 0,
                'success_rate': 0,
                'average_duration': 0,
                'tasks_by_status': {},
                'hourly_distribution': {}
            }
        
        df = pd.DataFrame(tasks)
        
        # Convert timestamp strings to datetime
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        stats = {
            'total_tasks': len(df),
            'success_rate': (df['status'] == 'completed').mean() * 100 if 'status' in df.columns else 0,
            'average_duration': df['duration'].mean() if 'duration' in df.columns else 0,
            'tasks_by_status': df['status'].value_counts().to_dict() if 'status' in df.columns else {},
            'hourly_distribution': {}
        }
        
        # Calculate hourly distribution if timestamp data is available
        if 'created_at' in df.columns and not df['created_at'].empty:
            hourly_dist = df.groupby(df['created_at'].dt.hour).size()
            stats['hourly_distribution'] = hourly_dist.to_dict()
        
        return stats
        
    async def generate_performance_metrics(self, data: List[Dict]) -> Dict:
        if not data:
            return {
                'response_times': {'mean': 0, 'median': 0, 'p95': 0},
                'error_rates': 0,
                'success_rates': 0
            }
        
        df = pd.DataFrame(data)
        
        metrics = {
            'response_times': {
                'mean': df['response_time'].mean() if 'response_time' in df.columns else 0,
                'median': df['response_time'].median() if 'response_time' in df.columns else 0,
                'p95': df['response_time'].quantile(0.95) if 'response_time' in df.columns else 0
            },
            'error_rates': (df['status'] == 'error').mean() * 100 if 'status' in df.columns else 0,
            'success_rates': (df['status'] == 'success').mean() * 100 if 'status' in df.columns else 0
        }
        
        return metrics
        
    async def create_visualization(self, data: List[Dict], viz_type: str) -> Dict:
        if not data and not self.dev_mode:
            return {'error': 'No data available for visualization'}
        
        # Generate mock data for development mode if no data available
        if self.dev_mode or not data:
            import random
            if viz_type == 'task_status_pie':
                # Generate mock task status data
                mock_data = [
                    {'status': 'completed'} for _ in range(random.randint(50, 80))
                ] + [
                    {'status': 'failed'} for _ in range(random.randint(5, 15))
                ] + [
                    {'status': 'pending'} for _ in range(random.randint(3, 10))
                ]
                df = pd.DataFrame(mock_data)
            else:
                # For other visualization types, return a simple mock response
                return {
                    'data': [],
                    'layout': {
                        'title': f'Mock {viz_type} visualization',
                        'showlegend': True
                    },
                    'config': {}
                }
        else:
            df = pd.DataFrame(data)
        
        try:
            if viz_type == 'time_series':
                if 'timestamp' in df.columns and 'value' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    fig = px.line(
                        df, 
                        x='timestamp', 
                        y='value',
                        title='Time Series Analysis'
                    )
                else:
                    return {'error': 'Missing timestamp or value columns for time series'}
                    
            elif viz_type == 'distribution':
                if 'value' in df.columns:
                    fig = px.histogram(
                        df,
                        x='value',
                        title='Distribution Analysis'
                    )
                else:
                    return {'error': 'Missing value column for distribution'}
                    
            elif viz_type == 'heatmap':
                if all(col in df.columns for col in ['x_axis', 'y_axis', 'value']):
                    pivot_table = pd.pivot_table(
                        df,
                        values='value',
                        index='x_axis',
                        columns='y_axis',
                        fill_value=0
                    )
                    fig = px.imshow(pivot_table)
                else:
                    return {'error': 'Missing required columns for heatmap'}
                    
            elif viz_type == 'task_status_pie':
                if 'status' in df.columns:
                    status_counts = df['status'].value_counts()
                    fig = px.pie(
                        values=status_counts.values,
                        names=status_counts.index,
                        title='Task Status Distribution'
                    )
                else:
                    return {'error': 'Missing status column for pie chart'}
                    
            elif viz_type == 'hourly_activity':
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at'])
                    df['hour'] = df['created_at'].dt.hour
                    hourly_counts = df['hour'].value_counts().sort_index()
                    fig = px.bar(
                        x=hourly_counts.index,
                        y=hourly_counts.values,
                        title='Hourly Task Activity',
                        labels={'x': 'Hour of Day', 'y': 'Number of Tasks'}
                    )
                else:
                    return {'error': 'Missing created_at column for hourly activity'}
            else:
                return {'error': f'Unknown visualization type: {viz_type}'}
                
            return json.loads(fig.to_json())
            
        except Exception as e:
            return {'error': f'Error creating visualization: {str(e)}'}
    
    async def get_system_analytics(self, hours: int = 24) -> Dict:
        """Get comprehensive system analytics"""
        try:
            if self.dev_mode or not self.db:
                # Generate mock analytics for development
                import random
                return {
                    'cpu_avg': round(random.uniform(20, 60), 2),
                    'memory_avg': round(random.uniform(30, 70), 2),
                    'disk_avg': round(random.uniform(15, 50), 2),
                    'peak_cpu': round(random.uniform(70, 95), 2),
                    'peak_memory': round(random.uniform(80, 95), 2),
                    'trend': random.choice(['increasing', 'decreasing', 'stable']),
                    'data_points': hours
                }
            else:
                # Get system metrics from the last N hours
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                cursor = self.db.system_metrics.find({
                    "timestamp": {"$gte": cutoff_time}
                }).sort("timestamp", 1)
                
                metrics = []
                async for metric in cursor:
                    metrics.append(metric)
                
                if not metrics:
                    return {
                        'cpu_avg': 0,
                        'memory_avg': 0,
                        'disk_avg': 0,
                        'peak_cpu': 0,
                        'peak_memory': 0,
                        'trend': 'stable'
                    }
                
                df = pd.DataFrame(metrics)
                
                # Calculate averages
                cpu_avg = df['cpu_percent'].mean()
                memory_avg = df['memory_percent'].mean()
                disk_avg = df['disk_percent'].mean()
                
                # Calculate peaks
                peak_cpu = df['cpu_percent'].max()
                peak_memory = df['memory_percent'].max()
                
                # Calculate trend (simple linear regression)
                if len(df) > 1:
                    cpu_trend = np.polyfit(range(len(df)), df['cpu_percent'], 1)[0]
                    if cpu_trend > 0.1:
                        trend = 'increasing'
                    elif cpu_trend < -0.1:
                        trend = 'decreasing'
                    else:
                        trend = 'stable'
                else:
                    trend = 'stable'
                
                return {
                    'cpu_avg': round(cpu_avg, 2),
                    'memory_avg': round(memory_avg, 2),
                    'disk_avg': round(disk_avg, 2),
                    'peak_cpu': round(peak_cpu, 2),
                    'peak_memory': round(peak_memory, 2),
                    'trend': trend,
                    'data_points': len(metrics)
                }
            
        except Exception as e:
            return {
                'error': f'Error getting system analytics: {str(e)}',
                'cpu_avg': 0,
                'memory_avg': 0,
                'disk_avg': 0,
                'peak_cpu': 0,
                'peak_memory': 0,
                'trend': 'unknown'
            }
    
    async def get_task_analytics(self, days: int = 7) -> Dict:
        """Get task analytics for the last N days"""
        try:
            if self.dev_mode or not self.db:
                # Generate mock task analytics for development
                import random
                from datetime import datetime, timedelta
                
                # Mock daily distribution
                daily_distribution = {}
                for i in range(days):
                    date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
                    daily_distribution[date] = random.randint(5, 25)
                
                return {
                    'total_tasks': random.randint(50, 200),
                    'success_rate': round(random.uniform(75, 95), 2),
                    'avg_duration': round(random.uniform(2, 15), 2),
                    'daily_distribution': daily_distribution,
                    'status_breakdown': {
                        'completed': random.randint(80, 150),
                        'failed': random.randint(5, 20),
                        'pending': random.randint(3, 15)
                    }
                }
            else:
                cutoff_time = datetime.utcnow() - timedelta(days=days)
                
                cursor = self.db.tasks.find({
                    "created_at": {"$gte": cutoff_time}
                }).sort("created_at", 1)
                
                tasks = []
                async for task in cursor:
                    tasks.append(task)
                
                if not tasks:
                    return {
                        'total_tasks': 0,
                        'success_rate': 0,
                        'avg_duration': 0,
                        'daily_distribution': {},
                        'status_breakdown': {}
                    }
                
                df = pd.DataFrame(tasks)
                df['created_at'] = pd.to_datetime(df['created_at'])
                
                # Calculate basic stats
                total_tasks = len(df)
                success_rate = (df['status'] == 'completed').mean() * 100
                
                # Calculate average duration if available
                if 'completed_at' in df.columns and 'created_at' in df.columns:
                    df['duration'] = (pd.to_datetime(df['completed_at']) - df['created_at']).dt.total_seconds()
                    avg_duration = df['duration'].mean()
                else:
                    avg_duration = 0
                
                # Daily distribution
                daily_dist = df.groupby(df['created_at'].dt.date).size()
                daily_distribution = {str(date): int(count) for date, count in daily_dist.items()}
                
                # Status breakdown
                status_breakdown = df['status'].value_counts().to_dict()
                
                return {
                    'total_tasks': total_tasks,
                    'success_rate': round(success_rate, 2),
                    'avg_duration': round(avg_duration, 2) if avg_duration > 0 else 0,
                    'daily_distribution': daily_distribution,
                    'status_breakdown': status_breakdown
                }
            
        except Exception as e:
            return {
                'error': f'Error getting task analytics: {str(e)}',
                'total_tasks': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'daily_distribution': {},
                'status_breakdown': {}
            }

# Global analytics service instance
analytics_service = AnalyticsService() 