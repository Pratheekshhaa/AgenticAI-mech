"""
UEBA Security Monitor - Monitors agent behavior for anomalies
"""

import asyncio
import json
import time
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import redis

class UEBA_Monitor:
    """User and Entity Behavior Analytics for monitoring agent behavior"""
    
    def __init__(self, rules_path: str = "config/ueba_rules.yaml"):
        self.monitor_id = "ueba_monitor"
        self.rules = self.load_rules(rules_path)
        self.agent_behaviors = defaultdict(lambda: defaultdict(deque))
        self.alerts = []
        self.anomaly_scores = defaultdict(float)
        
        # Redis for monitoring
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        
        # Behavior baselines (will be learned over time)
        self.baselines = {}
        self.learning_mode = True
        self.learning_start = datetime.now()
        
        print(f"✅ UEBA Monitor initialized: {self.monitor_id}")
    
    def load_rules(self, rules_path: str) -> Dict[str, Any]:
        """Load UEBA security rules"""
        try:
            with open(rules_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ UEBA rules file not found: {rules_path}, using defaults")
            return self.get_default_rules()
    
    def get_default_rules(self) -> Dict[str, Any]:
        """Get default UEBA rules"""
        return {
            'anomaly_detection': {
                'api_calls': {
                    'max_calls_per_minute': 100,
                    'max_calls_per_hour': 1000,
                    'alert_on_burst': True
                },
                'agents': {
                    'max_messages_per_minute': 50,
                    'max_failed_requests_per_hour': 10
                }
            },
            'alert_severity_levels': {
                'critical': {
                    'triggers': ['unauthorized_access', 'data_tampering'],
                    'actions': ['isolate_agent', 'alert_security']
                },
                'high': {
                    'triggers': ['api_rate_exceeded', 'unusual_pattern'],
                    'actions': ['throttle_agent', 'notify_admin']
                }
            }
        }
    
    async def monitor_agent_behavior(self, agent_id: str, event_type: str, event_data: Dict[str, Any]):
        """Monitor agent behavior for anomalies"""
        timestamp = datetime.now()
        
        # Record behavior
        self.record_behavior(agent_id, event_type, event_data, timestamp)
        
        # Check for anomalies
        anomalies = await self.detect_anomalies(agent_id, event_type, event_data, timestamp)
        
        # Update anomaly score
        if anomalies:
            self.update_anomaly_score(agent_id, anomalies)
            
            # Generate alerts for significant anomalies
            for anomaly in anomalies:
                if anomaly['severity'] in ['critical', 'high']:
                    await self.generate_alert(agent_id, anomaly)
        
        # Auto-isolate if score is too high
        if self.anomaly_scores[agent_id] > 0.8:
            await self.isolate_agent(agent_id)
        
        return {
            'agent_id': agent_id,
            'timestamp': timestamp.isoformat(),
            'anomalies_detected': len(anomalies),
            'current_score': self.anomaly_scores[agent_id]
        }
    
    def record_behavior(self, agent_id: str, event_type: str, event_data: Dict[str, Any], timestamp: datetime):
        """Record agent behavior for pattern analysis"""
        behavior_key = f"{agent_id}:{event_type}"
        
        # Add to behavior queue
        self.agent_behaviors[behavior_key]['timestamps'].append(timestamp)
        
        # Keep only last hour of data
        one_hour_ago = datetime.now() - timedelta(hours=1)
        while (self.agent_behaviors[behavior_key]['timestamps'] and 
               self.agent_behaviors[behavior_key]['timestamps'][0] < one_hour_ago):
            self.agent_behaviors[behavior_key]['timestamps'].popleft()
        
        # Update counts
        minute_key = timestamp.strftime('%Y-%m-%d %H:%M')
        if minute_key not in self.agent_behaviors[behavior_key]:
            self.agent_behaviors[behavior_key][minute_key] = 0
        self.agent_behaviors[behavior_key][minute_key] += 1
    
    async def detect_anomalies(self, agent_id: str, event_type: str, 
                              event_data: Dict[str, Any], timestamp: datetime) -> List[Dict[str, Any]]:
        """Detect anomalies in agent behavior"""
        anomalies = []
        
        # Rule 1: Check API call frequency
        if event_type == 'api_call':
            calls_last_minute = self.get_calls_in_last_minute(agent_id, 'api_call')
            max_calls = self.rules['anomaly_detection']['api_calls']['max_calls_per_minute']
            
            if calls_last_minute > max_calls:
                anomalies.append({
                    'type': 'API_CALL_FREQUENCY',
                    'severity': 'high',
                    'message': f'Agent {agent_id} made {calls_last_minute} API calls in last minute (max: {max_calls})',
                    'value': calls_last_minute,
                    'threshold': max_calls
                })
        
        # Rule 2: Check message frequency
        elif event_type == 'message_sent':
            messages_last_minute = self.get_calls_in_last_minute(agent_id, 'message_sent')
            max_messages = self.rules['anomaly_detection']['agents']['max_messages_per_minute']
            
            if messages_last_minute > max_messages:
                anomalies.append({
                    'type': 'MESSAGE_FREQUENCY',
                    'severity': 'medium',
                    'message': f'Agent {agent_id} sent {messages_last_minute} messages in last minute',
                    'value': messages_last_minute,
                    'threshold': max_messages
                })
        
        # Rule 3: Check for unusual time access
        hour = timestamp.hour
        if hour < 6 or hour > 22:  # Unusual hours
            anomalies.append({
                'type': 'UNUSUAL_TIME_ACCESS',
                'severity': 'low',
                'message': f'Agent {agent_id} active during unusual hours ({hour}:00)',
                'value': hour,
                'threshold': '06:00-22:00'
            })
        
        # Rule 4: Check for failed requests
        if event_type == 'request_failed':
            failures_last_hour = self.get_failures_last_hour(agent_id)
            max_failures = self.rules['anomaly_detection']['agents']['max_failed_requests_per_hour']
            
            if failures_last_hour > max_failures:
                anomalies.append({
                    'type': 'HIGH_FAILURE_RATE',
                    'severity': 'high',
                    'message': f'Agent {agent_id} has {failures_last_hour} failed requests in last hour',
                    'value': failures_last_hour,
                    'threshold': max_failures
                })
        
        # Rule 5: Check for data access anomalies
        if event_type == 'data_access' and event_data.get('sensitive', False):
            anomalies.append({
                'type': 'SENSITIVE_DATA_ACCESS',
                'severity': 'critical',
                'message': f'Agent {agent_id} accessed sensitive data: {event_data.get("data_type")}',
                'details': event_data
            })
        
        return anomalies
    
    def get_calls_in_last_minute(self, agent_id: str, event_type: str) -> int:
        """Get number of calls in the last minute"""
        behavior_key = f"{agent_id}:{event_type}"
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        
        if behavior_key not in self.agent_behaviors:
            return 0
        
        timestamps = self.agent_behaviors[behavior_key]['timestamps']
        count = sum(1 for ts in timestamps if ts > one_minute_ago)
        return count
    
    def get_failures_last_hour(self, agent_id: str) -> int:
        """Get number of failures in the last hour"""
        behavior_key = f"{agent_id}:request_failed"
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        if behavior_key not in self.agent_behaviors:
            return 0
        
        timestamps = self.agent_behaviors[behavior_key]['timestamps']
        count = sum(1 for ts in timestamps if ts > one_hour_ago)
        return count
    
    def update_anomaly_score(self, agent_id: str, anomalies: List[Dict[str, Any]]):
        """Update anomaly score for an agent"""
        current_score = self.anomaly_scores[agent_id]
        
        for anomaly in anomalies:
            severity = anomaly['severity']
            if severity == 'critical':
                current_score += 0.3
            elif severity == 'high':
                current_score += 0.2
            elif severity == 'medium':
                current_score += 0.1
            elif severity == 'low':
                current_score += 0.05
        
        # Apply decay over time (score reduces by 10% per hour)
        hours_since_update = 0  # Would be calculated in real implementation
        decay_factor = 0.9 ** hours_since_update
        current_score *= decay_factor
        
        # Clamp between 0 and 1
        self.anomaly_scores[agent_id] = max(0, min(1, current_score))
    
    async def generate_alert(self, agent_id: str, anomaly: Dict[str, Any]):
        """Generate security alert"""
        alert = {
            'alert_id': f"alert_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'anomaly_type': anomaly['type'],
            'severity': anomaly['severity'],
            'message': anomaly['message'],
            'details': anomaly,
            'status': 'new'
        }
        
        self.alerts.append(alert)
        
        # Publish alert
        await self.publish_alert(alert)
        
        # Take action based on severity
        await self.take_action(agent_id, anomaly['severity'], alert)
        
        print(f"🚨 UEBA Alert: {anomaly['severity'].upper()} - {anomaly['message']}")
    
    async def publish_alert(self, alert: Dict[str, Any]):
        """Publish alert to Redis channel"""
        channel = 'ueba:alerts'
        self.redis_client.publish(channel, json.dumps(alert))
    
    async def take_action(self, agent_id: str, severity: str, alert: Dict[str, Any]):
        """Take action based on alert severity"""
        if severity == 'critical':
            # Immediate isolation
            await self.isolate_agent(agent_id)
            
            # Notify security team
            await self.notify_security_team(alert)
            
            # Stop all workflows involving this agent
            await self.stop_agent_workflows(agent_id)
        
        elif severity == 'high':
            # Throttle agent
            await self.throttle_agent(agent_id)
            
            # Notify admin
            await self.notify_admin(alert)
        
        elif severity == 'medium':
            # Increase monitoring
            await self.increase_monitoring(agent_id)
            
            # Log warning
            print(f"⚠️ Warning for {agent_id}: {alert['message']}")
    
    async def isolate_agent(self, agent_id: str):
        """Isolate an agent from the system"""
        print(f"🛑 Isolating agent: {agent_id}")
        
        # Send isolation command
        isolation_msg = {
            'command': 'isolate',
            'agent_id': agent_id,
            'timestamp': datetime.now().isoformat(),
            'reason': 'UEBA security alert'
        }
        
        self.redis_client.publish(f'agent:{agent_id}:control', json.dumps(isolation_msg))
        
        # Log isolation
        isolation_log = {
            'agent_id': agent_id,
            'action': 'isolated',
            'timestamp': datetime.now().isoformat(),
            'ueba_score': self.anomaly_scores[agent_id]
        }
        self.redis_client.hset('ueba:isolations', agent_id, json.dumps(isolation_log))
    
    async def throttle_agent(self, agent_id: str):
        """Throttle agent's API calls"""
        print(f"🐌 Throttling agent: {agent_id}")
        
        throttle_msg = {
            'command': 'throttle',
            'agent_id': agent_id,
            'timestamp': datetime.now().isoformat(),
            'rate_limit': 10  # Calls per minute
        }
        
        self.redis_client.publish(f'agent:{agent_id}:control', json.dumps(throttle_msg))
    
    async def notify_security_team(self, alert: Dict[str, Any]):
        """Notify security team (simulated)"""
        print(f"📢 Notifying security team: {alert['message']}")
    
    async def notify_admin(self, alert: Dict[str, Any]):
        """Notify admin (simulated)"""
        print(f"📧 Notifying admin: {alert['message']}")
    
    async def stop_agent_workflows(self, agent_id: str):
        """Stop all workflows involving the agent"""
        print(f"⏹️ Stopping workflows for agent: {agent_id}")
    
    async def increase_monitoring(self, agent_id: str):
        """Increase monitoring level for agent"""
        print(f"👁️ Increasing monitoring for agent: {agent_id}")
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get UEBA status for an agent"""
        return {
            'agent_id': agent_id,
            'anomaly_score': self.anomaly_scores.get(agent_id, 0),
            'status': 'isolated' if self.anomaly_scores.get(agent_id, 0) > 0.8 else 'monitored',
            'last_alert': next((a for a in reversed(self.alerts) if a['agent_id'] == agent_id), None),
            'behavior_summary': self.get_behavior_summary(agent_id)
        }
    
    def get_behavior_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get behavior summary for an agent"""
        summary = {}
        
        for behavior_key in self.agent_behaviors:
            if behavior_key.startswith(f"{agent_id}:"):
                event_type = behavior_key.split(':', 1)[1]
                timestamps = list(self.agent_behaviors[behavior_key]['timestamps'])
                
                if timestamps:
                    summary[event_type] = {
                        'count_last_hour': len(timestamps),
                        'last_activity': max(timestamps).isoformat() if timestamps else None
                    }
        
        return summary
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        return {
            'total_agents_monitored': len(self.anomaly_scores),
            'active_alerts': len([a for a in self.alerts if a['status'] == 'new']),
            'anomaly_distribution': {
                'critical': len([s for s in self.anomaly_scores.values() if s > 0.8]),
                'high': len([s for s in self.anomaly_scores.values() if 0.6 < s <= 0.8]),
                'medium': len([s for s in self.anomaly_scores.values() if 0.4 < s <= 0.6]),
                'low': len([s for s in self.anomaly_scores.values() if 0.2 < s <= 0.4]),
                'normal': len([s for s in self.anomaly_scores.values() if s <= 0.2])
            },
            'recent_alerts': self.alerts[-10:] if self.alerts else [],
            'learning_mode': self.learning_mode,
            'learning_progress': self.calculate_learning_progress()
        }
    
    def calculate_learning_progress(self) -> float:
        """Calculate learning progress percentage"""
        if not self.learning_mode:
            return 100.0
        
        learning_days = self.rules.get('baseline_learning', {}).get('learning_period_days', 7)
        days_elapsed = (datetime.now() - self.learning_start).days
        progress = min(100.0, (days_elapsed / learning_days) * 100)
        
        return progress
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        print("👁️ Starting UEBA monitoring...")
        
        # Subscribe to all agent channels
        self.pubsub.psubscribe('agent:*')
        
        for message in self.pubsub.listen():
            if message['type'] == 'pmessage':
                channel = message['channel']
                data = json.loads(message['data'])
                
                # Extract agent ID from channel
                if channel.startswith('agent:'):
                    parts = channel.split(':')
                    if len(parts) >= 2:
                        agent_id = parts[1]
                        
                        # Monitor this activity
                        await self.monitor_agent_behavior(
                            agent_id=agent_id,
                            event_type='message_sent',
                            event_data={'channel': channel, 'data': data}
                        )

# Singleton instance
_ueba_monitor_instance = None

def get_ueba_monitor():
    """Get or create UEBA Monitor instance"""
    global _ueba_monitor_instance
    if _ueba_monitor_instance is None:
        _ueba_monitor_instance = UEBA_Monitor()
    return _ueba_monitor_instance

if __name__ == "__main__":
    # Test the UEBA Monitor
    async def test():
        monitor = UEBA_Monitor()
        
        # Simulate some agent behaviors
        test_agent = "test_agent_001"
        
        # Normal behavior
        for i in range(5):
            await monitor.monitor_agent_behavior(
                agent_id=test_agent,
                event_type='api_call',
                event_data={'endpoint': '/api/data', 'method': 'GET'}
            )
            await asyncio.sleep(0.1)
        
        # Anomalous behavior (many API calls quickly)
        print("\n🚨 Simulating anomalous behavior...")
        for i in range(150):  # Exceeds threshold of 100/min
            await monitor.monitor_agent_behavior(
                agent_id=test_agent,
                event_type='api_call',
                event_data={'endpoint': '/api/data', 'method': 'GET'}
            )
        
        # Check status
        status = monitor.get_agent_status(test_agent)
        print(f"\n📊 Agent Status: {status}")
        
        # Get dashboard data
        dashboard = monitor.get_dashboard_data()
        print(f"\n📈 Dashboard Data: {json.dumps(dashboard, indent=2)}")
    
    asyncio.run(test())