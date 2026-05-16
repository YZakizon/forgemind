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
