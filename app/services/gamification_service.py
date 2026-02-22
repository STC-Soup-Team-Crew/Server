"""
Gamification Service

Handles streaks, badges, and weekly goals for users.
Provides motivation and engagement through game-like mechanics.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from ..data.ingredient_defaults import BADGE_THRESHOLDS
from ..schemas.impact_schemas import (
    BadgeInfo,
    BadgeTier,
    BadgeType,
    StreakInfo,
    GamificationResponse,
    WeeklyProgress,
    GamificationUpdate
)


# Badge display names and descriptions
BADGE_METADATA = {
    BadgeType.WASTE_SAVER: {
        "name": "Food Saver",
        "descriptions": {
            BadgeTier.BRONZE: "Prevented 5kg of food waste",
            BadgeTier.SILVER: "Prevented 25kg of food waste",
            BadgeTier.GOLD: "Prevented 100kg of food waste - Food Waste Champion!"
        }
    },
    BadgeType.MONEY_SAVER: {
        "name": "Penny Pincher",
        "descriptions": {
            BadgeTier.BRONZE: "Saved $50 on groceries",
            BadgeTier.SILVER: "Saved $250 on groceries",
            BadgeTier.GOLD: "Saved $1000 on groceries - Budget Master!"
        }
    },
    BadgeType.CARBON_HERO: {
        "name": "Climate Guardian",
        "descriptions": {
            BadgeTier.BRONZE: "Avoided 10kg of CO₂ emissions",
            BadgeTier.SILVER: "Avoided 50kg of CO₂ emissions",
            BadgeTier.GOLD: "Avoided 200kg of CO₂ emissions - Planet Protector!"
        }
    },
    BadgeType.STREAK_MASTER: {
        "name": "Streak Master",
        "descriptions": {
            BadgeTier.BRONZE: "Maintained a 7-day streak",
            BadgeTier.SILVER: "Maintained a 30-day streak",
            BadgeTier.GOLD: "Maintained a 100-day streak - Unstoppable!"
        }
    },
    BadgeType.RECIPE_CHEF: {
        "name": "Home Chef",
        "descriptions": {
            BadgeTier.BRONZE: "Made 5 recipes",
            BadgeTier.SILVER: "Made 25 recipes",
            BadgeTier.GOLD: "Made 100 recipes - Master Chef!"
        }
    },
    BadgeType.COMMUNITY_HERO: {
        "name": "Community Hero",
        "descriptions": {
            BadgeTier.BRONZE: "Shared 3 food items",
            BadgeTier.SILVER: "Shared 15 food items",
            BadgeTier.GOLD: "Shared 50 food items - Neighborhood Hero!"
        }
    }
}


class GamificationService:
    """
    Service for managing user gamification elements.
    
    Handles:
    - Streak tracking (consecutive days of activity)
    - Badge progression and awarding
    - Weekly goal tracking
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize the service.
        
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
    
    def _get_week_start(self, target_date: Optional[date] = None) -> date:
        """Get the Monday of the week containing target_date."""
        if target_date is None:
            target_date = date.today()
        days_since_monday = target_date.weekday()
        return target_date - timedelta(days=days_since_monday)
    
    async def _ensure_gamification_record(self, user_id: str) -> Dict[str, Any]:
        """
        Ensure a gamification record exists for the user.
        Returns the existing or newly created record.
        """
        result = self.supabase.table("user_gamification")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        # Create new record
        today = date.today()
        week_start = self._get_week_start(today)
        
        new_record = {
            "user_id": user_id,
            "current_streak": 0,
            "longest_streak": 0,
            "last_active_date": None,
            "weekly_goal_kg": 2.0,
            "weekly_progress_kg": 0,
            "week_start_date": week_start.isoformat(),
            "total_waste_kg": 0,
            "total_cost_usd": 0,
            "total_co2_kg": 0,
            "total_events": 0,
            "badges": {}
        }
        
        insert_result = self.supabase.table("user_gamification")\
            .insert(new_record)\
            .execute()
        
        if insert_result.data and len(insert_result.data) > 0:
            return insert_result.data[0]
        
        return new_record
    
    async def update_streak(self, user_id: str) -> Tuple[int, bool]:
        """
        Update the user's streak based on today's activity.
        
        Logic:
        - If last_active_date is yesterday: increment streak
        - If last_active_date is today: no change (already counted)
        - Otherwise: reset to 1 (starting new streak)
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (new_streak, is_new_record)
        """
        record = await self._ensure_gamification_record(user_id)
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        current_streak = record.get("current_streak", 0)
        longest_streak = record.get("longest_streak", 0)
        last_active_str = record.get("last_active_date")
        
        # Parse last active date
        last_active = None
        if last_active_str:
            try:
                if isinstance(last_active_str, str):
                    last_active = date.fromisoformat(last_active_str)
                else:
                    last_active = last_active_str
            except (ValueError, TypeError):
                pass
        
        # Calculate new streak
        new_streak = current_streak
        
        if last_active == today:
            # Already logged today, no change
            return current_streak, False
        elif last_active == yesterday:
            # Continuing streak
            new_streak = current_streak + 1
        else:
            # Starting new streak
            new_streak = 1
        
        # Check if new record
        is_new_record = new_streak > longest_streak
        new_longest = max(longest_streak, new_streak)
        
        # Update database
        self.supabase.table("user_gamification")\
            .update({
                "current_streak": new_streak,
                "longest_streak": new_longest,
                "last_active_date": today.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("user_id", user_id)\
            .execute()
        
        return new_streak, is_new_record
    
    async def check_and_award_badges(
        self, 
        user_id: str,
        totals: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Check badge thresholds and award any newly earned badges.
        
        Args:
            user_id: User ID
            totals: Optional dict with waste_kg, cost_usd, co2_kg to check against.
                   If None, will fetch from database.
                   
        Returns:
            List of newly awarded badges (badge_type, tier)
        """
        record = await self._ensure_gamification_record(user_id)
        
        # Get current values
        if totals is None:
            totals = {
                "waste_kg": record.get("total_waste_kg", 0),
                "cost_usd": record.get("total_cost_usd", 0),
                "co2_kg": record.get("total_co2_kg", 0),
                "streak": record.get("current_streak", 0),
                "events": record.get("total_events", 0)
            }
        else:
            totals["streak"] = record.get("current_streak", 0)
            totals["events"] = record.get("total_events", 0)
        
        # Get current badges
        current_badges = record.get("badges", {})
        if current_badges is None:
            current_badges = {}
        
        new_badges = []
        
        # Check each badge type
        badge_checks = [
            (BadgeType.WASTE_SAVER, "waste_saver", totals.get("waste_kg", 0)),
            (BadgeType.MONEY_SAVER, "money_saver", totals.get("cost_usd", 0)),
            (BadgeType.CARBON_HERO, "carbon_hero", totals.get("co2_kg", 0)),
            (BadgeType.STREAK_MASTER, "streak_master", totals.get("streak", 0)),
            (BadgeType.RECIPE_CHEF, "recipe_chef", totals.get("events", 0)),
        ]
        
        for badge_type, threshold_key, current_value in badge_checks:
            thresholds = BADGE_THRESHOLDS.get(threshold_key, {})
            current_badge = current_badges.get(threshold_key, {})
            current_tier = current_badge.get("tier") if current_badge else None
            
            # Check each tier
            for tier_name, tier_value in [("bronze", BadgeTier.BRONZE), ("silver", BadgeTier.SILVER), ("gold", BadgeTier.GOLD)]:
                threshold = thresholds.get(tier_name, float('inf'))
                
                if current_value >= threshold:
                    # Earned this tier
                    tier_order = {"bronze": 0, "silver": 1, "gold": 2}
                    current_order = tier_order.get(current_tier, -1)
                    new_order = tier_order.get(tier_name, 0)
                    
                    if new_order > current_order:
                        # New badge/tier earned!
                        badge_info = {
                            "type": badge_type.value,
                            "tier": tier_name,
                            "earned_at": datetime.utcnow().isoformat(),
                            "name": BADGE_METADATA[badge_type]["name"],
                            "description": BADGE_METADATA[badge_type]["descriptions"][tier_value]
                        }
                        
                        current_badges[threshold_key] = {
                            "tier": tier_name,
                            "earned_at": datetime.utcnow().isoformat()
                        }
                        
                        new_badges.append(badge_info)
        
        # Update badges in database if any new ones
        if new_badges:
            self.supabase.table("user_gamification")\
                .update({
                    "badges": current_badges,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("user_id", user_id)\
                .execute()
        
        return new_badges
    
    async def get_gamification_state(self, user_id: str) -> GamificationResponse:
        """
        Get the full gamification state for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            GamificationResponse with streak, badges, and weekly goal
        """
        record = await self._ensure_gamification_record(user_id)
        
        today = date.today()
        week_start = self._get_week_start(today)
        
        # Parse last active date
        last_active_str = record.get("last_active_date")
        last_active = None
        if last_active_str:
            try:
                if isinstance(last_active_str, str):
                    last_active = date.fromisoformat(last_active_str)
                else:
                    last_active = last_active_str
            except (ValueError, TypeError):
                pass
        
        # Build streak info
        streak_info = StreakInfo(
            current=record.get("current_streak", 0),
            longest=record.get("longest_streak", 0),
            last_active=last_active,
            is_active_today=last_active == today
        )
        
        # Build badge list
        badges = []
        current_badges = record.get("badges", {})
        totals = {
            "waste_kg": record.get("total_waste_kg", 0),
            "cost_usd": record.get("total_cost_usd", 0),
            "co2_kg": record.get("total_co2_kg", 0),
            "streak": record.get("current_streak", 0),
            "events": record.get("total_events", 0)
        }
        
        for badge_type in BadgeType:
            threshold_key = badge_type.value
            badge_data = current_badges.get(threshold_key, {}) if current_badges else {}
            thresholds = BADGE_THRESHOLDS.get(threshold_key, {})
            
            # Get current value for this badge type
            value_map = {
                "waste_saver": totals["waste_kg"],
                "money_saver": totals["cost_usd"],
                "carbon_hero": totals["co2_kg"],
                "streak_master": totals["streak"],
                "recipe_chef": totals["events"],
                "community_hero": 0  # TODO: track shares separately
            }
            current_value = value_map.get(threshold_key, 0)
            
            if badge_data and badge_data.get("tier"):
                # Has earned badge
                tier_str = badge_data.get("tier")
                tier = BadgeTier(tier_str)
                earned_at_str = badge_data.get("earned_at")
                earned_at = None
                if earned_at_str:
                    try:
                        earned_at = datetime.fromisoformat(earned_at_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
                
                # Calculate progress to next tier
                tier_order = {"bronze": 0, "silver": 1, "gold": 2}
                current_order = tier_order.get(tier_str, 0)
                next_tier_key = ["silver", "gold", None][current_order] if current_order < 2 else None
                next_threshold = thresholds.get(next_tier_key) if next_tier_key else None
                
                progress = None
                if next_threshold:
                    progress = min(100, round((current_value / next_threshold) * 100, 1))
                
                badges.append(BadgeInfo(
                    type=badge_type,
                    tier=tier,
                    name=BADGE_METADATA[badge_type]["name"],
                    description=BADGE_METADATA[badge_type]["descriptions"][tier],
                    earned_at=earned_at,
                    progress=progress,
                    next_tier_threshold=next_threshold
                ))
        
        # Find next badge closest to earning
        next_badge = None
        closest_progress = 0
        
        for badge_type in BadgeType:
            threshold_key = badge_type.value
            badge_data = current_badges.get(threshold_key, {}) if current_badges else {}
            thresholds = BADGE_THRESHOLDS.get(threshold_key, {})
            
            value_map = {
                "waste_saver": totals["waste_kg"],
                "money_saver": totals["cost_usd"],
                "carbon_hero": totals["co2_kg"],
                "streak_master": totals["streak"],
                "recipe_chef": totals["events"],
                "community_hero": 0
            }
            current_value = value_map.get(threshold_key, 0)
            
            # Find next tier to earn
            current_tier = badge_data.get("tier") if badge_data else None
            tier_order = {"bronze": 0, "silver": 1, "gold": 2}
            current_order = tier_order.get(current_tier, -1)
            
            next_tiers = ["bronze", "silver", "gold"][current_order + 1:]
            for next_tier_key in next_tiers:
                threshold = thresholds.get(next_tier_key)
                if threshold and current_value < threshold:
                    progress = (current_value / threshold) * 100
                    if progress > closest_progress:
                        closest_progress = progress
                        next_badge = BadgeInfo(
                            type=badge_type,
                            tier=BadgeTier(next_tier_key),
                            name=BADGE_METADATA[badge_type]["name"],
                            description=BADGE_METADATA[badge_type]["descriptions"][BadgeTier(next_tier_key)],
                            progress=round(progress, 1),
                            next_tier_threshold=threshold
                        )
                    break
        
        # Build weekly progress
        weekly_progress = WeeklyProgress(
            current_kg=record.get("weekly_progress_kg", 0),
            goal_kg=record.get("weekly_goal_kg", 2.0),
            percentage=round((record.get("weekly_progress_kg", 0) / max(record.get("weekly_goal_kg", 2.0), 0.01)) * 100, 1),
            week_start=week_start
        )
        
        return GamificationResponse(
            user_id=user_id,
            streak=streak_info,
            badges=badges,
            weekly_goal=weekly_progress,
            next_badge_progress=next_badge
        )
    
    async def get_gamification_update(
        self, 
        user_id: str,
        new_waste_kg: float
    ) -> GamificationUpdate:
        """
        Get a gamification update after an impact event.
        This is a lighter version for immediate feedback.
        
        Args:
            user_id: User ID
            new_waste_kg: Amount of waste from this event
            
        Returns:
            GamificationUpdate with streak, new badges, and weekly progress
        """
        # Update streak
        new_streak, is_new_record = await self.update_streak(user_id)
        
        # Check for new badges
        record = await self._ensure_gamification_record(user_id)
        new_badges = await self.check_and_award_badges(user_id)
        
        # Get updated weekly progress
        today = date.today()
        week_start = self._get_week_start(today)
        
        # Re-fetch to get updated values
        result = self.supabase.table("user_gamification")\
            .select("weekly_progress_kg, weekly_goal_kg")\
            .eq("user_id", user_id)\
            .execute()
        
        weekly_current = 0
        weekly_goal = 2.0
        if result.data and len(result.data) > 0:
            weekly_current = result.data[0].get("weekly_progress_kg", 0)
            weekly_goal = result.data[0].get("weekly_goal_kg", 2.0)
        
        weekly_progress = WeeklyProgress(
            current_kg=round(weekly_current, 4),
            goal_kg=weekly_goal,
            percentage=round((weekly_current / max(weekly_goal, 0.01)) * 100, 1),
            week_start=week_start
        )
        
        return GamificationUpdate(
            streak=new_streak,
            is_new_streak_record=is_new_record,
            new_badges=new_badges,
            weekly_progress=weekly_progress
        )


# Singleton instance for easy import
gamification_service = GamificationService()
