import random
from .schemas import Meal, PlanData

DISCLAIMER = 'Educational general-wellness example only. Nutrition values are approximate; consult a qualified professional for medical or dietary needs.'
FACTORS = {'sedentary':1.2,'light':1.375,'moderate':1.55,'active':1.725,'very_active':1.9}
MEALS = {
'breakfast': [
 ('Cinnamon rice and banana bowl',420,8,82,7,'vegan',[],['rice','banana','cinnamon','sunflower seeds']),
 ('Oats with banana and seeds',430,14,67,13,'vegan',['gluten'],['oats','banana','chia seeds']),
 ('Tofu vegetable scramble',420,24,32,21,'vegan',['soy'],['tofu','tomato','spinach','whole grain bread']),
 ('Greek yogurt fruit bowl',410,25,52,11,'vegetarian',['dairy'],['yogurt','berries','oats']),
 ('Egg and avocado toast',440,21,41,21,'omnivore',['eggs','gluten'],['egg','avocado','bread'])],
'lunch': [
 ('Chickpea rice bowl',590,22,92,14,'vegan',[],['chickpeas','rice','spinach']),
 ('Lentil quinoa salad',570,26,78,16,'vegan',[],['lentils','quinoa','cucumber']),
 ('Paneer vegetable wrap',610,29,66,26,'vegetarian',['dairy','gluten'],['paneer','vegetables','wheat wrap']),
 ('Chicken brown rice bowl',610,42,70,16,'omnivore',[],['chicken','brown rice','broccoli'])],
'snack': [
 ('Fruit and pumpkin seeds',220,7,32,8,'vegan',[],['apple','pumpkin seeds']),
 ('Carrot sticks and hummus',210,7,28,8,'vegan',['sesame'],['carrot','chickpeas','tahini']),
 ('Yogurt and berries',200,12,28,5,'vegetarian',['dairy'],['yogurt','berries']),
 ('Boiled egg and fruit',210,10,23,9,'omnivore',['eggs'],['egg','orange'])],
'dinner': [
 ('Bean sweet potato bowl',530,21,83,12,'vegan',[],['black beans','sweet potato','lettuce']),
 ('Tofu stir fry',520,28,56,21,'vegan',['soy'],['tofu','vegetables','rice']),
 ('Vegetable lentil pasta',540,23,82,13,'vegetarian',['gluten'],['pasta','lentils','tomato']),
 ('Grilled fish with potatoes',550,38,54,20,'omnivore',['fish'],['fish','potatoes','green beans'])]
}
FORBIDDEN = {
 'vegan': ['meat','chicken','beef','pork','fish','salmon','tuna','shrimp','egg','milk','cheese','yogurt','paneer','butter','honey','ghee','cream','whey'],
 'vegetarian': ['meat','chicken','beef','pork','fish','salmon','tuna','shrimp','gelatin','egg']
}
ALLERGEN_TERMS = {
 'nuts':['nut','nuts','almond','walnut','cashew','pecan','pistachio','hazelnut','nut butter'],
 'peanuts':['peanut','groundnut'], 'dairy':['milk','cheese','paneer','yogurt','butter','ghee','cream','whey'],
 'eggs':['egg'], 'soy':['soy','tofu','tempeh','edamame'],
 'gluten':['wheat','bread','pasta','oats','barley','rye','wrap'],
 'sesame':['sesame','tahini'], 'shellfish':['shrimp','prawn','crab','lobster'],
 'fish':['fish','salmon','tuna']
}

def targets(user):
    bmr=10*user.weight+6.25*user.height-5*user.age+(5 if user.sex=='male' else -161)
    tdee=bmr*FACTORS[user.activity_level]
    multiplier={'weight_management':.85,'balanced':1,'fitness':1.10}[user.goal]
    calories=round(max(1500 if user.sex=='male' else 1200,tdee*multiplier))
    split={'weight_management':(.30,.40,.30),'balanced':(.25,.50,.25),'fitness':(.30,.45,.25)}[user.goal]
    return {'bmr':round(bmr),'tdee':round(tdee),'calories':calories,'protein':round(calories*split[0]/4),'carbs':round(calories*split[1]/4),'fat':round(calories*split[2]/9)}

def allowed(meal, user):
    diet=meal[5]
    return (user.dietary_preference=='omnivore' or diet=='vegan' or (user.dietary_preference=='vegetarian' and diet=='vegetarian')) and not (set(meal[6]) & set(user.allergies or [])) and not unsafe_text(meal[0]+' '+' '.join(meal[7]), user)

def unsafe_text(text,user):
    import re
    value=text.lower()
    terms=FORBIDDEN.get(user.dietary_preference,[])+[term for a in user.allergies or [] for term in ALLERGEN_TERMS[a]]
    return next((term for term in terms if re.search(r'(?<![a-z])'+re.escape(term)+r'(?:s)?(?![a-z])',value)), None)

def rule_plan(user, t, rng=None):
    rng=rng or random.Random()
    result={}
    for name, proportion in [('breakfast',.25),('lunch',.35),('snack',.10),('dinner',.30)]:
        choices=[x for x in MEALS[name] if allowed(x,user)]
        if not choices: raise ValueError(f'No safe {name} choices match the profile')
        need=t['calories']*proportion
        ranked=sorted(choices,key=lambda m:abs(m[1]-need)+abs(m[2]-t['protein']*proportion)*2)
        x=rng.choice(ranked[:3]); scale=max(.65,min(1.65,need/x[1]))
        result[name]=Meal(name=x[0],calories=round(x[1]*scale),protein=round(x[2]*scale,1),carbs=round(x[3]*scale,1),fat=round(x[4]*scale,1),diet=x[5],allergens=x[6],ingredients=x[7]).model_dump()
    return assemble(result,t,'rule-based')

def assemble(meals,t,source,reason=None):
    keys=('breakfast','lunch','snack','dinner')
    summary={k:round(sum(meals[m][k] for m in keys),1) for k in ('calories','protein','carbs','fat')}
    return PlanData(**meals,nutrition_summary=summary,targets=t,hydration='Drink water regularly; needs vary with activity and climate.',source=source,disclaimer=DISCLAIMER,fallback_reason=reason).model_dump()

def validate_ai(meals,user,t):
    cleaned={}
    for label in ('breakfast','lunch','snack','dinner'):
        if label not in meals: raise ValueError(f'Missing {label}')
        meal=Meal.model_validate(meals[label])
        if user.dietary_preference=='vegan' and meal.diet!='vegan' or user.dietary_preference=='vegetarian' and meal.diet=='omnivore':
            raise ValueError(f'{label} violates dietary rules')
        if set(meal.allergens) & set(user.allergies or []): raise ValueError(f'{label} contains declared allergen')
        term=unsafe_text(meal.name+' '+' '.join(meal.ingredients),user)
        if term: raise ValueError(f'{label} violates dietary rules (found {term})')
        cleaned[label]=meal.model_dump()
    if abs(sum(m['calories'] for m in cleaned.values())-t['calories'])>t['calories']*.25:
        raise ValueError('AI calories outside target tolerance')
    return cleaned
