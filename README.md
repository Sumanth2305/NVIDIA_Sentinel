# 🕸️ NVIDIA Sentinel: Supply Chain Intelligence Agent

**NVIDIA Sentinel** is an AI-powered Agentic Intelligence system designed to map and monitor the complex dependencies of the global semiconductor supply chain. By utilizing **GraphRAG** (Knowledge Graphs + RAG), Sentinel uncovers "multi-hop" risks that traditional vector-based search engines miss.



## 🚀 The Core Innovation
Traditional RAG finds "similar text." **Sentinel** understands "relationships." 
If a user asks about a drought in Taiwan, Sentinel doesn't just find articles about water; it traverses the graph: 
`[Taiwan Drought] -> [TSMC Fabrication] -> [NVIDIA Blackwell Series] -> [Revenue Impact]`.

---

## ✨ Key Features
* **Agentic Intent Routing:** Automatically distinguishes between general chat and complex data queries using `LangChain`.
* **Text-to-Cypher Engine:** Translates natural language into verified Neo4j queries with built-in hallucination guards.
* **Automated Knowledge Ingestion:** A specialized ETL pipeline that scrapes news (NewsAPI/BeautifulSoup) and extracts entities via `LLMGraphTransformer`.
* **Interactive Visualizer:** A "Neural Grid" UI built with Streamlit and Glassmorphism CSS for real-time graph exploration.
* **Pro-Level Citations:** Every insight generated is linked directly back to its source article node via `[:MENTIONED_IN]` relationships.

---

## 🛠️ Tech Stack
* **Orchestration:** LangChain (Agents & Chains)
* **LLM:** OpenAI GPT-4o / GPT-4o-mini
* **Database:** Neo4j AuraDB (Graph)
* **Frontend:** Streamlit + Custom Glassmorphism CSS
* **Inference:** Python 3.10+

---

