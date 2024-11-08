import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="tctools",
        description="Use either any of [`tctools.format`, `tctools.git_info`, "
        "`tctools.make_release`, `tctools.xml_sorter`]",
    )

    parser.print_help()
