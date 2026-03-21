# Members CSV Reader

A simple Python script that reads a CSV file and displays the first and last name of each member.

## Requirements

- Python 3.x (no external dependencies)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Usage

```bash
# Use the default members.csv file
python read_members.py

# Use a custom CSV file
python read_members.py path/to/your/file.csv
```

## CSV Format

The CSV file must include the following columns:

| Column       | Description       |
|--------------|-------------------|
| `first_name` | Member's first name |
| `last_name`  | Member's last name  |

Example:

```
id,first_name,last_name,email,gender,ip_address
1,John,Doe,john@example.com,Male,192.168.1.1
```
