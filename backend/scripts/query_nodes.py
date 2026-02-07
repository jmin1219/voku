import kuzu

db = kuzu.Database("./data/voku.db", read_only=True)
conn = kuzu.Connection(db)

result = conn.execute(
    "MATCH (n:LeafNode) RETURN n.id, n.content, n.node_purpose LIMIT 10"
)
print("LeafNodes in database:")
for row in result.get_all():
    print(f"  ID: {row[0]}")
    print(f"  Content: {row[1]}")
    print(f"  Purpose: {row[2]}")
    print()
