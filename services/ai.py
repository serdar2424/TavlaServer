ai_names = ['ai_easy', 'ai_medium', 'ai_hard']
ai_rating = [1200, 1500, 1800]

def is_ai(username: str) -> bool:
    return username in ai_names