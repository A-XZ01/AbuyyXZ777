import sqlite3

conn = sqlite3.connect('data/bot_database.db')
cursor = conn.cursor()

# Check recent tickets
cursor.execute('SELECT id, ticket_number, status, proof_hash FROM tickets ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
print('Recent 5 tickets:')
for row in rows:
    hash_preview = row[3][:16] + '...' if row[3] else 'NULL'
    print(f'  ID: {row[0]}, Ticket: #{row[1]:04d}, Status: {row[2]}, Hash: {hash_preview}')

print('\n' + '='*50 + '\n')

# Check tickets with hash
cursor.execute('SELECT COUNT(*) FROM tickets WHERE proof_hash IS NOT NULL')
count = cursor.fetchone()[0]
print(f'Total tickets with hash: {count}')

conn.close()
