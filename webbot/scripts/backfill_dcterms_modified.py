import sqlite3, re, sys

DB_PATH = '/home/hongb/.openclaw/workspace/webbot/app/webbot.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

PREFIX = '<meta name="dcterms.modified" title="W3CDTF" content="'
PREFIX_LEN = len(PREFIX)

REGEX = re.compile(
    r'<meta\s+name=[\"\']dcterms\.modified[\"\']\s+title=[\"\']W3CDTF[\"\']\s+content=[\"\']([^\"\']+)[\"\']',
    re.I
)

# Step 1: Verify extraction (same as before)
print("=== Verifying extraction ===")
cur = conn.execute("""
    SELECT id, path, content FROM webbot_page
    WHERE content LIKE '%dcterms.modified%'
      AND INSTR(content, ?) > 0
    LIMIT 100
""", (PREFIX,))
errors = 0
ok = 0
for row in cur:
    m = REGEX.search(row['content'])
    if not m:
        errors += 1
        continue
    instr_pos = row['content'].find(PREFIX)
    if instr_pos == -1:
        errors += 1
        continue
    sql_date = row['content'][instr_pos + PREFIX_LEN:instr_pos + PREFIX_LEN + 10]
    if sql_date == m.group(1):
        ok += 1
    else:
        errors += 1
        print(f"  MISMATCH: {row['path'][:40]}: py='{sql_date}' regex='{m.group(1)}'")

print(f"  Correct: {ok}, Errors: {errors}/{ok+errors}")
if errors > 0 or ok == 0:
    print("FAIL")
    sys.exit(1)
print("OK\n")

# Step 2: Convert date-only to full datetime (YYYY-MM-DDT00:00:00)
# so frontend date parsing doesn't get confused by timezone
# Read all matching rows, extract date, prepend T00:00:00, update
print("=== Updating (Python loop - converts to full datetime) ===")
cur = conn.execute("""
    SELECT id, path, 
           SUBSTR(content, INSTR(content, ?) + ?, 10) AS meta_date
    FROM webbot_page
    WHERE content LIKE '%dcterms.modified%'
      AND INSTR(content, ?) > 0
      AND SUBSTR(content, INSTR(content, ?) + ?, 10)
          BETWEEN '2025-01-01' AND '2027-12-31'
""", (PREFIX, PREFIX_LEN, PREFIX, PREFIX, PREFIX_LEN))

rows = cur.fetchall()
update_count = 0
for row in rows:
    date_only = row['meta_date']
    # Convert to ISO datetime string
    new_lm = f"{date_only}T12:00:00"  # noon UTC to avoid date edge cases
    conn.execute("UPDATE webbot_page SET last_modified = ? WHERE id = ?",
                 (new_lm, row['id']))
    update_count += 1

conn.commit()
print(f"  Updated: {update_count} rows")

# Show results
print("\n=== Sample results ===")
cur = conn.execute("""
    SELECT path, last_modified FROM webbot_page
    WHERE content LIKE '%dcterms.modified%'
    LIMIT 5
""")
for row in cur:
    print(f"  {row['path'][:55]:55s} last_modified={row['last_modified']}")

print("\nDone")
