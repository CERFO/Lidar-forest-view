def _tree_data_match(a, b):
    """Compare deux dicts tree_data. Utilise No_tige si présent, sinon égalité."""
    if not a or not b:
        return a == b
    if 'No_tige' in a and 'No_tige' in b:
        return a.get('No_tige') == b.get('No_tige')
    return a == b
