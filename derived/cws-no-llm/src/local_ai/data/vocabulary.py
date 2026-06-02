"""
The master vocabulary script.

This script imports all individual vocabulary modules and combines them
into a single, structured dictionary called `ALL_VOCAB`.

This provides a centralized and organized way to access all vocabulary data.
"""

from .vocab import (
    ambience,
    artifacts,
    attributes,
    biology,
    body,
    celestial,
    concepts,
    cosmology,
    consumables,
    culture,
    feelings,
    imagery,
    locations,
    medicine,
    metaphysical,
    mythology,
    personas,
    philosophy,
    qualities,
    sect_details,
    sociology,
    states,
    techniques,
    tribulations,
    verbs,
    visuals,
)

# Helper to inspect and collect vocab dictionaries from a module
def _collect_from(module):
    """Collects all uppercase dictionary and list variables from a module."""
    return {
        key: value
        for key, value in vars(module).items()
        if key.isupper() and isinstance(value, (dict, list))
    }

# Combine all vocabularies into a single structured dictionary
# Grouped by their original module name for clarity
ALL_VOCAB = {
    "ambience": _collect_from(ambience),
    "artifacts": _collect_from(artifacts),
    "attributes": _collect_from(attributes),
    "biology": _collect_from(biology),
    "body": _collect_from(body),
    "celestial": _collect_from(celestial),
    "concepts": _collect_from(concepts),
    "cosmology": _collect_from(cosmology),
    "consumables": _collect_from(consumables),
    "culture": _collect_from(culture),
    "feelings": _collect_from(feelings),
    "imagery": _collect_from(imagery),
    "locations": _collect_from(locations),
    "medicine": _collect_from(medicine),
    "metaphysical": _collect_from(metaphysical),
    "mythology": _collect_from(mythology),
    "personas": _collect_from(personas),
    "philosophy": _collect_from(philosophy),
    "qualities": _collect_from(qualities),
    "sect_details": _collect_from(sect_details),
    "sociology": _collect_from(sociology),
    "states": _collect_from(states),
    "techniques": _collect_from(techniques),
    "tribulations": _collect_from(tribulations),
    "verbs": _collect_from(verbs),
    "visuals": _collect_from(visuals),
}

def get_vocab():
    """Returns the complete vocabulary dictionary."""
    return ALL_VOCAB

def get_flat_vocab(category):
    """
    Returns a flat list of all vocabulary words for a given top-level category.
    Example: get_flat_vocab("artifacts")
    """
    words = []
    if category in ALL_VOCAB:
        for vocab_dict in ALL_VOCAB[category].values():
            if isinstance(vocab_dict, list):
                words.extend(vocab_dict)
            elif isinstance(vocab_dict, dict):
                for value in vocab_dict.values():
                    if isinstance(value, list):
                        words.extend(value)
                    elif isinstance(value, str):
                        words.append(value)
    return list(set(words))
