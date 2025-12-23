import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 1. Load the secrets from .env
load_dotenv()

print("--- Level 0 Verification ---")

# Check OpenAI Key
if os.getenv("OPENAI_API_KEY"):
    print("✅ OpenAI Key found.")
else:
    print("❌ OpenAI Key MISSING.")

# Check NewsAPI Key
if os.getenv("NEWS_API_KEY"):
    print("✅ NewsAPI Key found.")
else:
    print("❌ NewsAPI Key MISSING.")

# Check Neo4j Connection
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("✅ Neo4j Database Connected successfully!")
except Exception as e:
    print(f"❌ Neo4j Connection FAILED: {e}")

print("----------------------------")