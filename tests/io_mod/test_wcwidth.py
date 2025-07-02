import pytest
from ploomber.io.wcwidth import wcswidth, wcwidth


@pytest.mark.parametrize(
    ("c", "expected"),
    [
        ("\0", 0),
        ("\n", -1),
        ("a", 1),
        ("1", 1),
        ("א", 1),
        ("\u200B", 0),  #noqa
        ("\u1ABE", 0),  #noqa
        ("\u0591", 0),
        ("🉐", 2),
        ("＄", 2),
    ],
)
def test_wcwidth(c: str, expected: int) -> None:
    assert wcwidth(c) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("", 0),
        ("hello, world!", 13),
        ("hello, world!\n", -1),
        ("0123456789", 10),
        ("שלום, עולם!", 11),
        ("שְבֻעָיים", 6),
        ("🉐🉐🉐", 6),
    ],
)
def test_wcswidth(s: str, expected: int) -> None:
    assert wcswidth(s) == expected
