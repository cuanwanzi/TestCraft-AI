# scripts/monitor.py
import asyncio
from typing import Any, Dict
import psutil
import logging
from datetime import datetime
import json

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, log_file="./data/logs/monitor.log"):
        self.log_file = log_file
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def monitor_system(self, interval=60):
        """监控系统状态"""
        
        self.logger.info("开始系统监控")
        
        while True:
            try:
                # 收集系统指标
                metrics = await self.collect_metrics()
                
                # 记录指标
                self.logger.info(f"系统指标: {json.dumps(metrics, indent=2)}")
                
                # 检查告警条件
                await self.check_alerts(metrics)
                
                # 等待下一个周期
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"监控异常: {str(e)}")
                await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "usage_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "usage_percent": psutil.disk_usage('/').percent
            },
            "network": {
                "sent": psutil.net_io_counters().bytes_sent,
                "received": psutil.net_io_counters().bytes_recv
            },
            "process": {
                "count": len(psutil.pids())
            }
        }
        
        return metrics
    
    async def check_alerts(self, metrics: Dict[str, Any]):
        """检查告警条件"""
        
        alerts = []
        
        # CPU使用率告警
        if metrics["cpu"]["usage_percent"] > 90:
            alerts.append("CPU使用率超过90%")
        
        # 内存使用率告警
        if metrics["memory"]["usage_percent"] > 90:
            alerts.append("内存使用率超过90%")
        
        # 磁盘使用率告警
        if metrics["disk"]["usage_percent"] > 90:
            alerts.append("磁盘使用率超过90%")
        
        if alerts:
            self.logger.warning(f"系统告警: {', '.join(alerts)}")

# 启动监控
async def main():
    monitor = SystemMonitor()
    await monitor.monitor_system(interval=60)

if __name__ == "__main__":
    asyncio.run(main())