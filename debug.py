import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

print("\n🔍 INSPECTING TSMC CONNECTIONS...")

# Find ANYTHING connected to TSMC
query = """
MATCH (n)-[r]-(target)
WHERE toLower(n.id) CONTAINS 'tsmc'
RETURN type(r) as Relationship, labels(target) as Type, target.id as Name
LIMIT 20
"""

results = graph.query(query)

if not results:
    print("❌ No connections found for TSMC. (Maybe it's named 'Taiwan Semiconductor'?)")
else:
    for row in results:
        print(f"TSMC --[{row['Relationship']}]-- {row['Name']} ({row['Type']})")