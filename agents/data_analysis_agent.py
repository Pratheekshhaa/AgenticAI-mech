"""
Data Analysis Agent - Analyzes vehicle telematics and detects anomalies
"""

import asyncio
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
import redis

class DataAnalysisAgent:
    """Worker agent for continuous vehicle data analysis"""
    
    def __init__(self, agent_id: str = "data_analysis_agent"):
        self.agent_id = agent_id
        self.capabilities = [
            "analyze_telematics",
            "detect_anomalies", 
            "forecast_service_demand",
            "extract_features"
        ]
        
        # Redis for communication
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        
        # Normal operating ranges for sensors
        self.normal_ranges = {
            "engine_temp": (70, 110),  # Celsius
            "oil_pressure": (30, 60),   # PSI
            "brake_pad_wear": (0, 80),  # Percentage
            "tire_pressure": (28, 36),  # PSI
            "battery_voltage": (11.8, 13.2),  # Volts
            "rpm": (800, 3500),  # RPM
            "fuel_level": (10, 100),  # Percentage
        }
        
        # Sliding window for anomaly detection
        self.data_windows = {}
        self.window_size = 100
        
        print(f"✅ Data Analysis Agent initialized: {self.agent_id}")
    
    async def analyze_telematics(self, telematics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis method for vehicle telematics"""
        vehicle_id = telematics_data.get("vehicle_id", "unknown")
        
        print(f"📊 Analyzing telematics for {vehicle_id}...")
        
        sensor_data = telematics_data.get("telematics_data", {})
        
        # Step 1: Check individual sensors
        anomalies = []
        for sensor, value in sensor_data.items():
            if sensor in self.normal_ranges:
                min_val, max_val = self.normal_ranges[sensor]
                if value < min_val or value > max_val:
                    severity = self.calculate_severity(sensor, value, min_val, max_val)
                    anomalies.append({
                        "sensor": sensor,
                        "value": value,
                        "normal_range": f"{min_val}-{max_val}",
                        "severity": severity,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Step 2: Update sliding window
        self.update_data_window(vehicle_id, sensor_data)
        
        # Step 3: Detect pattern-based anomalies
        pattern_anomalies = await self.detect_pattern_anomalies(vehicle_id, sensor_data)
        anomalies.extend(pattern_anomalies)
        
        # Step 4: Calculate health score
        health_score = self.calculate_health_score(anomalies, sensor_data)
        
        # Step 5: Forecast service demand
        service_forecast = self.forecast_service_demand(vehicle_id, sensor_data)
        
        # Step 6: Extract features
        features = self.extract_features(sensor_data)
        
        return {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "service_forecast": service_forecast,
            "features": features,
            "analysis_complete": True
        }
    
    def calculate_severity(self, sensor: str, value: float, min_val: float, max_val: float) -> str:
        """Calculate severity of anomaly"""
        normal_mid = (min_val + max_val) / 2
        deviation = abs(value - normal_mid) / (max_val - min_val)
        
        if deviation > 0.5:
            return "CRITICAL"
        elif deviation > 0.3:
            return "HIGH"
        elif deviation > 0.2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def update_data_window(self, vehicle_id: str, sensor_data: Dict[str, Any]):
        """Update sliding window of sensor data"""
        if vehicle_id not in self.data_windows:
            self.data_windows[vehicle_id] = []
        
        self.data_windows[vehicle_id].append(sensor_data)
        
        # Keep only last N readings
        if len(self.data_windows[vehicle_id]) > self.window_size:
            self.data_windows[vehicle_id] = self.data_windows[vehicle_id][-self.window_size:]
    
    async def detect_pattern_anomalies(self, vehicle_id: str, sensor_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies based on data patterns"""
        anomalies = []
        
        if vehicle_id in self.data_windows:
            window_data = self.data_windows[vehicle_id]
            if len(window_data) >= 10:
                # Convert to DataFrame for analysis
                df = pd.DataFrame(window_data)
                
                # Check for sudden changes
                for column in df.columns:
                    if column in self.normal_ranges and len(df[column]) >= 2:
                        # Calculate rate of change
                        values = df[column].values
                        roc = abs(values[-1] - values[-2]) / (values[-2] if values[-2] != 0 else 1)
                        
                        if roc > 0.3:  # Sudden 30% change
                            anomalies.append({
                                "sensor": column,
                                "value": values[-1],
                                "pattern": "sudden_change",
                                "severity": "HIGH",
                                "rate_of_change": roc,
                                "timestamp": datetime.now().isoformat()
                            })
                
                # Check for correlation anomalies
                if 'engine_temp' in df.columns and 'rpm' in df.columns:
                    correlation = df['engine_temp'].corr(df['rpm'])
                    if correlation < -0.7:  # Unusual negative correlation
                        anomalies.append({
                            "pattern": "correlation_anomaly",
                            "sensors": ["engine_temp", "rpm"],
                            "correlation": correlation,
                            "severity": "MEDIUM",
                            "timestamp": datetime.now().isoformat()
                        })
        
        return anomalies
    
    def calculate_health_score(self, anomalies: List[Dict[str, Any]], sensor_data: Dict[str, Any]) -> float:
        """Calculate overall vehicle health score (0-100)"""
        base_score = 100.0
        
        # Deduct for anomalies
        for anomaly in anomalies:
            severity = anomaly.get("severity", "LOW")
            if severity == "CRITICAL":
                base_score -= 25
            elif severity == "HIGH":
                base_score -= 15
            elif severity == "MEDIUM":
                base_score -= 10
            elif severity == "LOW":
                base_score -= 5
        
        # Additional deductions for specific sensors
        if "brake_pad_wear" in sensor_data:
            wear = sensor_data["brake_pad_wear"]
            if wear > 80:
                base_score -= 20
            elif wear > 70:
                base_score -= 15
            elif wear > 60:
                base_score -= 10
        
        if "engine_temp" in sensor_data:
            temp = sensor_data["engine_temp"]
            if temp > 105:
                base_score -= 20
            elif temp > 100:
                base_score -= 10
        
        return max(0, min(100, base_score))
    
    def forecast_service_demand(self, vehicle_id: str, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast when service will be needed"""
        days_to_service = 30  # Default
        
        # Adjust based on sensor readings
        urgency = "LOW"
        components = []
        
        if "brake_pad_wear" in sensor_data:
            wear = sensor_data["brake_pad_wear"]
            if wear > 85:
                days_to_service = 7
                urgency = "CRITICAL"
                components.append("Brake Pads")
            elif wear > 70:
                days_to_service = 14
                urgency = "HIGH"
                components.append("Brake Pads")
            elif wear > 60:
                days_to_service = 21
                urgency = "MEDIUM"
                components.append("Brake Pads")
        
        if "engine_temp" in sensor_data:
            temp = sensor_data["engine_temp"]
            if temp > 105:
                days_to_service = min(days_to_service, 3)
                urgency = "CRITICAL"
                components.append("Cooling System")
            elif temp > 100:
                days_to_service = min(days_to_service, 7)
                urgency = "HIGH"
                components.append("Cooling System")
        
        return {
            "estimated_days_to_service": days_to_service,
            "urgency": urgency,
            "components_needing_service": components,
            "confidence": 0.85,
            "recommended_actions": [
                f"Inspect {', '.join(components)}" if components else "No immediate service needed",
                "Check all fluid levels",
                "Review maintenance history"
            ]
        }
    
    def extract_features(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract important features from sensor data"""
        features = {}
        
        # Basic statistics
        for sensor, value in sensor_data.items():
            if isinstance(value, (int, float)):
                features[f"{sensor}_value"] = value
        
        # Derived features
        if "engine_temp" in sensor_data and "rpm" in sensor_data:
            features["temp_rpm_ratio"] = sensor_data["engine_temp"] / max(sensor_data["rpm"], 1)
        
        if "brake_pad_wear" in sensor_data and "tire_pressure" in sensor_data:
            features["wear_pressure_index"] = sensor_data["brake_pad_wear"] * sensor_data["tire_pressure"] / 100
        
        return features
    
    async def start_listening(self):
        """Start listening for analysis requests"""
        print(f"👂 {self.agent_id} listening for messages...")
        
        # Subscribe to agent's channel
        self.pubsub.subscribe(f"agent:{self.agent_id}")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    
                    if data.get('action') == 'analyze_telematics':
                        payload = data.get('payload', {})
                        result = await self.analyze_telematics(payload)
                        
                        # Send response back
                        response = {
                            "message_id": data.get('message_id'),
                            "sender": self.agent_id,
                            "recipient": data.get('sender'),
                            "action": "analysis_complete",
                            "payload": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Publish response
                        response_channel = f"response:{data.get('message_id')}"
                        self.redis_client.publish(response_channel, json.dumps(response))
                        
                except Exception as e:
                    print(f"❌ Error in {self.agent_id}: {e}")

if __name__ == "__main__":
    # Test the agent
    agent = DataAnalysisAgent()
    
    # Test data
    test_data = {
        "vehicle_id": "VIN001",
        "telematics_data": {
            "engine_temp": 115,
            "oil_pressure": 25,
            "brake_pad_wear": 85,
            "tire_pressure": 32,
            "battery_voltage": 12.8,
            "rpm": 2800,
            "fuel_level": 65
        }
    }
    
    async def test():
        result = await agent.analyze_telematics(test_data)
        print("\n📋 Analysis Results:")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())