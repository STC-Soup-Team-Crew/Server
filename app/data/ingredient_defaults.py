"""
Default ingredient lookup data for impact calculations.

Data Sources:
- Weight: USDA FoodData Central (typical serving/unit weights)
- Cost: Average US grocery prices (2024-2026 estimates)
- Carbon: DEFRA emissions factors, EPA estimates, academic research

Note: These are reasonable estimates for a hackathon demo.
For production, integrate with:
- USDA FoodData Central API for nutrition/weights
- Climatiq API or CarbonCloud for carbon footprints
- Regional grocery APIs for accurate pricing

Carbon Intensity Reference (kg CO2e per kg of food):
- Beef: 27.0
- Lamb: 39.2
- Pork: 12.1
- Chicken: 6.9
- Fish: 5.4
- Eggs: 4.8
- Dairy (cheese): 13.5
- Dairy (milk): 3.2
- Rice: 4.0
- Vegetables: 0.5-2.0
- Fruits: 0.4-1.1
"""

from typing import Dict, List, Any

# Type alias for ingredient data
IngredientData = Dict[str, Any]

# Default values when ingredient not found
DEFAULT_INGREDIENT: IngredientData = {
    "weight_kg": 0.15,      # ~150g average portion
    "cost_usd": 2.00,       # ~$2 average item
    "carbon_kg_co2e": 2.0,  # ~2 kg CO2e (conservative middle estimate)
    "category": "other",
    "aliases": []
}

# Badge thresholds for gamification
BADGE_THRESHOLDS = {
    "waste_saver": {
        "bronze": 5.0,      # kg food waste prevented
        "silver": 25.0,
        "gold": 100.0
    },
    "money_saver": {
        "bronze": 50.0,     # USD saved
        "silver": 250.0,
        "gold": 1000.0
    },
    "carbon_hero": {
        "bronze": 10.0,     # kg CO2 avoided
        "silver": 50.0,
        "gold": 200.0
    },
    "streak_master": {
        "bronze": 7,        # days
        "silver": 30,
        "gold": 100
    },
    "recipe_chef": {
        "bronze": 5,        # recipes made
        "silver": 25,
        "gold": 100
    },
    "community_hero": {
        "bronze": 3,        # items shared
        "silver": 15,
        "gold": 50
    }
}

# Unit conversion factors to kg
UNIT_CONVERSIONS = {
    # Weight units
    "kg": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "lb": 0.453592,
    "lbs": 0.453592,
    "pound": 0.453592,
    "pounds": 0.453592,
    "oz": 0.0283495,
    "ounce": 0.0283495,
    "ounces": 0.0283495,
    
    # Volume units (approximate conversions for general ingredients)
    "cup": 0.24,        # ~240g for most ingredients
    "cups": 0.24,
    "tbsp": 0.015,      # ~15g
    "tablespoon": 0.015,
    "tablespoons": 0.015,
    "tsp": 0.005,       # ~5g
    "teaspoon": 0.005,
    "teaspoons": 0.005,
    "ml": 0.001,
    "l": 1.0,
    "liter": 1.0,
    "liters": 1.0,
    
    # Count units (will use ingredient-specific weight)
    "piece": 1.0,       # Uses default weight_kg
    "pieces": 1.0,
    "item": 1.0,
    "items": 1.0,
    "whole": 1.0,
    "slice": 0.3,       # ~30% of whole item
    "slices": 0.3,
    "head": 1.0,
    "bunch": 1.0,
    "clove": 0.1,       # ~10% of whole item (for garlic)
    "cloves": 0.1,
    "can": 0.4,         # ~400g typical can
    "cans": 0.4,
    "package": 0.5,     # ~500g typical package
    "packages": 0.5,
    "bag": 0.5,
    "bags": 0.5,
    "box": 0.4,
    "boxes": 0.4,
    "bottle": 0.5,
    "bottles": 0.5,
    "jar": 0.3,
    "jars": 0.3,
}

