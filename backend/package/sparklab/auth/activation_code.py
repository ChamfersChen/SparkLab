import secrets
import string

_CODE_CHARS = string.ascii_uppercase.translate(str.maketrans("", "", "IO")) + string.digits.translate(
    str.maketrans("", "", "01")
)


def generate_code() -> str:
    parts = ["".join(secrets.choice(_CODE_CHARS) for _ in range(4)) for _ in range(3)]
    return "-".join(parts)
