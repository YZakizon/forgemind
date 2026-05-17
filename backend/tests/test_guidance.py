from app.services.guidance import build_guidance_prompt_block, retrieve_guidance


def test_retrieve_guidance_matches_topic_tags():
    rules = retrieve_guidance("I am furious and angry after work")
    assert rules
    assert rules[0].topic == "anger"


def test_guidance_prompt_is_compact_and_rule_based():
    rules = retrieve_guidance("I cannot sleep tonight")
    block = build_guidance_prompt_block(rules)
    assert "Approved guidance" in block
    assert "sleep" in block
    assert "Do:" in block


def test_guidance_covers_required_relationship_and_pressure_topics():
    messages = {
        "anxiety": "I am anxious and overthinking everything",
        "divorce": "This divorce and custody pressure is crushing me",
        "dating": "I got ghosted after a date and want to text back",
        "wedding stress": "Wedding planning with my fiance is too much",
        "loneliness": "I feel lonely and disconnected from everyone",
        "fatherhood": "Being a dad is wearing me down",
        "family conflict": "My family argument is still in my head",
    }
    for expected_topic, message in messages.items():
        assert retrieve_guidance(message)[0].topic == expected_topic
