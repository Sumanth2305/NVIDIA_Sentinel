import os
import time
import requests
from bs4 import BeautifulSoup
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

# The target URL pattern (We use a placeholder here for safety)
# In a real scenario, you would use: "https://nvidianews.nvidia.com/news?page={}"
BASE_URL = "https://nvidianews.nvidia.com/news?page="
START_PAGE = 1
MAX_PAGES = 5  # Increase this to 10, 20, or 50 for "Way More Data"

# Neo4j Connection
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

def clean_text(text):
    return text.strip().replace('"', "'")

def ingest_article(title, date, url, content):
    """
    Inserts a single article and runs the Entity Extraction Cypher immediately.
    """
    print(f"  └── Processing: {title[:30]}...")
    
    # 1. Create Article Node
    query_create = f"""
    MERGE (a:Article {{url: "{url}"}})
    SET a.title = "{clean_text(title)}",
        a.date = "{date}",
        a.text = "{clean_text(content[:1000])}..." 
    """
    graph.query(query_create)
    
    # 2. Extract Entities (The "Brain" Part)
    # This acts as a simple Named Entity Recognition (NER) using Cypher keyword matching
    # In a production app, you would use an LLM here, but this is faster for bulk data.
    query_extract = f"""
    MATCH (a:Article {{url: "{url}"}})
    
    # Find Companies
    FOREACH (company IN ['Nvidia', 'TSMC', 'Intel', 'AMD', 'ASML', 'Microsoft', 'Google', 'Meta'] | 
        FOREACH (_ IN CASE WHEN toLower(a.title) CONTAINS toLower(company) OR toLower(a.text) CONTAINS toLower(company) THEN [1] ELSE [] END |
            MERGE (c:Company {{id: company}})
            MERGE (c)-[:MENTIONED_IN]->(a)
        )
    )

    # Find Products
    FOREACH (product IN ['H100', 'Blackwell', 'Hopper', 'Grace CPU', 'RTX 4090', 'Rubin', 'CUDA'] | 
        FOREACH (_ IN CASE WHEN toLower(a.title) CONTAINS toLower(product) OR toLower(a.text) CONTAINS toLower(product) THEN [1] ELSE [] END |
            MERGE (p:Product {{id: product}})
            MERGE (p)-[:MENTIONED_IN]->(a)
            # Link Product to Nvidia automatically
            MERGE (n:Company {{id: 'Nvidia'}})
            MERGE (n)-[:PRODUCES]->(p)
        )
    )
    
    # Find Events
    FOREACH (event IN ['Earnings', 'Acquisition', 'Launch', 'Delay', 'Sanction', 'Partnership'] | 
        FOREACH (_ IN CASE WHEN toLower(a.title) CONTAINS toLower(event) OR toLower(a.text) CONTAINS toLower(event) THEN [1] ELSE [] END |
            MERGE (e:Event {{id: event}})
            MERGE (a)-[:REPORTED_EVENT]->(e)
        )
    )
    """
    graph.query(query_extract)

def crawl_news():
    print(f"🚀 Starting Massive Ingestion: {MAX_PAGES} Pages")
    
    for page_num in range(START_PAGE, MAX_PAGES + 1):
        target_url = f"{BASE_URL}{page_num}"
        print(f"\n📄 Scraping Page {page_num}: {target_url}")
        
        try:
            # Add headers to look like a real browser (Prevents blocking)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(target_url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed to retrieve page {page_num} (Status: {response.status_code})")
                continue

            soup = BeautifulSoup(response.text, 'lxml')
            
            # SELECTOR STRATEGY: Find all article cards
            # Note: These class names are specific to standard news layouts. 
            # If scraping a different site, inspect the HTML to find the right <div> class.
            articles = soup.find_all("div", class_="col-md-4") 

            if not articles:
                print("⚠️ No articles found. Checking alternative layout...")
                articles = soup.find_all("article")

            print(f"   Found {len(articles)} articles. Processing...")

            for article in articles:
                try:
                    # Extract Data
                    title_tag = article.find("h3") or article.find("h2") or article.find("a")
                    date_tag = article.find("time") or article.find("span", class_="date")
                    
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        link = title_tag.find("a")['href'] if title_tag.find("a") else article.find("a")['href']
                        
                        # Handle relative links
                        if link.startswith("/"):
                            link = "https://nvidianews.nvidia.com" + link
                            
                        date = date_tag.get_text(strip=True) if date_tag else "Unknown Date"
                        
                        # Ingest into Neo4j
                        ingest_article(title, date, link, title) # Using title as content summary for speed
                        
                except Exception as e:
                    continue # Skip bad articles without crashing
            
            # Be polite to the server
            time.sleep(2)

        except Exception as e:
            print(f"Critical Error on page {page_num}: {e}")

    print("\n✅ Ingestion Complete. Knowledge Graph Updated.")

if __name__ == "__main__":
    crawl_news()