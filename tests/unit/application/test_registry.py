import pytest

from lucioles_processing.application.registry import BuildContext, Registry
from lucioles_processing.config import parse_chain_definition
from lucioles_processing.domain.run import Step
from tests.doubles import FakeBuilder, fake_registry, make_definition, raw_definition


def test_build_creates_all_components():
    comps = fake_registry().build(make_definition())
    assert isinstance(comps.builder, FakeBuilder)


def test_unknown_implementation_lists_alternatives():
    definition = parse_chain_definition(raw_definition(build={"use": "inconnue"}))
    with pytest.raises(ValueError, match=r"'inconnue' inconnue.*\['fake'\]"):
        fake_registry().build(definition)


def test_duplicate_registration():
    reg = Registry()
    reg.register(Step.FETCH, "a", lambda ctx: None)
    with pytest.raises(ValueError, match="déjà enregistrée"):
        reg.register(Step.FETCH, "a", lambda ctx: None)


def test_factory_receives_params_and_definition():
    seen = {}
    reg = fake_registry()
    reg._factories[Step.BUILD].clear()
    reg.register(Step.BUILD, "fake", lambda ctx: seen.update(p=dict(ctx.params), d=ctx.definition.name))
    reg.build(parse_chain_definition(raw_definition(build={"use": "fake", "params": {"k": 1}})))
    assert seen == {"p": {"k": 1}, "d": "demo"}


def test_require_missing_param():
    ctx = BuildContext(make_definition(), {}, Step.READ, "fake")
    with pytest.raises(ValueError, match="paramètre 'admin' manquant"):
        ctx.require("admin")


def test_require_present_param():
    ctx = BuildContext(make_definition(), {"admin": "x.gpkg"}, Step.READ, "fake")
    assert ctx.require("admin") == "x.gpkg"
