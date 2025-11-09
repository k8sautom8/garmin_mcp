"""
Training and Diet Recommendations functions for Garmin Connect MCP Server
"""
import datetime
import json
from typing import Any, Dict, List, Optional, Union

# The garmin_client will be set by the main file
garmin_client = None


def _to_json_str(data):
    """Convert data to JSON string if it's not already a string"""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        return str(data)


def configure(client):
    """Configure the module with the Garmin client instance"""
    global garmin_client
    garmin_client = client


def register_tools(app):
    """Register all recommendation tools with the MCP server app"""
    
    @app.tool()
    async def get_optimized_health_data(
        start_date: str,
        end_date: str,
        include_activities: bool = True,
        include_sleep: bool = True,
        include_stress: bool = True,
        include_body_battery: bool = True,
        include_training_readiness: bool = True,
        include_hrv: bool = False,
        activity_type: str = ""
    ) -> str:
        """Optimized tool to fetch multiple health and training data points in one call.
        
        This tool efficiently retrieves comprehensive health and training data for a date range,
        reducing the need for multiple individual tool calls.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            include_activities: Whether to include activity data (default: True)
            include_sleep: Whether to include sleep data (default: True)
            include_stress: Whether to include stress data (default: True)
            include_body_battery: Whether to include body battery data (default: True)
            include_training_readiness: Whether to include training readiness data (default: True)
            include_hrv: Whether to include HRV data (default: False, as it's more resource-intensive)
            activity_type: Optional activity type filter (e.g., "running", "cycling")
        """
        try:
            result = {
                "date_range": {"start": start_date, "end": end_date},
                "data": {}
            }
            
            # Get activities if requested
            if include_activities:
                try:
                    activities = garmin_client.get_activities_by_date(
                        start_date, end_date, activity_type
                    )
                    result["data"]["activities"] = activities if activities else []
                except Exception as e:
                    result["data"]["activities"] = f"Error: {str(e)}"
            
            # Get daily data for each date in range
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            current = start
            
            daily_data = []
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                day_data = {"date": date_str}
                
                # Get sleep data
                if include_sleep:
                    try:
                        sleep = garmin_client.get_sleep_data(date_str)
                        day_data["sleep"] = sleep if sleep else None
                    except Exception:
                        day_data["sleep"] = None
                
                # Get stress data
                if include_stress:
                    try:
                        stress = garmin_client.get_stress_data(date_str)
                        day_data["stress"] = stress if stress else None
                    except Exception:
                        day_data["stress"] = None
                
                # Get body battery
                if include_body_battery:
                    try:
                        # Body battery requires date range, so get single day
                        battery = garmin_client.get_body_battery(date_str, date_str)
                        day_data["body_battery"] = battery if battery else None
                    except Exception:
                        day_data["body_battery"] = None
                
                # Get training readiness
                if include_training_readiness:
                    try:
                        readiness = garmin_client.get_training_readiness(date_str)
                        day_data["training_readiness"] = readiness if readiness else None
                    except Exception:
                        day_data["training_readiness"] = None
                
                # Get HRV (optional, more resource-intensive)
                if include_hrv:
                    try:
                        hrv = garmin_client.get_hrv_data(date_str)
                        day_data["hrv"] = hrv if hrv else None
                    except Exception:
                        day_data["hrv"] = None
                
                # Get steps and basic stats
                try:
                    stats = garmin_client.get_stats(date_str)
                    day_data["stats"] = stats if stats else None
                except Exception:
                    day_data["stats"] = None
                
                daily_data.append(day_data)
                current += datetime.timedelta(days=1)
            
            result["data"]["daily_summary"] = daily_data
            
            # Get overall training metrics
            try:
                # Get max metrics for the end date (most recent)
                max_metrics = garmin_client.get_max_metrics(end_date)
                result["data"]["max_metrics"] = max_metrics if max_metrics else None
            except Exception:
                result["data"]["max_metrics"] = None
            
            return _to_json_str(result)
        except Exception as e:
            return f"Error retrieving optimized health data: {str(e)}"
    
    @app.tool()
    async def get_training_and_diet_recommendations(
        context: str,
        health_data_json: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        focus_area: Optional[str] = None
    ) -> str:
        """Generate training and diet recommendations based on recent health and training data.
        
        This tool analyzes health data (either provided directly or fetched automatically) and
        provides personalized training and diet recommendations based on the user's context.
        
        Args:
            context: User's request or context (e.g., "I want to improve my running performance",
                    "I'm feeling tired and need recovery advice", "Prepare for a marathon")
            health_data_json: Optional pre-fetched health data JSON (from get_optimized_health_data).
                            If not provided, will fetch data for the last 7 days.
            start_date: Start date for data fetch if health_data_json not provided (default: 7 days ago)
            end_date: End date for data fetch if health_data_json not provided (default: today)
            focus_area: Optional focus area ("performance", "recovery", "weight_loss", "endurance", "strength")
        """
        try:
            # If health data not provided, fetch it using the same logic as get_optimized_health_data
            if not health_data_json:
                if not end_date:
                    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
                if not start_date:
                    start = datetime.datetime.now() - datetime.timedelta(days=7)
                    start_date = start.strftime("%Y-%m-%d")
                
                # Fetch data directly using garmin_client (same logic as get_optimized_health_data)
                health_data = {
                    "date_range": {"start": start_date, "end": end_date},
                    "data": {}
                }
                
                # Get activities
                try:
                    activities = garmin_client.get_activities_by_date(start_date, end_date, "")
                    health_data["data"]["activities"] = activities if activities else []
                except Exception:
                    health_data["data"]["activities"] = []
                
                # Get daily data
                start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                current = start
                
                daily_data = []
                while current <= end:
                    date_str = current.strftime("%Y-%m-%d")
                    day_data = {"date": date_str}
                    
                    try:
                        sleep = garmin_client.get_sleep_data(date_str)
                        day_data["sleep"] = sleep if sleep else None
                    except Exception:
                        day_data["sleep"] = None
                    
                    try:
                        stress = garmin_client.get_stress_data(date_str)
                        day_data["stress"] = stress if stress else None
                    except Exception:
                        day_data["stress"] = None
                    
                    try:
                        battery = garmin_client.get_body_battery(date_str, date_str)
                        day_data["body_battery"] = battery if battery else None
                    except Exception:
                        day_data["body_battery"] = None
                    
                    try:
                        readiness = garmin_client.get_training_readiness(date_str)
                        day_data["training_readiness"] = readiness if readiness else None
                    except Exception:
                        day_data["training_readiness"] = None
                    
                    try:
                        stats = garmin_client.get_stats(date_str)
                        day_data["stats"] = stats if stats else None
                    except Exception:
                        day_data["stats"] = None
                    
                    daily_data.append(day_data)
                    current += datetime.timedelta(days=1)
                
                health_data["data"]["daily_summary"] = daily_data
                
                try:
                    max_metrics = garmin_client.get_max_metrics(end_date)
                    health_data["data"]["max_metrics"] = max_metrics if max_metrics else None
                except Exception:
                    health_data["data"]["max_metrics"] = None
            else:
                health_data = json.loads(health_data_json) if isinstance(health_data_json, str) else health_data_json
            
            # Analyze the data
            recommendations = {
                "context": context,
                "focus_area": focus_area or "general",
                "analysis": {},
                "training_recommendations": [],
                "diet_recommendations": [],
                "recovery_recommendations": []
            }
            
            # Extract key metrics from health data
            daily_summary = health_data.get("data", {}).get("daily_summary", [])
            activities = health_data.get("data", {}).get("activities", [])
            
            # Analyze sleep patterns
            sleep_scores = []
            avg_sleep_duration = 0
            for day in daily_summary:
                sleep = day.get("sleep")
                if sleep and isinstance(sleep, dict):
                    # Extract sleep duration if available
                    if "sleepTimeSeconds" in sleep:
                        sleep_scores.append(sleep.get("sleepTimeSeconds", 0) / 3600)  # Convert to hours
                    elif "sleepQuality" in sleep:
                        sleep_scores.append(sleep.get("sleepQuality", {}).get("overallSleepValue", 0))
            
            if sleep_scores:
                avg_sleep_duration = sum(sleep_scores) / len(sleep_scores)
                recommendations["analysis"]["average_sleep_hours"] = round(avg_sleep_duration, 1)
            
            # Analyze body battery trends
            body_battery_values = []
            for day in daily_summary:
                battery = day.get("body_battery")
                if battery and isinstance(battery, dict):
                    # Extract body battery values
                    if isinstance(battery, list) and len(battery) > 0:
                        for entry in battery:
                            if isinstance(entry, dict) and "bodyBatteryValue" in entry:
                                body_battery_values.append(entry.get("bodyBatteryValue", 0))
            
            if body_battery_values:
                avg_body_battery = sum(body_battery_values) / len(body_battery_values)
                recommendations["analysis"]["average_body_battery"] = round(avg_body_battery, 1)
            
            # Analyze training readiness
            readiness_scores = []
            for day in daily_summary:
                readiness = day.get("training_readiness")
                if readiness and isinstance(readiness, dict):
                    if "trainingReadiness" in readiness:
                        readiness_scores.append(readiness.get("trainingReadiness", {}).get("value", 0))
            
            if readiness_scores:
                avg_readiness = sum(readiness_scores) / len(readiness_scores)
                recommendations["analysis"]["average_training_readiness"] = round(avg_readiness, 1)
            
            # Analyze activity volume
            activity_count = len(activities) if isinstance(activities, list) else 0
            recommendations["analysis"]["activity_count"] = activity_count
            
            # Generate recommendations based on analysis
            # Training recommendations
            if avg_sleep_duration < 7:
                recommendations["training_recommendations"].append(
                    "Consider reducing training intensity - your average sleep is below 7 hours, "
                    "which may indicate insufficient recovery."
                )
            elif avg_sleep_duration >= 8:
                recommendations["training_recommendations"].append(
                    "Good sleep duration! You're well-rested for training. Consider maintaining or "
                    "slightly increasing training volume."
                )
            
            if body_battery_values and avg_body_battery < 50:
                recommendations["training_recommendations"].append(
                    "Your body battery is consistently low. Focus on recovery activities like "
                    "light walking, yoga, or complete rest days."
                )
            elif body_battery_values and avg_body_battery > 70:
                recommendations["training_recommendations"].append(
                    "Excellent body battery levels! This is a good time for high-intensity training sessions."
                )
            
            if readiness_scores and avg_readiness < 50:
                recommendations["training_recommendations"].append(
                    "Training readiness is low. Prioritize recovery: easy pace workouts, stretching, "
                    "and adequate rest between sessions."
                )
            elif readiness_scores and avg_readiness > 70:
                recommendations["training_recommendations"].append(
                    "High training readiness detected! Ideal time for challenging workouts, "
                    "intervals, or long-distance training."
                )
            
            if activity_count == 0:
                recommendations["training_recommendations"].append(
                    "No activities recorded in this period. Start with light to moderate intensity "
                    "activities and gradually build up."
                )
            elif activity_count > 5:
                recommendations["training_recommendations"].append(
                    f"You've been very active ({activity_count} activities). Ensure you're including "
                    "adequate rest days to prevent overtraining."
                )
            
            # Diet recommendations
            if avg_sleep_duration < 7:
                recommendations["diet_recommendations"].append(
                    "Prioritize foods rich in magnesium and tryptophan (nuts, seeds, turkey, bananas) "
                    "to support better sleep quality."
                )
            
            if body_battery_values and avg_body_battery < 50:
                recommendations["diet_recommendations"].append(
                    "Focus on nutrient-dense foods: complex carbohydrates for sustained energy, "
                    "lean proteins for recovery, and plenty of fruits/vegetables for micronutrients."
                )
            
            if activity_count > 0:
                recommendations["diet_recommendations"].append(
                    "Ensure adequate protein intake (1.6-2.2g per kg body weight) to support "
                    "muscle recovery and adaptation from your training."
                )
                recommendations["diet_recommendations"].append(
                    "Time your carbohydrate intake around workouts - consume 30-60g carbs 1-2 hours "
                    "before exercise and replenish within 30 minutes post-workout."
                )
            
            # Recovery recommendations
            if avg_sleep_duration < 7 or (body_battery_values and avg_body_battery < 50):
                recommendations["recovery_recommendations"].append(
                    "Prioritize sleep hygiene: maintain consistent sleep schedule, reduce screen time "
                    "before bed, and create a dark, cool sleeping environment."
                )
            
            if readiness_scores and avg_readiness < 50:
                recommendations["recovery_recommendations"].append(
                    "Consider active recovery: light stretching, foam rolling, or gentle yoga. "
                    "Stay hydrated and ensure adequate rest between training sessions."
                )
            
            # Context-specific recommendations
            context_lower = context.lower()
            if "marathon" in context_lower or "endurance" in context_lower:
                recommendations["training_recommendations"].append(
                    "For endurance training: gradually increase weekly mileage by 10%, include "
                    "one long run per week, and maintain easy pace for 80% of training."
                )
                recommendations["diet_recommendations"].append(
                    "Endurance focus: Increase carbohydrate intake to 6-10g per kg body weight. "
                    "Focus on whole grains, fruits, and starchy vegetables."
                )
            
            if "performance" in context_lower or "improve" in context_lower:
                recommendations["training_recommendations"].append(
                    "Include structured interval training: 1-2 high-intensity sessions per week "
                    "with adequate recovery days between."
                )
            
            if "tired" in context_lower or "fatigue" in context_lower or "recovery" in context_lower:
                recommendations["training_recommendations"].append(
                    "Reduce training intensity and volume. Focus on low-intensity activities "
                    "or complete rest until energy levels improve."
                )
                recommendations["diet_recommendations"].append(
                    "Support recovery with anti-inflammatory foods: fatty fish, berries, leafy greens, "
                    "and adequate hydration (35ml per kg body weight)."
                )
            
            if focus_area == "weight_loss":
                recommendations["diet_recommendations"].append(
                    "Create a moderate calorie deficit (300-500 kcal/day). Prioritize protein "
                    "to preserve muscle mass during weight loss."
                )
                recommendations["training_recommendations"].append(
                    "Combine strength training with cardiovascular exercise. Maintain training "
                    "intensity to preserve muscle mass."
                )
            
            return _to_json_str(recommendations)
        except Exception as e:
            return f"Error generating recommendations: {str(e)}"

    return app

