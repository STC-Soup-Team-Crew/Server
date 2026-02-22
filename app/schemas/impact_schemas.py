"""
Pydantic schemas for the Impact Tracking system.
Defines request/response models for impact calculation, aggregation, and gamification.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class ImpactSource(str, Enum):
    """Source of the impact event."""
    RECIPE = "recipe"
    FRIDGE_SHARE = "fridge_share"
    MANUAL = "manual"


class BadgeTier(str, Enum):
    """Badge tier levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class BadgeType(str, Enum):
    """Types of badges that can be earned."""
    WASTE_SAVER = "waste_saver"
    MONEY_SAVER = "money_saver"
    CARBON_HERO = "carbon_hero"
    STREAK_MASTER = "streak_master"
    RECIPE_CHEF = "recipe_chef"
    COMMUNITY_HERO = "community_hero"


# =============================================================================
# Input Models
# =============================================================================

class IngredientInput(BaseModel):
    """Single ingredient input for impact calculation."""
    name: str = Field(..., description="Ingredient name (e.g., 'chicken breast', 'tomato')")
    quantity: float = Field(default=1.0, ge=0, description="Quantity of the ingredient")
    unit: Optional[str] = Field(default="piece", description="Unit of measurement (e.g., 'cups', 'pieces', 'kg')")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Normalize ingredient name."""
        return v.strip().lower()
    
    @field_validator('unit')
    @classmethod
    def validate_unit(cls, v: Optional[str]) -> str:
        """Normalize unit."""
        if v is None:
            return "piece"
        return v.strip().lower()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "chicken breast",
                "quantity": 2,
                "unit": "pieces"
            }
        }


class ImpactCalculationRequest(BaseModel):
    """Request body for calculating impact from a list of ingredients."""
    user_id: str = Field(..., description="User ID (Clerk ID or guest ID)")
    ingredients: List[IngredientInput] = Field(..., min_length=1, description="List of ingredients to calculate impact for")
    source: ImpactSource = Field(default=ImpactSource.RECIPE, description="Source of the impact event")
    source_id: Optional[str] = Field(default=None, description="Optional ID of the source (recipe_id, listing_id)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_2abc123",
                "source": "recipe",
                "ingredients": [
                    {"name": "chicken breast", "quantity": 2, "unit": "pieces"},
                    {"name": "broccoli", "quantity": 1, "unit": "head"},
                    {"name": "rice", "quantity": 1, "unit": "cup"}
                ]
            }
        }


class WeeklyGoalUpdateRequest(BaseModel):
    """Request to update a user's weekly goal."""
    user_id: str = Field(..., description="User ID")
    weekly_goal_kg: float = Field(..., gt=0, le=100, description="New weekly goal in kg")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_2abc123",
                "weekly_goal_kg": 3.0
            }
        }


# =============================================================================
# Output Models - Impact Calculation
# =============================================================================

class IngredientImpact(BaseModel):
    """Calculated impact for a single ingredient."""
    name: str
    quantity: float
    unit: str
    weight_kg: float = Field(..., description="Estimated weight in kg")
    cost_usd: float = Field(..., description="Estimated cost in USD")
    co2_kg: float = Field(..., description="Estimated CO2 equivalent in kg")
    found_in_lookup: bool = Field(default=True, description="Whether ingredient was found in lookup table")


class ImpactTotals(BaseModel):
    """Aggregated impact totals."""
    waste_prevented_kg: float = Field(..., description="Total food waste prevented in kg")
    money_saved_usd: float = Field(..., description="Total money saved in USD")
    co2_avoided_kg: float = Field(..., description="Total CO2 emissions avoided in kg")
    
    class Config:
        json_schema_extra = {
            "example": {
                "waste_prevented_kg": 0.62,
                "money_saved_usd": 8.45,
                "co2_avoided_kg": 4.12
            }
        }


class WeeklyProgress(BaseModel):
    """Progress toward weekly goal."""
    current_kg: float = Field(..., description="kg saved this week")
    goal_kg: float = Field(..., description="Weekly goal in kg")
    percentage: float = Field(..., description="Percentage of goal achieved (0-100+)")
    week_start: date = Field(..., description="Start date of the current week")


class GamificationUpdate(BaseModel):
    """Gamification state after an impact event."""
    streak: int = Field(..., description="Current streak in days")
    is_new_streak_record: bool = Field(default=False, description="Whether this is a new personal best")
    new_badges: List[Dict[str, Any]] = Field(default=[], description="Any new badges earned from this action")
    weekly_progress: WeeklyProgress


class ImpactCalculationResponse(BaseModel):
    """Full response from impact calculation endpoint."""
    event_id: str = Field(..., description="UUID of the logged impact event")
    totals: ImpactTotals
    breakdown: List[IngredientImpact] = Field(..., description="Per-ingredient impact breakdown")
    gamification: GamificationUpdate
    message: str = Field(default="Impact calculated successfully")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "totals": {
                    "waste_prevented_kg": 0.62,
                    "money_saved_usd": 8.45,
                    "co2_avoided_kg": 4.12
                },
                "breakdown": [
                    {"name": "chicken breast", "quantity": 2, "unit": "pieces", "weight_kg": 0.34, "cost_usd": 5.50, "co2_kg": 3.40, "found_in_lookup": True}
                ],
                "gamification": {
                    "streak": 5,
                    "is_new_streak_record": False,
                    "new_badges": [],
                    "weekly_progress": {"current_kg": 2.1, "goal_kg": 3.0, "percentage": 70, "week_start": "2026-02-17"}
                },
                "message": "Impact calculated successfully"
            }
        }


