import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Libraries
from newsapi import NewsApiClient
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
# FIX 1: Use the modern, non-deprecated library
from langchain_neo4j import Neo4jGraph
from langchain_core.documents import Document

# --- CONFIGURATION ---
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("ingestion.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Strict Schema Definition
ALLOWED_NODES = ["Company", "Person", "Location", "Event", "Product"]
ALLOWED_RELATIONSHIPS = [
    "SUPPLIES_TO", "COMPETES_WITH", "LOCATED_IN", 
    "AFFECTS", "HAS_CEO", "ANNOUNCED", "PARTNERS_WITH"
]

class NvidiaSentinelETL:
    def __init__(self):
        self._validate_env()
        self.news_api = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))
        
        # Connect to Neo4j
        self.graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        
        # FIX 2: Initialize Constraints specifically for Professional Data Integrity
        self._initialize_schema()

        # The Brain
        # Note: Swapped to gpt-4o-mini to save you money during dev. 
        # Swap back to "gpt-4o" for maximum precision if budget allows.
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
        
        self.transformer = LLMGraphTransformer(
            llm=self.llm,
            allowed_nodes=ALLOWED_NODES,
            allowed_relationships=ALLOWED_RELATIONSHIPS
        )

    def _validate_env(self):
        """Ensures all secrets are present."""
        required_keys = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "OPENAI_API_KEY", "NEWS_API_KEY"]
        missing = [key for key in required_keys if not os.getenv(key)]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {missing}")

    def _initialize_schema(self):
        """
        Creates constraints to ensure data integrity.
        This prevents duplicate Articles and silences 'Label not found' warnings.
        """
        logger.info("Initializing Graph Schema & Constraints...")
        try:
            self.graph.query("CREATE CONSTRAINT article_url IF NOT EXISTS FOR (a:Article) REQUIRE a.url IS UNIQUE")
            self.graph.query("CREATE INDEX article_date IF NOT EXISTS FOR (a:Article) ON (a.processed_at)")
        except Exception as e:
            logger.warning(f"Schema initialization warning (can often be ignored if constraints exist): {e}")

    def fetch_articles(self, days_back=30):
        """Fetches highly specific supply chain news."""
        query = "(Nvidia OR TSMC OR ASML) AND (supply OR shortage OR delay OR production OR tariff)"
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        logger.info(f"Fetching news for query: '{query}' since {from_date}")
        
        try:
            response = self.news_api.get_everything(
                q=query,
                from_param=from_date,
                language='en',
                sort_by='relevancy',
                page_size=100
            )
            articles = response.get('articles', [])
            logger.info(f"Fetched {len(articles)} articles.")
            return articles
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []

    def check_if_processed(self, url):
        """Idempotency Check."""
        query = "MATCH (a:Article {url: $url}) RETURN count(a) > 0 as exists"
        result = self.graph.query(query, params={"url": url})
        return result[0]['exists']

    def process_and_load(self, articles):
        documents = []
        
        for article in articles:
            url = article['url']
            title = article['title']
            content = f"{title}\n{article.get('description', '')}"
            
            if self.check_if_processed(url):
                logger.info(f"Skipping duplicate: {title[:30]}...")
                continue
            
            doc = Document(page_content=content, metadata={"source": "newsapi", "url": url, "title": title})
            documents.append(doc)

        if not documents:
            logger.warning("No new documents to process.")
            return

        logger.info(f"Extracting Knowledge Graph from {len(documents)} documents...")
        
        try:
            # 1. AI Extraction
            graph_documents = self.transformer.convert_to_graph_documents(documents)
            
            for i, graph_doc in enumerate(graph_documents):
                article_meta = documents[i].metadata
                
                # 2. Add the Entities/Relationships to DB
                self.graph.add_graph_documents([graph_doc])
                
                # FIX 3: THE "PRO" LINKING STEP
                # Connect the extracted entities back to the source Article.
                # This enables "Citations" in your final app.
                self.graph.query(
                    """
                    MERGE (a:Article {url: $url})
                    SET a.title = $title, a.processed_at = datetime()
                    WITH a
                    MATCH (n) WHERE n.id IN $node_ids
                    MERGE (n)-[:MENTIONED_IN]->(a)
                    """, 
                    params={
                        "url": article_meta["url"], 
                        "title": article_meta["title"],
                        "node_ids": [node.id for node in graph_doc.nodes]
                    }
                )

            logger.info(f"✅ Successfully ingested {len(documents)} articles into Neo4j.")
            
        except Exception as e:
            if "insufficient_quota" in str(e):
                logger.critical("🚨 OPENAI QUOTA EXCEEDED. Go to platform.openai.com/billing to add credits.")
            else:
                logger.error(f"Graph transformation failed: {e}")

if __name__ == "__main__":
    bot = NvidiaSentinelETL()
    news = bot.fetch_articles()
    bot.process_and_load(news)