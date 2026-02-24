"""
Impact Aggregator Service

Aggregates impact data for users across different time periods.
Provides weekly summaries, comparisons, and historical data.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from ..schemas.impact_schemas import (
    PeriodSummary,
    WeeklySummaryResponse,
    WeeklyProgress,
    ImpactEventCreate
)


class ImpactAggregator:
    """
    Service for aggregating and querying impact data.
    
    Handles weekly summaries, period comparisons, and user statistics.
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize the aggregator.
        
        Args:
            supabase_client: Supabase client instance (optional, for DI)
        """
        self._supabase = supabase_client
    
    @property
    def supabase(self):
        """Lazy load supabase client."""
        if self._supabase is None:
            from ..db.session import supabase
            self._supabase = supabase
        return self._supabase
    
    def get_week_start(self, target_date: Optional[date] = None) -> date:
        """Get the Monday of the week containing target_date."""
        if target_date is None:
            target_date = date.today()
        # weekday() returns 0 for Monday, 6 for Sunday
        days_since_monday = target_date.weekday()
        return target_date - timedelta(days=days_since_monday)
    
    async def log_impact_event(
        self, 
        event: ImpactEventCreate
    ) -> str:
        """
        Log an impact event to the database.
        
        Args:
            event: ImpactEventCreate with all event data
            
        Returns:
            UUID of the created event
        """
        data = {
            "user_id": event.user_id,
            "source": event.source,
            "source_id": event.source_id,
            "ingredients": event.ingredients,
            "total_waste_kg": event.total_waste_kg,
            "total_cost_usd": event.total_cost_usd,
            "total_co2_kg": event.total_co2_kg,
            "status": "active"
        }
        
        result = self.supabase.table("impact_events").insert(data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get("id", "")
        
        return ""
    
    async def get_period_summary(
        self, 
        user_id: str, 
        start_date: date, 
        end_date: date,
        period_name: str = "custom"
    ) -> PeriodSummary:
        """
        Get aggregated impact for a specific date range.
        
        Args:
            user_id: User ID to query
            start_date: Start of period
            end_date: End of period (inclusive)
            period_name: Label for this period
            
        Returns:
            PeriodSummary with aggregated values
        """
        # Query impact events for the period
        result = self.supabase.table("impact_events")\
            .select("total_waste_kg, total_cost_usd, total_co2_kg")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .gte("created_at", start_date.isoformat())\
            .lt("created_at", (end_date + timedelta(days=1)).isoformat())\
            .execute()
        
        # Aggregate results
        events = result.data if result.data else []
        
        total_waste = sum(e.get("total_waste_kg", 0) for e in events)
        total_cost = sum(e.get("total_cost_usd", 0) for e in events)
        total_co2 = sum(e.get("total_co2_kg", 0) for e in events)
        
        return PeriodSummary(
            period=period_name,
            waste_kg=round(total_waste, 4),
            money_usd=round(total_cost, 2),
            co2_kg=round(total_co2, 4),
            event_count=len(events),
            start_date=start_date,
            end_date=end_date
        )
    
    async def get_all_time_totals(self, user_id: str) -> PeriodSummary:
        """
        Get all-time totals for a user.
        
        First tries to read from user_gamification table (denormalized).
        Falls back to aggregating from impact_events if needed.
        """
        # Try to get from gamification table (faster)
        gam_result = self.supabase.table("user_gamification")\
            .select("total_waste_kg, total_cost_usd, total_co2_kg, total_events")\
            .eq("user_id", user_id)\
            .execute()
        
        if gam_result.data and len(gam_result.data) > 0:
            data = gam_result.data[0]
            return PeriodSummary(
                period="all_time",
                waste_kg=data.get("total_waste_kg", 0),
                money_usd=data.get("total_cost_usd", 0),
                co2_kg=data.get("total_co2_kg", 0),
                event_count=data.get("total_events", 0)
            )
        
        # Fall back to aggregating from events
        result = self.supabase.table("impact_events")\
            .select("total_waste_kg, total_cost_usd, total_co2_kg")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
        
        events = result.data if result.data else []
        
        return PeriodSummary(
            period="all_time",
            waste_kg=round(sum(e.get("total_waste_kg", 0) for e in events), 4),
            money_usd=round(sum(e.get("total_cost_usd", 0) for e in events), 2),
            co2_kg=round(sum(e.get("total_co2_kg", 0) for e in events), 4),
            event_count=len(events)
        )
    
    async def get_weekly_summary(self, user_id: str) -> WeeklySummaryResponse:
        """
        Get comprehensive weekly summary including comparisons.
        
        Args:
            user_id: User ID to query
            
        Returns:
            WeeklySummaryResponse with this week, last week, all-time, and comparisons
        """
        today = date.today()
        this_week_start = self.get_week_start(today)
        last_week_start = this_week_start - timedelta(days=7)
        this_week_end = this_week_start + timedelta(days=6)
        last_week_end = last_week_start + timedelta(days=6)
        
        # Get summaries for each period
        this_week = await self.get_period_summary(
            user_id, this_week_start, this_week_end, "this_week"
        )
        last_week = await self.get_period_summary(
            user_id, last_week_start, last_week_end, "last_week"
        )
        all_time = await self.get_all_time_totals(user_id)
        
        # Get weekly goal from gamification
        weekly_goal = await self.get_weekly_goal(user_id)
        
        # Calculate comparison percentages
        comparison = {}
        if last_week.waste_kg > 0:
            comparison["waste_kg_change"] = round(
                ((this_week.waste_kg - last_week.waste_kg) / last_week.waste_kg) * 100, 1
            )
        if last_week.money_usd > 0:
            comparison["money_usd_change"] = round(
                ((this_week.money_usd - last_week.money_usd) / last_week.money_usd) * 100, 1
            )
        if last_week.co2_kg > 0:
            comparison["co2_kg_change"] = round(
                ((this_week.co2_kg - last_week.co2_kg) / last_week.co2_kg) * 100, 1
            )
        
        return WeeklySummaryResponse(
            user_id=user_id,
            this_week=this_week,
            last_week=last_week,
            all_time=all_time,
            weekly_goal=WeeklyProgress(
                current_kg=this_week.waste_kg,
                goal_kg=weekly_goal,
                percentage=round((this_week.waste_kg / weekly_goal) * 100, 1) if weekly_goal > 0 else 0,
                week_start=this_week_start
            ),
            comparison=comparison
        )
    
    async def get_weekly_goal(self, user_id: str) -> float:
        """Get the user's weekly goal in kg."""
        result = self.supabase.table("user_gamification")\
            .select("weekly_goal_kg")\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get("weekly_goal_kg", 2.0)
        
        return 2.0  # Default goal
    
    async def update_weekly_goal(self, user_id: str, goal_kg: float) -> bool:
        """
        Update a user's weekly goal.
        
        Args:
            user_id: User ID
            goal_kg: New goal in kg
            
        Returns:
            True if successful
        """
        # Ensure gamification record exists
        await self._ensure_gamification_record(user_id)
        
        result = self.supabase.table("user_gamification")\
            .update({"weekly_goal_kg": goal_kg, "updated_at": datetime.utcnow().isoformat()})\
            .eq("user_id", user_id)\
            .execute()
        
        return result.data is not None
    
    async def _ensure_gamification_record(self, user_id: str) -> None:
        """Create gamification record if it doesn't exist."""
        result = self.supabase.table("user_gamification")\
            .select("user_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            today = date.today()
            week_start = self.get_week_start(today)
            
            self.supabase.table("user_gamification").insert({
                "user_id": user_id,
                "current_streak": 0,
                "longest_streak": 0,
                "weekly_goal_kg": 2.0,
                "weekly_progress_kg": 0,
                "week_start_date": week_start.isoformat(),
                "total_waste_kg": 0,
                "total_cost_usd": 0,
                "total_co2_kg": 0,
                "total_events": 0,
                "badges": {}
            }).execute()
    
    async def update_user_totals(
        self, 
        user_id: str, 
        waste_kg: float, 
        cost_usd: float, 
        co2_kg: float
    ) -> None:
        """
        Increment user's all-time totals after an impact event.
        
        Args:
            user_id: User ID
            waste_kg: Amount to add to total waste
            cost_usd: Amount to add to total cost
            co2_kg: Amount to add to total CO2
        """
        await self._ensure_gamification_record(user_id)
        
        # Get current values
        result = self.supabase.table("user_gamification")\
            .select("total_waste_kg, total_cost_usd, total_co2_kg, total_events, weekly_progress_kg, week_start_date")\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            current = result.data[0]
            today = date.today()
            week_start = self.get_week_start(today)
            
            # Check if we need to reset weekly progress
            current_week_start = current.get("week_start_date")
            weekly_progress = current.get("weekly_progress_kg", 0)
            
            if current_week_start and current_week_start != week_start.isoformat():
                # New week, reset weekly progress
                weekly_progress = 0
            
            # Update totals
            self.supabase.table("user_gamification")\
                .update({
                    "total_waste_kg": current.get("total_waste_kg", 0) + waste_kg,
                    "total_cost_usd": current.get("total_cost_usd", 0) + cost_usd,
                    "total_co2_kg": current.get("total_co2_kg", 0) + co2_kg,
                    "total_events": current.get("total_events", 0) + 1,
                    "weekly_progress_kg": weekly_progress + waste_kg,
                    "week_start_date": week_start.isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("user_id", user_id)\
                .execute()
    
    async def get_recent_events(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent impact events for a user.
        
        Args:
            user_id: User ID
            limit: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        result = self.supabase.table("impact_events")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data if result.data else []


# Singleton instance for easy import
impact_aggregator = ImpactAggregator()
