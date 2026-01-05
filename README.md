# NVIDIA Sentinel: Supply Chain Intelligence Agent

**NVIDIA Sentinel** is an AI-powered Agentic Intelligence system designed to map and monitor the complex dependencies of the semiconductor supply chain of NVIDIA. By utilizing **GraphRAG** (Knowledge Graphs + RAG), Sentinel uncovers "multi-hop" risks that traditional vector-based search engines miss.


## Demo

https://github.com/user-attachments/assets/0d67124b-93c7-4a9f-8bcc-0e3c49315243

---

## The Core Innovation
Traditional RAG finds "similar text." **Sentinel** understands "relationships." 
If a user asks about a drought in Taiwan, Sentinel doesn't just find articles about water; it traverses the graph: 
`[Taiwan Drought] -> [TSMC Fabrication] -> [NVIDIA Blackwell Series] -> [Revenue Impact]`.

---

## What I Built (and Learned)

Instead of a standard RAG pipeline, I implemented **Graph RAG**. Here’s the workflow I engineered:

*   **Autonomous Ingestion:** I used the NewsAPI to scrape unstructured news specifically related to NVIDIA.
*   **The "Brain" (Agentic Architecture):** I implemented a semantic router using `LangChain` that intelligently directs traffic. It differentiates between general chatter and complex data queries, ensuring cost-efficiency.
*   **Text-to-Cypher with Transparency:** The model translates natural language into Neo4j Cypher queries. Crucially, I built it to be **"White-Box"**—it shows the generated code to the user, ensuring trust and explainability for enterprise analysts. It traverses the graph to find multi-hop answers.
---

## Key Features
* **Agentic Intent Routing:** Automatically distinguishes between general chat and complex data queries using `LangChain`.
* **Text-to-Cypher Engine:** Translates natural language into verified Neo4j queries with built-in hallucination guards.
* **Automated Knowledge Ingestion:** A specialized ETL pipeline that scrapes news (NewsAPI/BeautifulSoup) and extracts entities via `LLMGraphTransformer`.
* **Interactive Visualizer:** A "Neural Grid" UI built with Streamlit and Glassmorphism CSS for real-time graph exploration.
* **Pro-Level Citations:** Every insight generated is linked directly back to its source article node via `[:MENTIONED_IN]` relationships.

---

## Tech Stack
* **Orchestration:** LangChain (Agents & Chains)
* **LLM:** OpenAI GPT-4o / GPT-4o-mini
* **Database:** Neo4j AuraDB (Graph)
* **Frontend:** Streamlit + Custom Glassmorphism CSS
* **Inference:** Python 3.10+

---

## Getting Started

1. **Clone the Repo**
   ```bash
   git clone https://github.com/Sumanth2305/NVIDIA_Sentinel.git
   cd NVIDIA_Sentinel
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   Create a `.env` file with your credentials:
   ```
   OPENAI_API_KEY=sk-...
   NEO4J_URI=neo4j+s://...
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=...
   ```

4. **Run the Sentinel**
   ```bash
   streamlit run app.py
   ```

