"""
Master Agent - Main orchestrator for the predictive maintenance system
Coordinates all worker agents and manages workflows
"""

import asyncio
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import redis
import aiohttp

@dataclass
class AgentMessage:
    """Message format for inter-agent communication"""
    message_id: str
    timestamp: str
    sender: str
    recipient: str
    action: str
    payload: Dict[str, Any]
    priority: int = 1

class MasterAgent:
    """Main orchestrator that coordinates all worker agents"""
    
    def __init__(self, config_path: str = "config/agent_config.yaml"):
        self.agent_id = "master_agent"
        self.config = self.load_config(config_path)
        self.registered_agents = {}
        self.workflow_logs = []
        self.ueba_alerts = []
        
        # Initialize Redis for message passing
        self.redis_client = redis.Redis(
            host=self.config['redis']['host'],
            port=self.config['redis']['port'],
            decode_responses=True
        )
        
        # Load UEBA rules
        self.ueba_rules = self.load_ueba_rules()
        
        print(f"✅ Master Agent initialized: {self.agent_id}")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ Config file not found: {config_path}, using defaults")
            return {
                'redis': {'host': 'localhost', 'port': 6379},
                'agents': {
                    'data_analysis': {'endpoint': 'http://localhost:8001'},
                    'diagnosis': {'endpoint': 'http://localhost:8002'},
                    'customer_engagement': {'endpoint': 'http://localhost:8003'},
                    'scheduling': {'endpoint': 'http://localhost:8004'},
                    'rca': {'endpoint': 'http://localhost:8005'}
                },
                'monitoring_interval': 5
            }
    
    def load_ueba_rules(self) -> Dict[str, Any]:
        """Load UEBA security rules"""
        try:
            with open("config/ueba_rules.yaml", 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print("⚠️ UEBA rules file not found, using defaults")
            return {
                'anomaly_thresholds': {
                    'api_calls_per_minute': 100,
                    'workflow_changes_per_hour': 10,
                    'unusual_time_access': True
                },
                'alert_channels': ['log', 'dashboard'],
                'auto_isolation': True
            }
    
    def register_agent(self, agent_id: str, agent_type: str, endpoint: str, capabilities: List[str]):
        """Register a worker agent with the master"""
        self.registered_agents[agent_id] = {
            'type': agent_type,
            'endpoint': endpoint,
            'capabilities': capabilities,
            'status': 'active',
            'registered_at': datetime.now().isoformat(),
            'last_heartbeat': datetime.now().isoformat()
        }
        print(f"✅ Registered agent: {agent_id} ({agent_type})")
    
    async def send_message(self, recipient: str, action: str, payload: Dict[str, Any]):
        """Send message to a specific agent"""
        message = AgentMessage(
            message_id=f"msg_{int(datetime.now().timestamp())}",
            timestamp=datetime.now().isoformat(),
            sender=self.agent_id,
            recipient=recipient,
            action=action,
            payload=payload
        )
        
        # Publish to Redis channel
        channel = f"agent:{recipient}"
        self.redis_client.publish(channel, json.dumps(asdict(message)))
        
        # UEBA: Monitor message sending
        await self.monitor_ueba('message_sent', {
            'sender': self.agent_id,
            'recipient': recipient,
            'action': action
        })
        
        return message
    
    async def orchestrate_predictive_maintenance(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration workflow for predictive maintenance"""
        workflow_id = f"wf_{int(datetime.now().timestamp())}"
        print(f"\n🚀 Starting predictive maintenance workflow: {workflow_id}")
        
        steps = []
        
        try:
            # Step 1: Data Analysis
            print("📊 Step 1: Analyzing vehicle telematics...")
            analysis_msg = await self.send_message(
                recipient="data_analysis_agent",
                action="analyze_telematics",
                payload={
                    "workflow_id": workflow_id,
                    "vehicle_id": vehicle_data["vehicle_id"],
                    "telematics_data": vehicle_data["telematics"],
                    "timestamp": datetime.now().isoformat()
                }
            )
            steps.append({"step": 1, "action": "data_analysis", "status": "completed"})
            
            # Simulate receiving analysis results
            await asyncio.sleep(1)  # Simulate processing time
            
            # Step 2: Diagnosis
            print("🔍 Step 2: Running failure diagnosis...")
            diagnosis_msg = await self.send_message(
                recipient="diagnosis_agent",
                action="diagnose_failures",
                payload={
                    "workflow_id": workflow_id,
                    "vehicle_id": vehicle_data["vehicle_id"],
                    "analysis_data": {"anomalies": vehicle_data.get("anomalies", [])},
                    "timestamp": datetime.now().isoformat()
                }
            )
            steps.append({"step": 2, "action": "failure_diagnosis", "status": "completed"})
            
            # Check for critical issues
            if vehicle_data.get("has_critical_issue", False):
                print("⚠️ Step 3: Critical issue detected - Engaging customer...")
                
                # Step 3: Customer Engagement
                customer_msg = await self.send_message(
                    recipient="customer_engagement_agent",
                    action="notify_customer",
                    payload={
                        "workflow_id": workflow_id,
                        "vehicle_id": vehicle_data["vehicle_id"],
                        "issue_type": "critical",
                        "priority": "HIGH",
                        "message": "Critical component failure predicted"
                    }
                )
                steps.append({"step": 3, "action": "customer_engagement", "status": "completed"})
                
                # Step 4: Scheduling
                print("📅 Step 4: Scheduling service appointment...")
                schedule_msg = await self.send_message(
                    recipient="scheduling_agent",
                    action="book_appointment",
                    payload={
                        "workflow_id": workflow_id,
                        "vehicle_id": vehicle_data["vehicle_id"],
                        "customer_id": vehicle_data.get("customer_id", "unknown"),
                        "priority": "urgent",
                        "estimated_downtime": 2
                    }
                )
                steps.append({"step": 4, "action": "scheduling", "status": "completed"})
            
            # Step 5: RCA Analysis
            print("🔬 Step 5: Performing RCA analysis...")
            rca_msg = await self.send_message(
                recipient="rca_agent",
                action="analyze_root_cause",
                payload={
                    "workflow_id": workflow_id,
                    "vehicle_id": vehicle_data["vehicle_id"],
                    "issue_patterns": vehicle_data.get("issue_patterns", []),
                    "manufacturing_data": vehicle_data.get("manufacturing_data", {})
                }
            )
            steps.append({"step": 5, "action": "rca_analysis", "status": "completed"})
            
            # Step 6: UEBA Monitoring
            print("🛡️ Step 6: UEBA security monitoring...")
            ueba_status = await self.monitor_ueba('workflow_completion', {
                'workflow_id': workflow_id,
                'steps_completed': len(steps),
                'agents_involved': list(self.registered_agents.keys())
            })
            
            workflow_status = {
                "workflow_id": workflow_id,
                "vehicle_id": vehicle_data["vehicle_id"],
                "status": "completed",
                "steps": steps,
                "ueba_status": ueba_status,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 5  # Simulated
            }
            
            self.workflow_logs.append(workflow_status)
            print(f"✅ Workflow {workflow_id} completed successfully!")
            
            return workflow_status
            
        except Exception as e:
            error_status = {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ Workflow {workflow_id} failed: {e}")
            return error_status
    
    async def monitor_ueba(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """UEBA security monitoring"""
        # Check for anomalies
        anomalies = []
        
        # Rule 1: Check API call frequency
        if event_type == 'message_sent':
            agent = event_data.get('recipient', '')
            if agent and agent in self.registered_agents:
                # Simulate anomaly detection
                import random
                if random.random() < 0.1:  # 10% chance of simulated anomaly
                    anomaly = {
                        "type": "API_CALL_FREQUENCY",
                        "severity": "MEDIUM",
                        "message": f"Unusual API call pattern detected for {agent}",
                        "timestamp": datetime.now().isoformat()
                    }
                    anomalies.append(anomaly)
                    self.ueba_alerts.append(anomaly)
        
        # Rule 2: Check workflow anomalies
        if event_type == 'workflow_completion':
            steps = event_data.get('steps_completed', 0)
            if steps > 10:  # Too many steps might indicate issues
                anomaly = {
                    "type": "WORKFLOW_COMPLEXITY",
                    "severity": "LOW",
                    "message": f"Workflow has {steps} steps, which is unusually high",
                    "timestamp": datetime.now().isoformat()
                }
                anomalies.append(anomaly)
                self.ueba_alerts.append(anomaly)
        
        return {
            "status": "monitored",
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "timestamp": datetime.now().isoformat()
        }
    
    async def start_monitoring(self):
        """Start continuous vehicle monitoring"""
        print("📡 Starting continuous vehicle monitoring...")
        
        # In a real system, this would connect to telematics streams
        # For demo, we'll simulate periodic monitoring
        while True:
            # Simulate monitoring interval
            await asyncio.sleep(self.config.get('monitoring_interval', 5))
            
            # Check system health
            await self.check_system_health()
    
    async def check_system_health(self):
        """Check health of all registered agents"""
        print("🏥 Checking system health...")
        
        for agent_id, agent_info in self.registered_agents.items():
            # Update last heartbeat
            agent_info['last_heartbeat'] = datetime.now().isoformat()
            
            # Simulate health check
            print(f"  • {agent_id}: ✅ Active")
        
        return True
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        return {
            "master_agent": {
                "id": self.agent_id,
                "status": "active",
                "registered_agents": len(self.registered_agents),
                "active_workflows": len([w for w in self.workflow_logs if w['status'] == 'completed']),
                "ueba_alerts": len(self.ueba_alerts)
            },
            "agents": self.registered_agents,
            "recent_workflows": self.workflow_logs[-5:] if self.workflow_logs else [],
            "ueba_alerts": self.ueba_alerts[-10:] if self.ueba_alerts else []
        }

# Singleton instance
_master_agent_instance = None

def get_master_agent():
    """Get or create Master Agent instance"""
    global _master_agent_instance
    if _master_agent_instance is None:
        _master_agent_instance = MasterAgent()
    return _master_agent_instance

if __name__ == "__main__":
    # Test the Master Agent
    async def test():
        master = MasterAgent()
        
        # Register some agents
        master.register_agent(
            agent_id="data_analysis_agent",
            agent_type="data_analysis",
            endpoint="http://localhost:8001",
            capabilities=["analyze_telematics", "detect_anomalies"]
        )
        
        # Simulate a vehicle
        vehicle_data = {
            "vehicle_id": "VIN001",
            "telematics": {
                "engine_temp": 115,
                "brake_pad_wear": 85,
                "oil_pressure": 25
            },
            "has_critical_issue": True,
            "customer_id": "CUST001"
        }
        
        # Run workflow
        result = await master.orchestrate_predictive_maintenance(vehicle_data)
        print(f"\n📋 Workflow Result: {result}")
    
    asyncio.run(test())