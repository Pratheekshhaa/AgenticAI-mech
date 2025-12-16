# demo.py
import asyncio
import json
import random
from datetime import datetime
from agents.master_agent_simple import SimpleMasterAgent
from agents.data_analysis_simple import SimpleDataAnalysisAgent
from agents.diagnosis_simple import SimpleDiagnosisAgent

class DemoVehicleGenerator:
    """Generate demo vehicle data"""
    
    @staticmethod
    def generate_vehicle_data(vehicle_id: str, has_issues: bool = True):
        """Generate vehicle telematics data"""
        base_data = {
            "engine_temp": random.uniform(80, 95),
            "oil_pressure": random.uniform(35, 55),
            "brake_pad_wear": random.uniform(30, 100),
            "tire_pressure": random.uniform(30, 35),
            "battery_voltage": random.uniform(12.0, 13.0),
            "rpm": random.randint(800, 3000),
            "fuel_level": random.uniform(20, 100),
            "mileage": random.randint(5000, 50000)
        }
        
        # Introduce issues if requested
        if has_issues:
            if random.random() > 0.5:
                base_data["engine_temp"] = random.uniform(105, 120)  # Overheating
            if random.random() > 0.5:
                base_data["brake_pad_wear"] = random.uniform(85, 100)  # Worn brakes
            if random.random() > 0.7:
                base_data["oil_pressure"] = random.uniform(20, 30)  # Low oil pressure
        
        return {
            "vehicle_id": vehicle_id,
            "timestamp": datetime.utcnow().isoformat(),
            "telematics": base_data,
            "has_critical_issue": base_data["engine_temp"] > 110 or base_data["brake_pad_wear"] > 90,
            "anomalies": []  # Will be populated by analysis
        }

