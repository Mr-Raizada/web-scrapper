from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from services.monitoring_service import monitoring_service
from services.analytics_service import analytics_service
from typing import List, Optional
import asyncio
import logging
import os

# Development mode check
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"

# Mock user class for development
class User:
    def __init__(self, id: str, username: str, email: str):
        self.id = id
        self.username = username
        self.email = email

# Mock authentication for development
async def get_current_user():
    if DEV_MODE:
        return User(id="dev-user-id", username="devuser", email="dev@example.com")
    else:
        # In production, import from main.py
        from main import get_current_user as auth_get_current_user
        return await auth_get_current_user()

router = APIRouter()

@router.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await monitoring_service.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Handle incoming messages if needed (e.g., filter preferences)
            logging.info(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        monitoring_service.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        monitoring_service.disconnect(websocket)

@router.get("/metrics/system")
async def get_system_metrics(current_user: User = Depends(get_current_user)):
    """Get current system metrics"""
    return monitoring_service.get_system_metrics()

@router.get("/metrics/system/history")
async def get_system_history(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get system metrics history"""
    return await monitoring_service.get_system_history(hours)

@router.get("/metrics/tasks")
async def get_task_metrics(
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get task metrics"""
    return await monitoring_service.get_task_metrics(limit)

@router.get("/metrics/performance")
async def get_performance_summary(current_user: User = Depends(get_current_user)):
    """Get performance summary"""
    return await monitoring_service.get_performance_summary()

@router.get("/analytics/system")
async def get_system_analytics(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get system analytics"""
    return await analytics_service.get_system_analytics(hours)

@router.get("/analytics/tasks")
async def get_task_analytics(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get task analytics"""
    return await analytics_service.get_task_analytics(days)

@router.get("/analytics/performance")
async def get_performance_analytics(current_user: User = Depends(get_current_user)):
    """Get performance analytics"""
    task_data = await monitoring_service.get_task_metrics(100)
    return await analytics_service.generate_performance_metrics(task_data)

@router.get("/analytics/visualization/{viz_type}")
async def get_visualization(
    viz_type: str,
    current_user: User = Depends(get_current_user)
):
    """Get visualization data"""
    task_data = await monitoring_service.get_task_metrics(100)
    return await analytics_service.create_visualization(task_data, viz_type)

@router.get("/analytics/task-statistics")
async def get_task_statistics(current_user: User = Depends(get_current_user)):
    """Get task statistics"""
    task_data = await monitoring_service.get_task_metrics(100)
    return await analytics_service.calculate_task_statistics(task_data)

@router.post("/metrics/log")
async def log_custom_metric(
    task_id: str,
    metric_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Log custom metric for a task"""
    await monitoring_service.log_task_metrics(task_id, metric_data)
    return {"message": "Metric logged successfully"}

@router.get("/health/detailed")
async def get_detailed_health(current_user: User = Depends(get_current_user)):
    """Get detailed system health information"""
    try:
        system_metrics = monitoring_service.get_system_metrics()
        performance_summary = await monitoring_service.get_performance_summary()
        
        # Determine overall health status
        health_status = "healthy"
        issues = []
        
        # Check CPU usage
        if system_metrics.get('cpu_percent', 0) > 80:
            health_status = "warning"
            issues.append("High CPU usage")
        
        # Check memory usage
        if system_metrics.get('memory_percent', 0) > 85:
            health_status = "warning"
            issues.append("High memory usage")
        
        # Check disk usage
        if system_metrics.get('disk_percent', 0) > 90:
            health_status = "critical"
            issues.append("High disk usage")
        
        # Check error rate
        if performance_summary.get('error_rate', 0) > 10:
            health_status = "warning"
            issues.append("High error rate")
        
        return {
            "status": health_status,
            "timestamp": system_metrics.get('timestamp'),
            "system_metrics": system_metrics,
            "performance_summary": performance_summary,
            "issues": issues,
            "active_connections": len(monitoring_service.active_connections)
        }
        
    except Exception as e:
        logging.error(f"Error getting detailed health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": None
        } 