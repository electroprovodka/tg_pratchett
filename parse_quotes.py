import csv
from uuid import uuid4

RAW_QUOTES = "./raw_quotes.txt"
PARSED_QUOTES = "./quotes.csv"

with open(RAW_QUOTES, "r") as f:
    raw_quotes = f.readlines()

with open(PARSED_QUOTES, "w") as df:
    writer = csv.DictWriter(df, fieldnames=["id", "quote_text"], quoting=csv.QUOTE_ALL, skipinitialspace=True)
    writer.writeheader()
    for raw_quote in raw_quotes:
        writer.writerow({"id": str(uuid4()), "quote_text": raw_quote.strip()})