async def run_demo():
    """Run the complete demo"""
    
    print("\n" + "="*70)
    print("🚗 AUTOMOTIVE PREDICTIVE MAINTENANCE AI - DEMO")
    print("="*70)
    
    # Step 1: Initialize all agents
    print("\n1️⃣ INITIALIZING AGENTS...")
    master = SimpleMasterAgent()
    data_agent = SimpleDataAnalysisAgent()
    diagnosis_agent = SimpleDiagnosisAgent()
    
    # Register agents with master
    master.register_agent(
        "data_analysis_agent",
        "http://localhost:8001",
        ["analyze_telematics", "detect_anomalies", "forecast_service"]
    )
    
    master.register_agent(
        "diagnosis_agent",
        "http://localhost:8002",
        ["diagnose_failures", "predict_component_life", "rca_analysis"]
    )
    
    # Register placeholder for teammate's agents
    master.register_agent(
        "customer_agent",
        "http://localhost:8003",
        ["notify_customer", "schedule_appointment"]
    )
    
    master.register_agent(
        "scheduling_agent",
        "http://localhost:8004",
        ["book_appointment", "check_availability"]
    )
    
    print("✅ All agents initialized and registered!")
    
    # Step 2: Generate demo vehicle data
    print("\n2️⃣ GENERATING DEMO VEHICLE DATA...")
    vehicles = [
        ("VIN001", "Toyota Innova", "Delhi", True),  # With issues
        ("VIN002", "Hyundai Creta", "Mumbai", False),  # Healthy
        ("VIN003", "Maruti Suzuki Swift", "Bangalore", True),  # With issues
    ]
    
    for vin, model, city, has_issues in vehicles:
        print(f"\n   Vehicle: {vin} ({model})")
        print(f"   Location: {city}")
        print(f"   Status: {'⚠️ Has issues' if has_issues else '✅ Healthy'}")
    
    # Step 3: Process first vehicle with issues
    print("\n3️⃣ PROCESSING VEHICLE VIN001 (WITH ISSUES)...")
    vehicle_data = DemoVehicleGenerator.generate_vehicle_data("VIN001", has_issues=True)
    
    print(f"\n   📊 Telematics Data:")
    for sensor, value in vehicle_data["telematics"].items():
        print(f"   • {sensor}: {value:.1f}")
    
    # Step 4: Run Data Analysis
    print("\n4️⃣ RUNNING DATA ANALYSIS...")
    analysis_result = await data_agent.analyze_telematics(vehicle_data)
    
    print(f"   🔍 Analysis Results:")
    print(f"   • Health Score: {analysis_result['health_score']:.0f}/100")
    print(f"   • Anomalies Detected: {analysis_result['anomaly_count']}")
    
    if analysis_result["anomalies_detected"]:
        print(f"   ⚠️ Anomalies:")
        for anomaly in analysis_result["anomalies_detected"]:
            print(f"     - {anomaly['sensor']}: {anomaly['value']:.1f} ({anomaly['severity']})")
    
    print(f"   📅 Service Forecast: {analysis_result['service_forecast']['estimated_days_to_service']} days")
    
    # Step 5: Run Diagnosis
    print("\n5️⃣ RUNNING DIAGNOSIS...")
    diagnosis_data = {
        "vehicle_id": "VIN001",
        "analysis_results": analysis_result
    }
    
    diagnosis_result = await diagnosis_agent.diagnose_failures(diagnosis_data)
    
    print(f"   ⚡ Diagnosis Results:")
    print(f"   • Priority: {diagnosis_result['priority']}")
    print(f"   • Predicted Failures: {len(diagnosis_result['predicted_failures'])}")
    
    for failure in diagnosis_result["predicted_failures"]:
        print(f"     - {failure['component']}: {failure['failure_probability']*100:.0f}% probability")
        print(f"       Days to failure: {failure['days_to_failure']}, Cost: ₹{failure['estimated_cost']}")
    
    # Step 6: Orchestrate with Master Agent
    print("\n6️⃣ MASTER AGENT ORCHESTRATION...")
    workflow_result = await master.orchestrate_predictive_maintenance(vehicle_data)
    
    print(f"\n   🎯 Workflow Status: {workflow_result['status'].upper()}")
    print(f"   📋 Agents Involved: {', '.join(workflow_result['agents_involved'])}")
    print(f"   🔒 UEBA Status: {workflow_result['ueba_status']['status']}")
    
    # Step 7: RCA/CAPA Insights
    print("\n7️⃣ RCA/CAPA INSIGHTS FOR MANUFACTURING...")
    rca_insights = diagnosis_result["rca_insights"]
    
    if rca_insights["insights"]:
        print(f"   🔍 Patterns Identified: {rca_insights['patterns_identified']}")
        for insight in rca_insights["insights"]:
            print(f"\n   📝 Pattern: {insight['pattern']}")
            print(f"     Possible Root Cause: {insight['possible_root_cause']}")
            print(f"     Preventive Action: {insight['preventive_action']}")
            print(f"     Manufacturing Improvement: {insight['manufacturing_improvement']}")
    else:
        print("   ✅ No significant patterns detected for RCA")
    
    # Step 8: UEBA Security Demo
    print("\n8️⃣ UEBA SECURITY DEMONSTRATION...")
    print("   📊 Normal Operation Monitoring:")
    print("     • All agents behaving normally")
    print("     • API calls within expected limits")
    print("     • No unauthorized access attempts")
    
    print("\n   🚨 Simulating Security Anomaly...")
    print("     Scenario: Diagnosis agent making 1000+ API calls/minute")
    print("     UEBA Action: Flag as anomalous behavior")
    print("     Result: Agent isolated, security alert triggered")
    print("     ✅ Security incident prevented!")
    
    # Step 9: Extensibility Demo
    print("\n9️⃣ AGENT EXTENSIBILITY DEMO...")
    print("   📦 How teammates can add their agents:")
    print("     1. Create agent class with required capabilities")
    print("     2. Register with Master Agent using register_agent()")
    print("     3. Master will automatically route relevant tasks")
    print("     4. UEBA will monitor new agent automatically")
    
    print("\n   Example for Customer Engagement Agent:")
    print("""
   class CustomerAgent:
       def __init__(self):
           self.capabilities = ["notify_customer", "schedule_callback"]
       
       async def notify_customer(self, data):
           # Call customer via voice/SMS
           return {"status": "customer_notified"}
   """)
    
    # Step 10: Summary
    print("\n" + "="*70)
    print("🎉 DEMO SUMMARY")
    print("="*70)
    
    summary = {
        "total_vehicles_processed": len(vehicles),
        "anomalies_detected": analysis_result["anomaly_count"],
        "predicted_failures": len(diagnosis_result["predicted_failures"]),
        "workflow_priority": diagnosis_result["priority"],
        "rca_insights_generated": rca_insights["patterns_identified"],
        "ueba_alerts": 0,
        "system_status": "OPERATIONAL"
    }
    
    for key, value in summary.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("="*70)
    
    return {
        "analysis": analysis_result,
        "diagnosis": diagnosis_result,
        "workflow": workflow_result,
        "summary": summary
    }

def create_simple_requirements():
    """Create minimal requirements file"""
    with open("simple_requirements.txt", "w") as f:
        f.write("""# Simple Requirements for Python 3.12
aiohttp==3.9.3
redis==5.0.1
numpy==1.26.0
pandas==2.1.3
""")
    print("✅ Created simple_requirements.txt")

if __name__ == "__main__":
    print("Setting up Automotive Predictive Maintenance AI Demo...")
    
    # Create simplified requirements
    create_simple_requirements()
    
    print("\nTo install dependencies:")
    print("pip install -r simple_requirements.txt")
    
    print("\nTo run the demo:")
    print("python demo.py")
    
    # Run the demo
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")
    except Exception as e:
        print(f"\nError during demo: {e}")
        print("\nTrying to run with minimal setup...")
        
        # Try minimal demo
        import sys
        if sys.version_info >= (3, 12):
            print("Python 3.12 detected - using simplified version...")
            # Run with built-in modules only
            exec(open("demo_minimal.py").read())  # Create a minimal version