# Comprehensive ingredient lookup table
# Format: "normalized_name": {weight_kg, cost_usd, carbon_kg_co2e, category, aliases}
INGREDIENT_LOOKUP: Dict[str, IngredientData] = {
    # =========================================================================
    # PRODUCE - Vegetables
    # =========================================================================
    "tomato": {
        "weight_kg": 0.15,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 1.4,
        "category": "produce",
        "aliases": ["tomatoes", "roma tomato", "cherry tomato", "grape tomato"]
    },
    "onion": {
        "weight_kg": 0.15,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["onions", "yellow onion", "white onion", "red onion"]
    },
    "garlic": {
        "weight_kg": 0.05,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["garlic clove", "garlic cloves"]
    },
    "potato": {
        "weight_kg": 0.20,
        "cost_usd": 0.40,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["potatoes", "russet potato", "red potato", "yukon gold"]
    },
    "carrot": {
        "weight_kg": 0.10,
        "cost_usd": 0.30,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["carrots", "baby carrots"]
    },
    "broccoli": {
        "weight_kg": 0.30,
        "cost_usd": 1.75,
        "carbon_kg_co2e": 0.8,
        "category": "produce",
        "aliases": ["broccoli florets", "broccoli head"]
    },
    "spinach": {
        "weight_kg": 0.15,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["baby spinach", "spinach leaves"]
    },
    "lettuce": {
        "weight_kg": 0.25,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.7,
        "category": "produce",
        "aliases": ["romaine lettuce", "iceberg lettuce", "lettuce head"]
    },
    "bell pepper": {
        "weight_kg": 0.15,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 1.1,
        "category": "produce",
        "aliases": ["bell peppers", "red pepper", "green pepper", "yellow pepper", "capsicum"]
    },
    "cucumber": {
        "weight_kg": 0.20,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 0.7,
        "category": "produce",
        "aliases": ["cucumbers", "english cucumber"]
    },
    "celery": {
        "weight_kg": 0.40,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["celery stalks", "celery sticks"]
    },
    "mushroom": {
        "weight_kg": 0.10,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.8,
        "category": "produce",
        "aliases": ["mushrooms", "button mushrooms", "cremini", "portobello", "shiitake"]
    },
    "zucchini": {
        "weight_kg": 0.20,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 0.6,
        "category": "produce",
        "aliases": ["zucchinis", "courgette"]
    },
    "asparagus": {
        "weight_kg": 0.20,
        "cost_usd": 3.00,
        "carbon_kg_co2e": 1.0,
        "category": "produce",
        "aliases": ["asparagus spears"]
    },
    "corn": {
        "weight_kg": 0.20,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 1.0,
        "category": "produce",
        "aliases": ["corn on the cob", "sweet corn", "corn kernels"]
    },
    "cabbage": {
        "weight_kg": 0.50,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["green cabbage", "red cabbage", "napa cabbage"]
    },
    "cauliflower": {
        "weight_kg": 0.50,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 0.7,
        "category": "produce",
        "aliases": ["cauliflower head", "cauliflower florets"]
    },
    "green beans": {
        "weight_kg": 0.15,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 0.8,
        "category": "produce",
        "aliases": ["string beans", "snap beans"]
    },
    "peas": {
        "weight_kg": 0.15,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 0.8,
        "category": "produce",
        "aliases": ["green peas", "snow peas", "snap peas"]
    },
    "kale": {
        "weight_kg": 0.15,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["kale leaves", "baby kale"]
    },
    "avocado": {
        "weight_kg": 0.20,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 2.5,
        "category": "produce",
        "aliases": ["avocados"]
    },
    "eggplant": {
        "weight_kg": 0.35,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.8,
        "category": "produce",
        "aliases": ["aubergine", "eggplants"]
    },
    
    # =========================================================================
    # PRODUCE - Fruits
    # =========================================================================
    "apple": {
        "weight_kg": 0.18,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["apples", "green apple", "red apple", "gala apple", "fuji apple"]
    },
    "banana": {
        "weight_kg": 0.12,
        "cost_usd": 0.25,
        "carbon_kg_co2e": 0.9,
        "category": "produce",
        "aliases": ["bananas"]
    },
    "orange": {
        "weight_kg": 0.20,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["oranges", "navel orange"]
    },
    "lemon": {
        "weight_kg": 0.10,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["lemons", "lemon juice"]
    },
    "lime": {
        "weight_kg": 0.07,
        "cost_usd": 0.35,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["limes", "lime juice"]
    },
    "strawberry": {
        "weight_kg": 0.20,
        "cost_usd": 3.00,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["strawberries"]
    },
    "blueberry": {
        "weight_kg": 0.15,
        "cost_usd": 3.50,
        "carbon_kg_co2e": 0.6,
        "category": "produce",
        "aliases": ["blueberries"]
    },
    "grape": {
        "weight_kg": 0.25,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 0.7,
        "category": "produce",
        "aliases": ["grapes", "red grapes", "green grapes"]
    },
    "mango": {
        "weight_kg": 0.30,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 1.5,
        "category": "produce",
        "aliases": ["mangos", "mangoes"]
    },
    "pineapple": {
        "weight_kg": 1.0,
        "cost_usd": 3.00,
        "carbon_kg_co2e": 1.0,
        "category": "produce",
        "aliases": ["pineapples"]
    },
    "watermelon": {
        "weight_kg": 5.0,
        "cost_usd": 6.00,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["watermelons"]
    },
    "peach": {
        "weight_kg": 0.15,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["peaches"]
    },
    "pear": {
        "weight_kg": 0.18,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 0.4,
        "category": "produce",
        "aliases": ["pears"]
    },
    
    # =========================================================================
    # PROTEIN - Meat
    # =========================================================================
    "chicken breast": {
        "weight_kg": 0.17,
        "cost_usd": 3.50,
        "carbon_kg_co2e": 6.9,
        "category": "protein",
        "aliases": ["chicken breasts", "boneless chicken", "skinless chicken breast"]
    },
    "chicken thigh": {
        "weight_kg": 0.12,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 6.9,
        "category": "protein",
        "aliases": ["chicken thighs", "bone-in chicken thigh"]
    },
    "chicken": {
        "weight_kg": 0.15,
        "cost_usd": 3.00,
        "carbon_kg_co2e": 6.9,
        "category": "protein",
        "aliases": ["whole chicken", "chicken pieces"]
    },
    "ground beef": {
        "weight_kg": 0.25,
        "cost_usd": 5.00,
        "carbon_kg_co2e": 27.0,
        "category": "protein",
        "aliases": ["minced beef", "beef mince", "hamburger meat"]
    },
    "beef steak": {
        "weight_kg": 0.22,
        "cost_usd": 8.00,
        "carbon_kg_co2e": 27.0,
        "category": "protein",
        "aliases": ["steak", "ribeye", "sirloin", "filet mignon", "beef"]
    },
    "pork chop": {
        "weight_kg": 0.18,
        "cost_usd": 3.50,
        "carbon_kg_co2e": 12.1,
        "category": "protein",
        "aliases": ["pork chops", "pork loin"]
    },
    "ground pork": {
        "weight_kg": 0.25,
        "cost_usd": 4.00,
        "carbon_kg_co2e": 12.1,
        "category": "protein",
        "aliases": ["minced pork", "pork mince"]
    },
    "bacon": {
        "weight_kg": 0.15,
        "cost_usd": 5.00,
        "carbon_kg_co2e": 12.1,
        "category": "protein",
        "aliases": ["bacon strips", "streaky bacon"]
    },
    "sausage": {
        "weight_kg": 0.10,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 12.1,
        "category": "protein",
        "aliases": ["sausages", "italian sausage", "breakfast sausage"]
    },
    "ham": {
        "weight_kg": 0.10,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 12.1,
        "category": "protein",
        "aliases": ["sliced ham", "deli ham"]
    },
    "lamb": {
        "weight_kg": 0.20,
        "cost_usd": 10.00,
        "carbon_kg_co2e": 39.2,
        "category": "protein",
        "aliases": ["lamb chop", "lamb chops", "ground lamb"]
    },
    "turkey": {
        "weight_kg": 0.15,
        "cost_usd": 3.00,
        "carbon_kg_co2e": 10.9,
        "category": "protein",
        "aliases": ["turkey breast", "ground turkey", "deli turkey"]
    },
    
    # =========================================================================
    # PROTEIN - Seafood
    # =========================================================================
    "salmon": {
        "weight_kg": 0.17,
        "cost_usd": 6.00,
        "carbon_kg_co2e": 5.4,
        "category": "protein",
        "aliases": ["salmon fillet", "salmon filet", "smoked salmon"]
    },
    "tuna": {
        "weight_kg": 0.15,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 5.4,
        "category": "protein",
        "aliases": ["tuna steak", "canned tuna", "tuna fish"]
    },
    "shrimp": {
        "weight_kg": 0.15,
        "cost_usd": 6.00,
        "carbon_kg_co2e": 12.0,
        "category": "protein",
        "aliases": ["shrimps", "prawns", "jumbo shrimp"]
    },
    "cod": {
        "weight_kg": 0.17,
        "cost_usd": 5.00,
        "carbon_kg_co2e": 4.0,
        "category": "protein",
        "aliases": ["cod fillet", "atlantic cod"]
    },
    "tilapia": {
        "weight_kg": 0.15,
        "cost_usd": 4.00,
        "carbon_kg_co2e": 4.0,
        "category": "protein",
        "aliases": ["tilapia fillet"]
    },
    "crab": {
        "weight_kg": 0.15,
        "cost_usd": 12.00,
        "carbon_kg_co2e": 5.0,
        "category": "protein",
        "aliases": ["crab meat", "crab legs"]
    },
    
    # =========================================================================
    # PROTEIN - Eggs & Plant-based
    # =========================================================================
    "egg": {
        "weight_kg": 0.06,
        "cost_usd": 0.35,
        "carbon_kg_co2e": 4.8,
        "category": "protein",
        "aliases": ["eggs", "large egg", "large eggs"]
    },
    "tofu": {
        "weight_kg": 0.20,
        "cost_usd": 2.50,
        "carbon_kg_co2e": 2.0,
        "category": "protein",
        "aliases": ["firm tofu", "silken tofu", "extra firm tofu"]
    },
    "tempeh": {
        "weight_kg": 0.20,
        "cost_usd": 3.50,
        "carbon_kg_co2e": 1.0,
        "category": "protein",
        "aliases": []
    },
    "black beans": {
        "weight_kg": 0.25,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.8,
        "category": "protein",
        "aliases": ["canned black beans"]
    },
    "chickpeas": {
        "weight_kg": 0.25,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 0.8,
        "category": "protein",
        "aliases": ["garbanzo beans", "canned chickpeas"]
    },
    "lentils": {
        "weight_kg": 0.20,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 0.9,
        "category": "protein",
        "aliases": ["red lentils", "green lentils", "brown lentils"]
    },
    
    # =========================================================================
    # DAIRY
    # =========================================================================
    "milk": {
        "weight_kg": 0.24,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 3.2,
        "category": "dairy",
        "aliases": ["whole milk", "skim milk", "2% milk"]
    },
    "cheese": {
        "weight_kg": 0.10,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 13.5,
        "category": "dairy",
        "aliases": ["cheddar", "cheddar cheese", "swiss cheese", "mozzarella"]
    },
    "parmesan": {
        "weight_kg": 0.05,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 13.5,
        "category": "dairy",
        "aliases": ["parmesan cheese", "parmigiano reggiano", "grated parmesan"]
    },
    "butter": {
        "weight_kg": 0.05,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 12.0,
        "category": "dairy",
        "aliases": ["unsalted butter", "salted butter"]
    },
    "cream": {
        "weight_kg": 0.12,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 4.5,
        "category": "dairy",
        "aliases": ["heavy cream", "whipping cream", "half and half"]
    },
    "yogurt": {
        "weight_kg": 0.17,
        "cost_usd": 1.25,
        "carbon_kg_co2e": 2.5,
        "category": "dairy",
        "aliases": ["greek yogurt", "plain yogurt"]
    },
    "sour cream": {
        "weight_kg": 0.12,
        "cost_usd": 1.50,
        "carbon_kg_co2e": 3.0,
        "category": "dairy",
        "aliases": []
    },
    "cream cheese": {
        "weight_kg": 0.10,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 8.0,
        "category": "dairy",
        "aliases": ["philadelphia"]
    },
    
    # =========================================================================
    # GRAINS & STARCHES
    # =========================================================================
    "rice": {
        "weight_kg": 0.18,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 4.0,
        "category": "grains",
        "aliases": ["white rice", "brown rice", "jasmine rice", "basmati rice"]
    },
    "pasta": {
        "weight_kg": 0.15,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 1.5,
        "category": "grains",
        "aliases": ["spaghetti", "penne", "linguine", "fettuccine", "macaroni"]
    },
    "bread": {
        "weight_kg": 0.05,
        "cost_usd": 0.30,
        "carbon_kg_co2e": 1.5,
        "category": "grains",
        "aliases": ["white bread", "whole wheat bread", "bread slice", "bread slices"]
    },
    "flour": {
        "weight_kg": 0.12,
        "cost_usd": 0.25,
        "carbon_kg_co2e": 0.7,
        "category": "grains",
        "aliases": ["all-purpose flour", "wheat flour", "whole wheat flour"]
    },
    "oats": {
        "weight_kg": 0.08,
        "cost_usd": 0.40,
        "carbon_kg_co2e": 1.0,
        "category": "grains",
        "aliases": ["rolled oats", "oatmeal", "steel cut oats"]
    },
    "quinoa": {
        "weight_kg": 0.17,
        "cost_usd": 2.00,
        "carbon_kg_co2e": 1.2,
        "category": "grains",
        "aliases": []
    },
    "tortilla": {
        "weight_kg": 0.04,
        "cost_usd": 0.30,
        "carbon_kg_co2e": 1.2,
        "category": "grains",
        "aliases": ["tortillas", "flour tortilla", "corn tortilla", "wrap"]
    },
    "noodles": {
        "weight_kg": 0.15,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 1.5,
        "category": "grains",
        "aliases": ["egg noodles", "rice noodles", "ramen noodles", "udon"]
    },
    
    # =========================================================================
    # CONDIMENTS & OILS
    # =========================================================================
    "olive oil": {
        "weight_kg": 0.015,
        "cost_usd": 0.30,
        "carbon_kg_co2e": 3.5,
        "category": "condiments",
        "aliases": ["extra virgin olive oil", "evoo"]
    },
    "vegetable oil": {
        "weight_kg": 0.015,
        "cost_usd": 0.10,
        "carbon_kg_co2e": 3.0,
        "category": "condiments",
        "aliases": ["canola oil", "cooking oil"]
    },
    "soy sauce": {
        "weight_kg": 0.015,
        "cost_usd": 0.15,
        "carbon_kg_co2e": 1.0,
        "category": "condiments",
        "aliases": ["soya sauce", "tamari"]
    },
    "ketchup": {
        "weight_kg": 0.02,
        "cost_usd": 0.10,
        "carbon_kg_co2e": 1.5,
        "category": "condiments",
        "aliases": ["tomato ketchup", "catsup"]
    },
    "mustard": {
        "weight_kg": 0.015,
        "cost_usd": 0.10,
        "carbon_kg_co2e": 0.8,
        "category": "condiments",
        "aliases": ["dijon mustard", "yellow mustard"]
    },
    "mayonnaise": {
        "weight_kg": 0.015,
        "cost_usd": 0.15,
        "carbon_kg_co2e": 2.5,
        "category": "condiments",
        "aliases": ["mayo"]
    },
    "honey": {
        "weight_kg": 0.02,
        "cost_usd": 0.30,
        "carbon_kg_co2e": 0.5,
        "category": "condiments",
        "aliases": []
    },
    "sugar": {
        "weight_kg": 0.015,
        "cost_usd": 0.05,
        "carbon_kg_co2e": 1.0,
        "category": "condiments",
        "aliases": ["white sugar", "brown sugar", "granulated sugar"]
    },
    "salt": {
        "weight_kg": 0.005,
        "cost_usd": 0.02,
        "carbon_kg_co2e": 0.1,
        "category": "condiments",
        "aliases": ["table salt", "sea salt", "kosher salt"]
    },
    "pepper": {
        "weight_kg": 0.002,
        "cost_usd": 0.05,
        "carbon_kg_co2e": 0.5,
        "category": "condiments",
        "aliases": ["black pepper", "ground pepper"]
    },
    "vinegar": {
        "weight_kg": 0.015,
        "cost_usd": 0.10,
        "carbon_kg_co2e": 0.5,
        "category": "condiments",
        "aliases": ["white vinegar", "apple cider vinegar", "balsamic vinegar", "rice vinegar"]
    },
    "tomato sauce": {
        "weight_kg": 0.12,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 1.5,
        "category": "condiments",
        "aliases": ["marinara sauce", "pasta sauce", "tomato paste"]
    },
    
    # =========================================================================
    # HERBS & SPICES
    # =========================================================================
    "basil": {
        "weight_kg": 0.01,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.3,
        "category": "produce",
        "aliases": ["fresh basil", "basil leaves"]
    },
    "cilantro": {
        "weight_kg": 0.03,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 0.3,
        "category": "produce",
        "aliases": ["fresh cilantro", "coriander"]
    },
    "parsley": {
        "weight_kg": 0.03,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 0.3,
        "category": "produce",
        "aliases": ["fresh parsley", "italian parsley"]
    },
    "ginger": {
        "weight_kg": 0.05,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.5,
        "category": "produce",
        "aliases": ["fresh ginger", "ginger root"]
    },
    "rosemary": {
        "weight_kg": 0.01,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.3,
        "category": "produce",
        "aliases": ["fresh rosemary"]
    },
    "thyme": {
        "weight_kg": 0.01,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 0.3,
        "category": "produce",
        "aliases": ["fresh thyme"]
    },
    
    # =========================================================================
    # NUTS & SEEDS
    # =========================================================================
    "almonds": {
        "weight_kg": 0.03,
        "cost_usd": 0.75,
        "carbon_kg_co2e": 2.3,
        "category": "other",
        "aliases": ["almond", "sliced almonds"]
    },
    "peanuts": {
        "weight_kg": 0.03,
        "cost_usd": 0.40,
        "carbon_kg_co2e": 1.2,
        "category": "other",
        "aliases": ["peanut", "roasted peanuts"]
    },
    "walnuts": {
        "weight_kg": 0.03,
        "cost_usd": 1.00,
        "carbon_kg_co2e": 1.0,
        "category": "other",
        "aliases": ["walnut", "walnut pieces"]
    },
    "peanut butter": {
        "weight_kg": 0.03,
        "cost_usd": 0.50,
        "carbon_kg_co2e": 1.2,
        "category": "other",
        "aliases": []
    },
}


