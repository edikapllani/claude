import unittest
from unittest.mock import patch, mock_open
from io import StringIO
from read_members import read_memebers


VALID_CSV = "first_name,last_name\nJohn,Doe\nJane,Smith\n"
MISSING_COLUMN_CSV = "first_name\nJohn\n"


class TestReadMemebers(unittest.TestCase):

    def test_prints_names(self):
        """Prints first and last name for each row."""
        with patch("builtins.open", mock_open(read_data=VALID_CSV)):
            with patch("builtins.print") as mock_print:
                read_memebers("members.csv")
                mock_print.assert_any_call("John", "Doe")
                mock_print.assert_any_call("Jane", "Smith")

    def test_file_not_found(self):
        """Prints an error message when the file does not exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("builtins.print") as mock_print:
                read_memebers("missing.csv")
                mock_print.assert_called_once_with("Error: 'missing.csv' file not found.")

    def test_permission_error(self):
        """Prints an error message when the file cannot be read."""
        with patch("builtins.open", side_effect=PermissionError):
            with patch("builtins.print") as mock_print:
                read_memebers("members.csv")
                mock_print.assert_called_once_with(
                    "Error: Permission denied — cannot read 'members.csv'."
                )

    def test_missing_column(self):
        """Prints an error message when a required column is missing."""
        with patch("builtins.open", mock_open(read_data=MISSING_COLUMN_CSV)):
            with patch("builtins.print") as mock_print:
                read_memebers("members.csv")
                args = mock_print.call_args[0][0]
                self.assertIn("Missing expected column", args)

    def test_default_filepath(self):
        """Uses members.csv as the default file path."""
        with patch("builtins.open", mock_open(read_data=VALID_CSV)) as mock_file:
            read_memebers()
            mock_file.assert_called_once_with("members.csv", newline="")


if __name__ == "__main__":
    unittest.main()
