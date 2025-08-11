# Sample consultancy profile for scoring
CONSULTANCY_PROFILE = {
    'sectors': ['roads', 'highways', 'traffic studies', 'transport planning', 'environmental', 'social impact'],
    'countries': ['Nigeria', 'Kenya', 'Egypt', 'South Africa', 'Morocco'],
    'keywords': ['design', 'supervision', 'impact assessment', 'planning', 'study']
}

def score_opportunity(opportunity):
    """
    Score opportunity (0-100) based on sector, country, and summary keyword match.
    """
    score = 0
    # Sector match (40%)
    if opportunity.get('sector'):
        for s in CONSULTANCY_PROFILE['sectors']:
            if s.lower() in opportunity['sector'].lower():
                score += 40
                break
    # Country match (30%)
    if opportunity.get('country'):
        for c in CONSULTANCY_PROFILE['countries']:
            if c.lower() in opportunity['country'].lower():
                score += 30
                break
    # Keyword in summary (30%)
    if opportunity.get('summary'):
        for k in CONSULTANCY_PROFILE['keywords']:
            if k.lower() in opportunity['summary'].lower():
                score += 30
                break
    return min(score, 100)

# Sample partner list (in real use, query DB)
PARTNERS = [
    {'name': 'Lagos Engineering Ltd', 'country': 'Nigeria', 'sector': 'roads', 'website': 'https://lagoseng.com'},
    {'name': 'Cairo Infra Partners', 'country': 'Egypt', 'sector': 'transport planning', 'website': 'https://cairoinfra.com'},
    {'name': 'Nairobi Civil Works', 'country': 'Kenya', 'sector': 'highways', 'website': 'https://nairobicivil.co.ke'},
    {'name': 'Casablanca Enviro', 'country': 'Morocco', 'sector': 'environmental', 'website': 'https://casablancaenviro.ma'},
    {'name': 'Cape Town Traffic', 'country': 'South Africa', 'sector': 'traffic studies', 'website': 'https://capetowntraffic.co.za'},
]

def find_partners(country, sector):
    """
    Return up to 3 partners matching country and sector.
    """
    matches = [p for p in PARTNERS if country.lower() in p['country'].lower() and sector.lower() in p['sector'].lower()]
    if len(matches) < 3:
        # Fallback: match by country only
        matches += [p for p in PARTNERS if country.lower() in p['country'].lower() and p not in matches]
    return matches[:3] 