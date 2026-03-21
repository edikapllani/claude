import csv
import argparse


def read_memebers(filepath):
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
    parser = argparse.ArgumentParser(description="Display first and last names from a members CSV file.")
    parser.add_argument("filepath", nargs="?", default="members.csv", help="Path to the CSV file (default: members.csv)")
    args = parser.parse_args()
    read_memebers(args.filepath)
