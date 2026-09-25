import httpx
from .config import settings
from .planner import rule_plan, targets, validate_ai, assemble

async def generate(user):
    t=targets(user)
    if not settings.ai_api_url or not settings.ai_api_key: return rule_plan(user,t)
    try:
        prompt=(f'Create one day of meals as JSON object with breakfast, lunch, snack, dinner. '
                f'Each meal requires name, calories, protein, carbs, fat, ingredients, diet, allergens. '
                f'Calorie target {t["calories"]}; dietary preference {user.dietary_preference}; '
                f'allergies {user.allergies}; cuisines {user.cuisines}. Do not include identifying details.')
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.post(settings.ai_api_url,headers={'Authorization':f'Bearer {settings.ai_api_key}'},json={
                'model':settings.ai_model,'temperature':.4,'response_format':{'type':'json_object'},
                'messages':[{'role':'system','content':'Return only valid JSON with the four requested meals. Do not suggest forbidden ingredients.'},
                            {'role':'user','content':prompt}]})
            response.raise_for_status()
            import json
            raw=json.loads(response.json()['choices'][0]['message']['content'])
        return assemble(validate_ai(raw,user,t),t,'ai:'+settings.ai_model)
    except Exception as exc:
        reason=f'AI service unavailable or unsafe response: {type(exc).__name__}'
        return {**rule_plan(user,t),'fallback_reason':reason}
