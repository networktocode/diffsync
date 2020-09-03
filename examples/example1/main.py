from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC


def main():

    a = BackendA()
    a.init()

    b = BackendB()
    b.init()

    c = BackendC()
    c.init()

    diff_a_b = a.diff(b)
    diff_a_b.print_detailed()


if __name__ == "__main__":
    main()
