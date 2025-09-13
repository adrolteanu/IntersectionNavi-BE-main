import random

def generate_random_routes():
    """
    Generate 100 random routes for vehicles passing through the intersection.
    Adjust the candidate edge IDs below to match valid edges in your network (map-3.net.xml).
    """
    routes = []
    # Candidate entry and exit edges
    possible_entries = ['-178160266', '26314368#1', '813669391#1']
    possible_exits   = ['178160266', '26314368#2']
    
    for _ in range(100):
        entry = random.choice(possible_entries)
        exit_choice = random.choice(possible_exits)
        routes.append({"from": entry, "to": exit_choice})
    
    return routes
