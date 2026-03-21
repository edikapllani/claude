# Members CSV Reader

A lightweight Python utility to read a CSV file and display the first and last name of each member. Can be used as a CLI tool or imported as a library in your own Python application.

## Install

**Directly from GitHub:**

```bash
pip install git+https://github.com/edikapllani/claude.git
```

**Or clone and install locally:**

```bash
git clone https://github.com/edikapllani/claude.git
cd claude
pip install .
```

## Requirements

- Python 3.8 or higher
- No external dependencies — uses the Python standard library only

## CLI Usage

```bash
# Use the default members.csv in the current directory
python read_members.py

# Use a custom CSV file
python read_members.py path/to/your/file.csv

# After installing the package, use the shorthand command
read-members path/to/your/file.csv
```

## Integration — Use as a Library

Import the function directly into your application:

```python
from read_members import read_memebers

# Use the default members.csv
read_memebers()

# Use a custom file path
read_memebers("path/to/your/file.csv")
```

## CSV Format

The CSV file must include at minimum the following columns (column order does not matter):

| Column       | Required | Description          |
|--------------|----------|----------------------|
| `first_name` | Yes      | Member's first name  |
| `last_name`  | Yes      | Member's last name   |

Additional columns (e.g. `id`, `email`, `gender`, `ip_address`) are ignored.

**Example CSV:**

```
id,first_name,last_name,email,gender,ip_address
1,John,Doe,john@example.com,Male,192.168.1.1
2,Jane,Smith,jane@example.com,Female,192.168.1.2
```

## Error Handling

The utility handles the following error cases gracefully (no exceptions bubble up):

| Scenario                        | Output                                      |
|---------------------------------|---------------------------------------------|
| File not found                  | `Error: 'file.csv' file not found.`         |
| No read permission              | `Error: Permission denied — cannot read...` |
| Missing `first_name`/`last_name`| `Error: Missing expected column '...'`      |
| Any other unexpected error      | `Unexpected error: <details>`               |

## Function Reference

```python
def read_memebers(filepath: str = "members.csv") -> None
```

| Parameter  | Type  | Default        | Description                  |
|------------|-------|----------------|------------------------------|
| `filepath` | `str` | `"members.csv"`| Path to the CSV file to read |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.
