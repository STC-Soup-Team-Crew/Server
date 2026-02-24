"""
Impact Tracking API Endpoints

Provides endpoints for:
- Calculating impact from ingredients
- Getting weekly/all-time summaries
- Managing gamification (badges, streaks, goals)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json

from ...schemas.impact_schemas import (
    ImpactCalculationRequest,
    ImpactCalculationResponse,
    WeeklySummaryResponse,
    GamificationResponse,
    WeeklyGoalUpdateRequest,
    ImpactEventCreate,
    IngredientInput
)
from ...services.impact_calculator import impact_calculator
from ...services.impact_aggregator import impact_aggregator
from ...services.gamification_service import gamification_service

router = APIRouter(prefix="/impact", tags=["Impact Tracking"])


@router.post(
    "/calculate",
    response_model=ImpactCalculationResponse,
    summary="Calculate environmental impact",
    description="""
    Calculate the environmental and financial impact of using a list of ingredients.
    
    This endpoint:
    1. Looks up each ingredient's weight, cost, and carbon intensity
    2. Calculates totals for waste prevented, money saved, and CO₂ avoided
    3. Logs the event to the user's history
    4. Updates gamification (streaks, badges, weekly progress)
    5. Returns a detailed breakdown and any newly earned badges
    
    **Use Cases:**
    - After a user makes a recipe (source="recipe")
    - After a user claims/shares food on FridgeShare (source="fridge_share")
    - Manual logging (source="manual")
    """
)
async def calculate_impact(request: ImpactCalculationRequest):
    """Calculate and log impact for a list of ingredients."""
    try:
        # Calculate impact
        totals, breakdown = impact_calculator.calculate_total_impact(request.ingredients)
        
        # Log the event
        event_data = ImpactEventCreate(
            user_id=request.user_id,
            source=request.source.value,
            source_id=request.source_id,
            ingredients=[
                {
                    "name": b.name,
                    "quantity": b.quantity,
                    "unit": b.unit,
                    "weight_kg": b.weight_kg,
                    "cost_usd": b.cost_usd,
                    "co2_kg": b.co2_kg
                }
                for b in breakdown
            ],
            total_waste_kg=totals.waste_prevented_kg,
            total_cost_usd=totals.money_saved_usd,
            total_co2_kg=totals.co2_avoided_kg
        )
        
        event_id = await impact_aggregator.log_impact_event(event_data)
        
        # Update user totals
        await impact_aggregator.update_user_totals(
            request.user_id,
            totals.waste_prevented_kg,
            totals.money_saved_usd,
            totals.co2_avoided_kg
        )
        
        # Get gamification update
        gamification = await gamification_service.get_gamification_update(
            request.user_id,
            totals.waste_prevented_kg
        )
        
        return ImpactCalculationResponse(
            event_id=event_id or "mock-event-id",
            totals=totals,
            breakdown=breakdown,
            gamification=gamification,
            message="Impact calculated and logged successfully!"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating impact: {str(e)}")


@router.get(
    "/summary/{user_id}",
    response_model=WeeklySummaryResponse,
    summary="Get user's impact summary",
    description="""
    Get a comprehensive summary of a user's environmental impact.
    
    Returns:
    - This week's totals
    - Last week's totals (for comparison)
    - All-time totals
    - Weekly goal progress
    - Percentage change from last week
    """
)
async def get_impact_summary(user_id: str):
    """Get weekly and all-time impact summary for a user."""
    try:
        summary = await impact_aggregator.get_weekly_summary(user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")


@router.get(
    "/badges/{user_id}",
    response_model=GamificationResponse,
    summary="Get user's gamification state",
    description="""
    Get the full gamification state for a user including:
    - Current and longest streak
    - All earned badges with tiers
    - Progress toward next badges
    - Weekly goal status
    """
)
async def get_gamification(user_id: str):
    """Get badges, streak, and gamification state for a user."""
    try:
        state = await gamification_service.get_gamification_state(user_id)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gamification: {str(e)}")


@router.put(
    "/goal",
    summary="Update weekly goal",
    description="Update a user's weekly waste prevention goal (in kg)."
)
async def update_weekly_goal(request: WeeklyGoalUpdateRequest):
    """Update a user's weekly goal."""
    try:
        success = await impact_aggregator.update_weekly_goal(
            request.user_id,
            request.weekly_goal_kg
        )
        
        if success:
            return {"message": f"Weekly goal updated to {request.weekly_goal_kg}kg", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to update goal")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating goal: {str(e)}")


@router.get(
    "/history/{user_id}",
    summary="Get recent impact events",
    description="Get the most recent impact events for a user."
)
async def get_impact_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of events to return")
):
    """Get recent impact events for a user."""
    try:
        events = await impact_aggregator.get_recent_events(user_id, limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.post(
    "/estimate",
    summary="Quick impact estimate",
    description="""
    Get a quick impact estimate without logging to database.
    Useful for preview/display before confirming an action.
    """
)
async def estimate_impact(ingredients: List[IngredientInput]):
    """Get a quick estimate without logging."""
    try:
        totals, breakdown = impact_calculator.calculate_total_impact(ingredients)
        return {
            "totals": totals,
            "breakdown": breakdown,
            "note": "This is an estimate. Use /calculate to log this impact."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error estimating impact: {str(e)}")


# Health check for this router
@router.get("/health")
async def health_check():
    """Health check for impact tracking service."""
    return {"status": "healthy", "service": "impact-tracking"}