def get_ingredient_data(name: str) -> IngredientData:
    """
    Look up ingredient data by name, checking aliases.
    Returns default values if not found.
    
    Args:
        name: Ingredient name to look up
        
    Returns:
        IngredientData dict with weight_kg, cost_usd, carbon_kg_co2e, category
    """
    normalized = name.lower().strip()
    
    # Direct lookup
    if normalized in INGREDIENT_LOOKUP:
        return INGREDIENT_LOOKUP[normalized]
    
    # Check aliases
    for ingredient_name, data in INGREDIENT_LOOKUP.items():
        if normalized in [alias.lower() for alias in data.get("aliases", [])]:
            return data
    
    # Fuzzy match: check if name contains or is contained by any ingredient
    for ingredient_name, data in INGREDIENT_LOOKUP.items():
        if normalized in ingredient_name or ingredient_name in normalized:
            return data
        for alias in data.get("aliases", []):
            if normalized in alias.lower() or alias.lower() in normalized:
                return data
    
    # Return default if not found
    return DEFAULT_INGREDIENT.copy()


def get_unit_multiplier(unit: str, ingredient_name: str = "") -> float:
    """
    Get the weight multiplier for a given unit.
    For count-based units (piece, whole, etc.), uses the ingredient's default weight.
    
    Args:
        unit: The unit string (e.g., "cups", "pieces", "kg")
        ingredient_name: The ingredient name for context-specific conversions
        
    Returns:
        Multiplier to apply to quantity for weight calculation
    """
    normalized_unit = unit.lower().strip()
    
    # Check if it's a count-based unit
    count_units = {"piece", "pieces", "item", "items", "whole", "head", "bunch"}
    
    if normalized_unit in count_units:
        # For count units, the multiplier is 1.0 (use ingredient's weight_kg directly)
        return 1.0
    
    return UNIT_CONVERSIONS.get(normalized_unit, 1.0)


def get_all_ingredients() -> Dict[str, IngredientData]:
    """Return the full ingredient lookup dictionary."""
    return INGREDIENT_LOOKUP


def get_badge_thresholds() -> Dict[str, Dict[str, float]]:
    """Return badge threshold configuration."""
    return BADGE_THRESHOLDS


# List of all ingredient names for autocomplete/validation
INGREDIENT_NAMES: List[str] = list(INGREDIENT_LOOKUP.keys())
