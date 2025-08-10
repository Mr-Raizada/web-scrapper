from sqlalchemy import text, Index, create_index
from typing import List, Dict, Any
import motor.motor_asyncio
import asyncio
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    def __init__(self):
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.db = self.client.scraper_db
        
    async def create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Tasks collection indexes
            await self.db.tasks.create_index([("user_id", 1)])
            await self.db.tasks.create_index([("status", 1)])
            await self.db.tasks.create_index([("created_at", -1)])
            await self.db.tasks.create_index([("user_id", 1), ("status", 1)])
            await self.db.tasks.create_index([("user_id", 1), ("created_at", -1)])
            
            # Scraping results indexes
            await self.db.scraping_results.create_index([("task_id", 1)])
            await self.db.scraping_results.create_index([("created_at", -1)])
            await self.db.scraping_results.create_index([("url", 1)])
            
            # System metrics indexes
            await self.db.system_metrics.create_index([("timestamp", -1)])
            await self.db.system_metrics.create_index([("timestamp", 1)], expireAfterSeconds=7*24*3600)  # TTL for 7 days
            
            # Task metrics indexes
            await self.db.task_metrics.create_index([("task_id", 1)])
            await self.db.task_metrics.create_index([("timestamp", -1)])
            await self.db.task_metrics.create_index([("timestamp", 1)], expireAfterSeconds=30*24*3600)  # TTL for 30 days
            
            # Users indexes
            await self.db.users.create_index([("username", 1)], unique=True)
            await self.db.users.create_index([("email", 1)], unique=True)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    async def analyze_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyze slow queries using MongoDB profiler"""
        try:
            # Enable profiler if not already enabled
            await self.db.set_profiling_level(1, 100)  # Log queries slower than 100ms
            
            # Get slow queries from system.profile collection
            cursor = self.db.system.profile.find({
                "millis": {"$gt": 100}
            }).sort("millis", -1).limit(limit)
            
            slow_queries = []
            async for query in cursor:
                slow_queries.append({
                    "operation": query.get("op"),
                    "collection": query.get("ns"),
                    "duration_ms": query.get("millis"),
                    "timestamp": query.get("ts"),
                    "query": query.get("query"),
                    "planSummary": query.get("planSummary")
                })
            
            return slow_queries
            
        except Exception as e:
            logger.error(f"Error analyzing slow queries: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics for performance analysis"""
        try:
            collections = ["tasks", "scraping_results", "system_metrics", "task_metrics", "users"]
            stats = {}
            
            for collection_name in collections:
                collection = self.db[collection_name]
                stats[collection_name] = await collection.stats()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    async def optimize_collections(self):
        """Perform collection optimization operations"""
        try:
            # Compact collections to reclaim space
            collections = ["tasks", "scraping_results", "system_metrics", "task_metrics"]
            
            for collection_name in collections:
                try:
                    await self.db.command({"compact": collection_name})
                    logger.info(f"Compacted collection: {collection_name}")
                except Exception as e:
                    logger.warning(f"Could not compact {collection_name}: {e}")
            
            # Update statistics
            await self.db.command({"analyze": "tasks"})
            await self.db.command({"analyze": "scraping_results"})
            
            logger.info("Collection optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing collections: {e}")
            raise
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data to maintain performance"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean up old system metrics (keep last 7 days)
            system_metrics_cutoff = datetime.utcnow() - timedelta(days=7)
            result = await self.db.system_metrics.delete_many({
                "timestamp": {"$lt": system_metrics_cutoff}
            })
            logger.info(f"Deleted {result.deleted_count} old system metrics")
            
            # Clean up old task metrics (keep last 30 days)
            task_metrics_cutoff = datetime.utcnow() - timedelta(days=30)
            result = await self.db.task_metrics.delete_many({
                "timestamp": {"$lt": task_metrics_cutoff}
            })
            logger.info(f"Deleted {result.deleted_count} old task metrics")
            
            # Clean up failed tasks older than specified days
            result = await self.db.tasks.delete_many({
                "status": "failed",
                "created_at": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} old failed tasks")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            raise
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics"""
        try:
            # Get database stats
            db_stats = await self.db.command("dbStats")
            
            # Get collection stats
            collection_stats = await self.get_collection_stats()
            
            # Calculate performance metrics
            total_documents = sum(
                stats.get("count", 0) for stats in collection_stats.values()
            )
            
            total_size = sum(
                stats.get("size", 0) for stats in collection_stats.values()
            )
            
            avg_doc_size = total_size / total_documents if total_documents > 0 else 0
            
            return {
                "total_documents": total_documents,
                "total_size_bytes": total_size,
                "average_document_size": avg_doc_size,
                "database_size": db_stats.get("dataSize", 0),
                "index_size": db_stats.get("indexSize", 0),
                "storage_size": db_stats.get("storageSize", 0),
                "collections": len(collection_stats),
                "indexes": db_stats.get("indexes", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def monitor_query_performance(self, duration_minutes: int = 5):
        """Monitor query performance for a specified duration"""
        try:
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            logger.info(f"Starting query performance monitoring for {duration_minutes} minutes")
            
            while datetime.utcnow() < end_time:
                # Get current slow queries
                slow_queries = await self.analyze_slow_queries(5)
                
                if slow_queries:
                    logger.warning(f"Found {len(slow_queries)} slow queries:")
                    for query in slow_queries:
                        logger.warning(f"  - {query['operation']} on {query['collection']}: {query['duration_ms']}ms")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
            
            logger.info("Query performance monitoring completed")
            
        except Exception as e:
            logger.error(f"Error monitoring query performance: {e}")
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        try:
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "performance_metrics": await self.get_performance_metrics(),
                "slow_queries": await self.analyze_slow_queries(10),
                "collection_stats": await self.get_collection_stats(),
                "recommendations": []
            }
            
            # Generate recommendations based on metrics
            metrics = report["performance_metrics"]
            
            if metrics.get("total_size_bytes", 0) > 1_000_000_000:  # 1GB
                report["recommendations"].append("Consider implementing data archiving for large collections")
            
            if len(report["slow_queries"]) > 5:
                report["recommendations"].append("Multiple slow queries detected. Review and optimize query patterns")
            
            if metrics.get("index_size", 0) > metrics.get("database_size", 0) * 0.5:
                report["recommendations"].append("Index size is large relative to data size. Consider index optimization")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": str(e)}

# Global database optimizer instance
db_optimizer = DatabaseOptimizer() 