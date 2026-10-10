import pytest

from ghat_guide import prompts


@pytest.mark.parametrize("lang,name", [("hi", "Hindi"), ("bho", "Bhojpuri"), ("mai", "Maithili")])
def test_system_prompts_name_language(lang, name):
    assert name in prompts.sys_explain(lang)
    assert name in prompts.sys_ritual(lang)


def test_unknown_language():
    with pytest.raises(ValueError):
        prompts.sys_explain("en")


def test_user_templates_fill():
    assert "घाट 5" in prompts.user_explain("घाट 5")
    u = prompts.user_ritual("[a#b]\nnote", "सवाल?")
    assert "<notes>" in u and "सवाल?" in u


@pytest.mark.parametrize("schema", [prompts.TRANSCRIBE_SCHEMA, prompts.EXPLAIN_SCHEMA, prompts.RITUAL_SCHEMA])
def test_schema_required_keys_are_properties(schema):
    assert set(schema["required"]) <= set(schema["properties"])
