"""Main executable for DSync "example1"."""

from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC


def main():
    """Demonstrate DSync behavior using the example backends provided."""
    # pylint: disable=invalid-name

    a = BackendA(name="Backend-A")
    a.load()

    b = BackendB(name="Backend-B")
    b.load()

    c = BackendC()
    c.load()

    diff_a_b = a.diff_to(b)
    diff_a_b.print_detailed()

    a.sync_to(b)
    a.diff_to(b).print_detailed()


if __name__ == "__main__":
    main()
