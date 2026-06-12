from core.security import hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    plain = "SecurePassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False
