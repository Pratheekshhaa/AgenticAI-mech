"""
Diagnosis Agent - Predicts component failures and assigns priority
"""

import asyncio
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import redis

class DiagnosisAgent:
    """Worker agent for predictive failure diagnosis"""
    
    def __init__(self, agent_id: str = "diagnosis_agent"):
        self.agent_id = agent_id
        self.capabilities = [
            "diagnose_failures",
            "predict_component_life",
            "assign_priority",
            "recommend_actions",
            "calculate_risk_score"
        ]
        
        # Redis for communication
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        
        # Component database
        self.component_db = self.load_component_database()
        
        # Failure patterns
        self.failure_patterns = self.load_failure_patterns()
        
        # Historical diagnosis records
        self.diagnosis_history = {}
        
        print(f"✅ Diagnosis Agent initialized: {self.agent_id}")
    
    def load_component_database(self) -> Dict[str, Any]:
        """Load component information database"""
        return {
            "brake_system": {
                "components": ["brake_pads", "brake_rotors", "brake_calipers", "brake_fluid"],
                "criticality": "CRITICAL",
                "avg_repair_cost": 15000,
                "downtime_days": 1,
                "common_failures": ["excessive_wear", "overheating", "fluid_leak"],
                "warning_signs": ["squeaking_noise", "vibration", "longer_stopping_distance"]
            },
            "engine_cooling": {
                "components": ["radiator", "water_pump", "thermostat", "coolant"],
                "criticality": "HIGH",
                "avg_repair_cost": 20000,
                "downtime_days": 2,
                "common_failures": ["overheating", "coolant_leak", "pump_failure"],
                "warning_signs": ["high_engine_temp", "coolant_leaks", "reduced_performance"]
            },
            "electrical_system": {
                "components": ["battery", "alternator", "starter", "wiring"],
                "criticality": "MEDIUM",
                "avg_repair_cost": 8000,
                "downtime_days": 1,
                "common_failures": ["battery_drain", "charging_failure", "electrical_short"],
                "warning_signs": ["battery_warning", "starting_issues", "electrical_faults"]
            },
            "suspension_system": {
                "components": ["shock_absorbers", "struts", "springs", "bushings"],
                "criticality": "MEDIUM",
                "avg_repair_cost": 12000,
                "downtime_days": 1,
                "common_failures": ["wear", "leaks", "noise"],
                "warning_signs": ["uneven_wear", "noise_over_bumps", "poor_handling"]
            }
        }
    
    def load_failure_patterns(self) -> List[Dict[str, Any]]:
        """Load historical failure patterns"""
        patterns = [
            {
                "pattern_id": "FP001",
                "symptoms": ["high_engine_temp", "low_oil_pressure"],
                "predicted_failure": "engine_overheating",
                "probability": 0.85,
                "time_to_failure_days": 7,
                "severity": "CRITICAL"
            },
            {
                "pattern_id": "FP002",
                "symptoms": ["high_brake_wear", "low_tire_pressure"],
                "predicted_failure": "brake_system_failure",
                "probability": 0.75,
                "time_to_failure_days": 14,
                "severity": "HIGH"
            },
            {
                "pattern_id": "FP003",
                "symptoms": ["low_battery_voltage", "electrical_issues"],
                "predicted_failure": "electrical_failure",
                "probability": 0.65,
                "time_to_failure_days": 30,
                "severity": "MEDIUM"
            }
        ]
        return patterns
    
    async def diagnose_failures(self, diagnosis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main diagnosis method"""
        vehicle_id = diagnosis_data.get("vehicle_id", "unknown")
        analysis_data = diagnosis_data.get("analysis_data", {})
        
        print(f"🔍 Diagnosing failures for {vehicle_id}...")
        
        # Get anomalies from analysis
        anomalies = analysis_data.get("anomalies", [])
        
        # Step 1: Map anomalies to components
        component_issues = self.map_anomalies_to_components(anomalies)
        
        # Step 2: Predict failures
        failure_predictions = self.predict_failures(component_issues)
        
        # Step 3: Calculate risk scores
        risk_assessment = self.calculate_risk_scores(failure_predictions)
        
        # Step 4: Assign priority
        priority_assignment = self.assign_priority(failure_predictions, risk_assessment)
        
        # Step 5: Generate recommendations
        recommendations = self.generate_recommendations(failure_predictions)
        
        # Step 6: Estimate time to failure
        ttf_estimates = self.estimate_time_to_failure(failure_predictions)
        
        # Store in history
        diagnosis_record = {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.now().isoformat(),
            "component_issues": component_issues,
            "failure_predictions": failure_predictions,
            "risk_assessment": risk_assessment,
            "priority": priority_assignment
        }
        
        if vehicle_id not in self.diagnosis_history:
            self.diagnosis_history[vehicle_id] = []
        self.diagnosis_history[vehicle_id].append(diagnosis_record)
        
        return {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.now().isoformat(),
            "diagnosis_id": f"diag_{int(datetime.now().timestamp())}",
            "component_issues": component_issues,
            "predicted_failures": failure_predictions,
            "risk_assessment": risk_assessment,
            "priority": priority_assignment,
            "recommendations": recommendations,
            "time_to_failure_estimates": ttf_estimates,
            "confidence_score": self.calculate_confidence(failure_predictions)
        }
    
    def map_anomalies_to_components(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map sensor anomalies to vehicle components"""
        component_issues = []
        
        sensor_to_component = {
            "brake_pad_wear": "brake_system",
            "engine_temp": "engine_cooling",
            "oil_pressure": "engine_cooling",
            "battery_voltage": "electrical_system",
            "tire_pressure": "suspension_system"
        }
        
        for anomaly in anomalies:
            sensor = anomaly.get("sensor", "")
            if sensor in sensor_to_component:
                component = sensor_to_component[sensor]
                if component in self.component_db:
                    component_info = self.component_db[component]
                    
                    component_issues.append({
                        "component": component,
                        "sensor": sensor,
                        "anomaly_value": anomaly.get("value"),
                        "severity": anomaly.get("severity", "LOW"),
                        "component_info": component_info
                    })
        
        return component_issues
    
    def predict_failures(self, component_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict component failures based on issues"""
        predictions = []
        
        for issue in component_issues:
            component = issue["component"]
            severity = issue["severity"]
            
            if component in self.component_db:
                comp_info = self.component_db[component]
                
                # Calculate failure probability based on severity
                if severity == "CRITICAL":
                    probability = random.uniform(0.8, 0.95)
                    ttf_days = random.randint(1, 7)
                elif severity == "HIGH":
                    probability = random.uniform(0.6, 0.8)
                    ttf_days = random.randint(7, 14)
                elif severity == "MEDIUM":
                    probability = random.uniform(0.4, 0.6)
                    ttf_days = random.randint(14, 30)
                else:
                    probability = random.uniform(0.2, 0.4)
                    ttf_days = random.randint(30, 90)
                
                predictions.append({
                    "component": component,
                    "failure_probability": round(probability, 2),
                    "time_to_failure_days": ttf_days,
                    "criticality": comp_info["criticality"],
                    "estimated_repair_cost": comp_info["avg_repair_cost"],
                    "estimated_downtime_days": comp_info["downtime_days"],
                    "common_symptoms": comp_info["warning_signs"],
                    "recommended_inspection": f"Inspect {', '.join(comp_info['components'][:2])}"
                })
        
        return predictions
    
    def calculate_risk_scores(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk scores for predicted failures"""
        if not predictions:
            return {"overall_risk": 0, "components": {}}
        
        component_risks = {}
        overall_risk = 0
        
        for prediction in predictions:
            component = prediction["component"]
            probability = prediction["failure_probability"]
            criticality = prediction["criticality"]
            
            # Weight based on criticality
            criticality_weights = {
                "CRITICAL": 1.0,
                "HIGH": 0.7,
                "MEDIUM": 0.4,
                "LOW": 0.2
            }
            
            weight = criticality_weights.get(criticality, 0.5)
            risk_score = probability * 100 * weight
            
            component_risks[component] = {
                "risk_score": round(risk_score, 2),
                "probability": probability,
                "criticality": criticality
            }
            
            overall_risk += risk_score
        
        # Normalize overall risk
        overall_risk = min(100, overall_risk / len(predictions))
        
        return {
            "overall_risk": round(overall_risk, 2),
            "components": component_risks
        }
    
    def assign_priority(self, predictions: List[Dict[str, Any]], risk_assessment: Dict[str, Any]) -> str:
        """Assign overall priority level"""
        overall_risk = risk_assessment.get("overall_risk", 0)
        
        # Check for critical failures
        critical_failures = [p for p in predictions 
                           if p["criticality"] == "CRITICAL" and p["failure_probability"] > 0.7]
        
        if critical_failures:
            return "CRITICAL"
        elif overall_risk > 70:
            return "HIGH"
        elif overall_risk > 50:
            return "MEDIUM"
        elif overall_risk > 30:
            return "LOW"
        else:
            return "NORMAL"
    
    def generate_recommendations(self, predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate repair and maintenance recommendations"""
        recommendations = []
        
        for prediction in predictions:
            if prediction["failure_probability"] > 0.6:
                urgency = "IMMEDIATE" if prediction["failure_probability"] > 0.8 else "SOON"
                
                recommendations.append({
                    "component": prediction["component"],
                    "action": f"Schedule service for {prediction['component'].replace('_', ' ')}",
                    "urgency": urgency,
                    "estimated_cost": prediction["estimated_repair_cost"],
                    "downtime_days": prediction["estimated_downtime_days"],
                    "recommended_timeline": f"Within {prediction['time_to_failure_days']} days",
                    "risk_if_ignored": "Vehicle breakdown or safety hazard"
                })
        
        # Add general recommendations
        if not recommendations:
            recommendations.append({
                "action": "Routine maintenance check",
                "urgency": "NORMAL",
                "estimated_cost": 2000,
                "downtime_days": 0.5,
                "recommended_timeline": "Next 30 days",
                "risk_if_ignored": "Minor issues may develop"
            })
        
        return recommendations
    
    def estimate_time_to_failure(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate time to failure for critical components"""
        estimates = {}
        
        for prediction in predictions:
            if prediction["failure_probability"] > 0.5:
                component = prediction["component"]
                ttf_days = prediction["time_to_failure_days"]
                
                estimates[component] = {
                    "days_to_failure": ttf_days,
                    "confidence": min(0.9, prediction["failure_probability"]),
                    "critical_window": f"Within {max(7, ttf_days // 2)} days",
                    "monitoring_required": "HIGH" if ttf_days < 14 else "MEDIUM"
                }
        
        return estimates
    
    def calculate_confidence(self, predictions: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the diagnosis"""
        if not predictions:
            return 0.9  # High confidence when no issues
        
        # Average probability as confidence
        avg_probability = sum(p["failure_probability"] for p in predictions) / len(predictions)
        
        # Adjust based on number of predictions
        if len(predictions) > 3:
            confidence = avg_probability * 0.9  # Slightly reduce for many predictions
        else:
            confidence = avg_probability
        
        return round(confidence, 2)
    
    async def start_listening(self):
        """Start listening for diagnosis requests"""
        print(f"👂 {self.agent_id} listening for messages...")
        
        # Subscribe to agent's channel
        self.pubsub.subscribe(f"agent:{self.agent_id}")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    
                    if data.get('action') == 'diagnose_failures':
                        payload = data.get('payload', {})
                        result = await self.diagnose_failures(payload)
                        
                        # Send response back
                        response = {
                            "message_id": data.get('message_id'),
                            "sender": self.agent_id,
                            "recipient": data.get('sender'),
                            "action": "diagnosis_complete",
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
    agent = DiagnosisAgent()
    
    # Test data
    test_data = {
        "vehicle_id": "VIN001",
        "analysis_data": {
            "anomalies": [
                {
                    "sensor": "brake_pad_wear",
                    "value": 85,
                    "severity": "CRITICAL",
                    "normal_range": "0-80"
                },
                {
                    "sensor": "engine_temp",
                    "value": 115,
                    "severity": "HIGH",
                    "normal_range": "70-110"
                }
            ]
        }
    }
    
    async def test():
        result = await agent.diagnose_failures(test_data)
        print("\n📋 Diagnosis Results:")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())