# =============================================================================
# Output Models - Summary & Aggregation
# =============================================================================

class PeriodSummary(BaseModel):
    """Summary for a specific time period."""
    period: str = Field(..., description="Period label (e.g., 'this_week', 'last_week', 'all_time')")
    waste_kg: float
    money_usd: float
    co2_kg: float
    event_count: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class WeeklySummaryResponse(BaseModel):
    """Response containing weekly and all-time summaries."""
    user_id: str
    this_week: PeriodSummary
    last_week: PeriodSummary
    all_time: PeriodSummary
    weekly_goal: WeeklyProgress
    comparison: Dict[str, float] = Field(
        default={},
        description="Percentage change from last week (positive = improvement)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_2abc123",
                "this_week": {
                    "period": "this_week",
                    "waste_kg": 2.5,
                    "money_usd": 18.50,
                    "co2_kg": 8.2,
                    "event_count": 4,
                    "start_date": "2026-02-17",
                    "end_date": "2026-02-23"
                },
                "last_week": {
                    "period": "last_week",
                    "waste_kg": 1.8,
                    "money_usd": 14.20,
                    "co2_kg": 6.5,
                    "event_count": 3,
                    "start_date": "2026-02-10",
                    "end_date": "2026-02-16"
                },
                "all_time": {
                    "period": "all_time",
                    "waste_kg": 25.3,
                    "money_usd": 185.00,
                    "co2_kg": 82.5,
                    "event_count": 45
                },
                "weekly_goal": {
                    "current_kg": 2.5,
                    "goal_kg": 3.0,
                    "percentage": 83.3,
                    "week_start": "2026-02-17"
                },
                "comparison": {
                    "waste_kg_change": 38.9,
                    "money_usd_change": 30.3,
                    "co2_kg_change": 26.2
                }
            }
        }


# =============================================================================
# Output Models - Gamification
# =============================================================================

class BadgeInfo(BaseModel):
    """Information about a badge."""
    type: BadgeType
    tier: BadgeTier
    name: str = Field(..., description="Display name of the badge")
    description: str
    earned_at: Optional[datetime] = None
    progress: Optional[float] = Field(None, description="Progress toward next tier (0-100)")
    next_tier_threshold: Optional[float] = Field(None, description="Value needed for next tier")


class StreakInfo(BaseModel):
    """Information about user's streak."""
    current: int = Field(..., description="Current streak in days")
    longest: int = Field(..., description="Longest streak ever achieved")
    last_active: Optional[date] = Field(None, description="Last date of activity")
    is_active_today: bool = Field(default=False, description="Whether user has logged activity today")


class GamificationResponse(BaseModel):
    """Full gamification state for a user."""
    user_id: str
    streak: StreakInfo
    badges: List[BadgeInfo]
    weekly_goal: WeeklyProgress
    next_badge_progress: Optional[BadgeInfo] = Field(
        None, 
        description="The badge closest to being earned"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_2abc123",
                "streak": {
                    "current": 5,
                    "longest": 12,
                    "last_active": "2026-02-22",
                    "is_active_today": True
                },
                "badges": [
                    {
                        "type": "waste_saver",
                        "tier": "bronze",
                        "name": "Food Saver",
                        "description": "Prevented 5kg of food waste",
                        "earned_at": "2026-02-15T10:30:00Z",
                        "progress": 60.0,
                        "next_tier_threshold": 25.0
                    }
                ],
                "weekly_goal": {
                    "current_kg": 2.5,
                    "goal_kg": 3.0,
                    "percentage": 83.3,
                    "week_start": "2026-02-17"
                },
                "next_badge_progress": {
                    "type": "money_saver",
                    "tier": "bronze",
                    "name": "Penny Pincher",
                    "description": "Save $50 on groceries",
                    "progress": 85.0,
                    "next_tier_threshold": 50.0
                }
            }
        }


# =============================================================================
# Database Models (for internal use)
# =============================================================================

class ImpactEventCreate(BaseModel):
    """Model for creating an impact event in the database."""
    user_id: str
    source: str
    source_id: Optional[str] = None
    ingredients: List[Dict[str, Any]]
    total_waste_kg: float
    total_cost_usd: float
    total_co2_kg: float


class UserGamificationCreate(BaseModel):
    """Model for creating/updating gamification record."""
    user_id: str
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: Optional[date] = None
    weekly_goal_kg: float = 2.0
    weekly_progress_kg: float = 0.0
    week_start_date: Optional[date] = None
    total_waste_kg: float = 0.0
    total_cost_usd: float = 0.0
    total_co2_kg: float = 0.0
    total_events: int = 0
    badges: Dict[str, Any] = {}
