import csv
import argparse

def read_memebers(filepath: str = "members.csv") -> None:
    """Read a CSV file and print the first and last name of each member.

    The CSV file must contain 'first_name' and 'last_name' columns.
    Extra columns (e.g. id, email, gender, ip_address) are ignored.

    Args:
        filepath: Path to the CSV file. Defaults to 'members.csv'.

    Returns:
        None. Prints each member's full name to stdout.

    Raises:
        Does not raise — all errors are caught and printed to stdout.

    Example:
        >>> from read_members import read_memebers
        >>> read_memebers("members.csv")
        John Doe
        Jane Smith
    """
    try:
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(row["first_name"], row["last_name"])
    except FileNotFoundError:
        print(f"Error: '{filepath}' file not found.")
    except PermissionError:
        print(f"Error: Permission denied — cannot read '{filepath}'.")
    except KeyError as e:
        print(f"Error: Missing expected column {e} in '{filepath}'.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Display first and last names from a members CSV file."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default="members.csv",
        help="Path to the CSV file (default: members.csv)",
    )
    args = parser.parse_args()
    read_memebers(args.filepath)
