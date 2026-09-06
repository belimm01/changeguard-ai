import changeguard


def test_package_is_importable() -> None:
    assert changeguard.__package__ == "changeguard"
