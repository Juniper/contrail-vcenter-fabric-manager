from cvfm.models import Model


def test_ne():
    m1 = Model(uuid="uuid-1")
    m2 = Model(uuid="uuid-2")

    assert m1 != m2


def test_eq():
    m1 = Model(uuid="uuid-1")
    m2 = Model(uuid="uuid-1")

    assert m1 == m2


def test_hash():
    m1 = Model(uuid="uuid-1")
    m2 = Model(uuid="uuid-1")

    assert m1 == m2
    assert len({m1, m2}) == 1
