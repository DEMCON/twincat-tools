import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="tctools",
        description="Use either `tctools.format` or `tctools.xml_sorter`",
    )

    parser.print_help()
