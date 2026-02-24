"""
Impact Calculator Service

Calculates environmental and financial impact for ingredients.
Takes ingredient inputs and returns weight, cost, and carbon estimates.
"""

from typing import List, Dict, Any, Tuple
from ..data.ingredient_defaults import (
    get_ingredient_data,
    get_unit_multiplier,
    DEFAULT_INGREDIENT,
    UNIT_CONVERSIONS
)
from ..schemas.impact_schemas import (
    IngredientInput,
    IngredientImpact,
    ImpactTotals
)


class ImpactCalculator:
    """
    Service for calculating environmental and financial impact of ingredients.
    
    Uses lookup tables for ingredient weights, costs, and carbon intensity.
    Supports various units and quantity specifications.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        pass
    
    def calculate_single_ingredient(
        self, 
        ingredient: IngredientInput
    ) -> IngredientImpact:
        """
        Calculate impact for a single ingredient.
        
        Args:
            ingredient: IngredientInput with name, quantity, and unit
            
        Returns:
            IngredientImpact with calculated values
        """
        # Look up ingredient data
        data = get_ingredient_data(ingredient.name)
        found_in_lookup = data != DEFAULT_INGREDIENT
        
        # Get base values from lookup
        base_weight_kg = data["weight_kg"]
        base_cost_usd = data["cost_usd"]
        carbon_per_kg = data["carbon_kg_co2e"]
        
        # Calculate actual weight based on quantity and unit
        weight_kg = self._calculate_weight(
            ingredient.quantity,
            ingredient.unit or "piece",
            base_weight_kg
        )
        
        # Calculate cost (proportional to weight)
        # Cost is stored per-unit in lookup, so scale by quantity
        cost_usd = self._calculate_cost(
            ingredient.quantity,
            ingredient.unit or "piece",
            base_cost_usd,
            base_weight_kg
        )
        
        # Calculate CO2 (carbon intensity * actual weight)
        co2_kg = round(weight_kg * carbon_per_kg, 4)
        
        return IngredientImpact(
            name=ingredient.name,
            quantity=ingredient.quantity,
            unit=ingredient.unit or "piece",
            weight_kg=round(weight_kg, 4),
            cost_usd=round(cost_usd, 2),
            co2_kg=round(co2_kg, 4),
            found_in_lookup=found_in_lookup
        )
    
    def _calculate_weight(
        self, 
        quantity: float, 
        unit: str, 
        base_weight_kg: float
    ) -> float:
        """
        Calculate total weight in kg based on quantity and unit.
        
        For weight/volume units: convert directly
        For count units: multiply by ingredient's base weight
        """
        normalized_unit = unit.lower().strip()
        
        # Direct weight units
        weight_units = {"kg", "g", "gram", "grams", "lb", "lbs", "pound", "pounds", "oz", "ounce", "ounces"}
        if normalized_unit in weight_units:
            multiplier = UNIT_CONVERSIONS.get(normalized_unit, 1.0)
            return quantity * multiplier
        
        # Volume units (approximate)
        volume_units = {"cup", "cups", "tbsp", "tablespoon", "tablespoons", "tsp", "teaspoon", "teaspoons", "ml", "l", "liter", "liters"}
        if normalized_unit in volume_units:
            multiplier = UNIT_CONVERSIONS.get(normalized_unit, 0.24)
            return quantity * multiplier
        
        # Count units - use base weight
        count_multiplier = UNIT_CONVERSIONS.get(normalized_unit, 1.0)
        return quantity * base_weight_kg * count_multiplier
    
    def _calculate_cost(
        self, 
        quantity: float, 
        unit: str, 
        base_cost_usd: float,
        base_weight_kg: float
    ) -> float:
        """
        Calculate estimated cost based on quantity.
        
        For count-based units: multiply base cost by quantity
        For weight/volume: calculate proportionally
        """
        normalized_unit = unit.lower().strip()
        
        # For count-based units, scale directly
        count_units = {"piece", "pieces", "item", "items", "whole", "head", "bunch", "can", "cans", "package", "packages", "bag", "bags", "box", "boxes", "bottle", "bottles", "jar", "jars"}
        if normalized_unit in count_units:
            multiplier = UNIT_CONVERSIONS.get(normalized_unit, 1.0)
            return quantity * base_cost_usd * multiplier
        
        # For weight/volume, calculate cost per kg and scale
        weight_kg = self._calculate_weight(quantity, unit, base_weight_kg)
        cost_per_kg = base_cost_usd / base_weight_kg if base_weight_kg > 0 else base_cost_usd
        return weight_kg * cost_per_kg
    
    def calculate_total_impact(
        self, 
        ingredients: List[IngredientInput]
    ) -> Tuple[ImpactTotals, List[IngredientImpact]]:
        """
        Calculate total impact for a list of ingredients.
        
        Args:
            ingredients: List of IngredientInput objects
            
        Returns:
            Tuple of (ImpactTotals, List[IngredientImpact])
        """
        breakdown = []
        total_waste = 0.0
        total_cost = 0.0
        total_co2 = 0.0
        
        for ingredient in ingredients:
            impact = self.calculate_single_ingredient(ingredient)
            breakdown.append(impact)
            total_waste += impact.weight_kg
            total_cost += impact.cost_usd
            total_co2 += impact.co2_kg
        
        totals = ImpactTotals(
            waste_prevented_kg=round(total_waste, 4),
            money_saved_usd=round(total_cost, 2),
            co2_avoided_kg=round(total_co2, 4)
        )
        
        return totals, breakdown
    
    def estimate_from_recipe_name(self, recipe_name: str) -> ImpactTotals:
        """
        Provide a rough estimate for a recipe based on its name.
        Used when detailed ingredients aren't available.
        
        Args:
            recipe_name: Name of the recipe
            
        Returns:
            ImpactTotals with rough estimates
        """
        # Default: assume average meal ~400g, ~$8, ~3kg CO2
        # Adjust based on keywords
        name_lower = recipe_name.lower()
        
        base_waste = 0.4  # kg
        base_cost = 8.0   # USD
        base_co2 = 3.0    # kg CO2e
        
        # Adjust for recipe type
        if any(word in name_lower for word in ["salad", "vegetable", "vegan", "veggie"]):
            base_co2 *= 0.5  # Lower carbon for plant-based
            base_cost *= 0.7
        elif any(word in name_lower for word in ["beef", "steak", "burger"]):
            base_co2 *= 2.5  # Higher carbon for beef
            base_cost *= 1.5
        elif any(word in name_lower for word in ["chicken", "turkey"]):
            base_co2 *= 1.2
        elif any(word in name_lower for word in ["fish", "salmon", "tuna", "shrimp"]):
            base_co2 *= 1.0
            base_cost *= 1.3
        
        # Adjust for portion words
        if any(word in name_lower for word in ["family", "large", "feast"]):
            base_waste *= 2.0
            base_cost *= 2.0
            base_co2 *= 2.0
        elif any(word in name_lower for word in ["small", "mini", "snack"]):
            base_waste *= 0.5
            base_cost *= 0.5
            base_co2 *= 0.5
        
        return ImpactTotals(
            waste_prevented_kg=round(base_waste, 4),
            money_saved_usd=round(base_cost, 2),
            co2_avoided_kg=round(base_co2, 4)
        )


# Singleton instance for easy import
impact_calculator = ImpactCalculator()
