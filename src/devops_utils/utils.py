import sys


def input_confirm(message: str):
    """Wait for user input, loop until a valid user input"""
    _message = f"{message} y/n\n" if message else "Confirm operation? y/n\n"
    response = input(_message)
    while response.lower().strip() not in ("yes", "y", "n", "no"):
        response = input(f"Please, enter a valid input! {_message}\n")
    return response.startswith("y")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
