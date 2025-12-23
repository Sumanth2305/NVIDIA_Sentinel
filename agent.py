import os
import sys
from dotenv import load_dotenv

# Libraries
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

# --- CONFIGURATION ---
load_dotenv()

class NvidiaSentinelAgent:
    def __init__(self):
        self._validate_env()
        
        print("🔌 Connecting to the 'Market Mind' Database...")
        try:
            self.graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI"),
                username=os.getenv("NEO4J_USERNAME"),
                password=os.getenv("NEO4J_PASSWORD")
            )
            self.graph.refresh_schema()
            print("✅ Database Connected.")
        except Exception as e:
            print(f"⚠️ Database Connection Failed: {e}")
            self.graph = None
        
        # The Brain
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
        
        # --- INTENT CLASSIFICATION ---
        self.intent_prompt = PromptTemplate(
            template="""
            You are a router. precise and fast.
            Classify the following user input into one of two categories: 'DATA' or 'GENERAL'.
            
            - 'DATA': The user is asking about companies, products, suppliers, relationships, news, or graph data.
            - 'GENERAL': The user is saying hi, hello, thanks, or asking about your identity.

            Input: {question}
            Classification:""",
            input_variables=["question"]
        )
        self.intent_chain = self.intent_prompt | self.llm

        # --- ENTITY EXTRACTION FOR VISUALIZATION ---
        self.entity_prompt = PromptTemplate(
            template="""
            Extract the single most important 'Subject' entity from this question for graph visualization.
            If multiple, pick the main one. Return ONLY the name.
            
            Question: {question}
            Entity:""",
            input_variables=["question"]
        )
        self.entity_chain = self.entity_prompt | self.llm
        
        # --- FINAL PROMPT ENGINEERING ---
        # FIX: We allow the Source URL to come from EITHER the Company OR the Product.
        cypher_generation_template = """
        You are an expert Neo4j Developer translating user questions into Cypher.
        The Schema: {schema}

        CRITICAL INSTRUCTIONS:
        1. SEARCH BROADLY: Use directionless arrows -[r]- to find connections.
        2. FIND PRODUCTS: Look for [:SUPPLIES_TO], [:PRODUCES], or [:MANUFACTURES].
        3. CITATIONS: The Article might be connected to the Company OR the Product. Check both paths.

        Examples:
        Question: "What products does TSMC supply?"
        Cypher: MATCH (c:Company)-[r]-(p:Product) 
                WHERE toLower(c.id) CONTAINS 'tsmc' 
                OPTIONAL MATCH (c)-[:MENTIONED_IN]-(a:Article) 
                RETURN c.id, type(r), p.id, a.url

        Question: "What is connected to Nvidia?"
        Cypher: MATCH (c:Company)-[r]-(target) 
                WHERE toLower(c.id) CONTAINS 'nvidia' 
                OPTIONAL MATCH (c)-[:MENTIONED_IN]-(a:Article)
                RETURN c.id, type(r), target.id, labels(target), a.url

        Question: {question}
        Cypher Query:"""
        
        cypher_prompt = PromptTemplate(
            input_variables=["schema", "question"], 
            template=cypher_generation_template
        )

        qa_template = """
        You are a Supply Chain Risk Analyst.
        
        Graph Data:
        {context}
        
        User Question: {question}
        
        STRICT INSTRUCTIONS:
        1. Answer based **ONLY** on the Graph Data above.
        2. List specific Product Names (e.g., "Arrow Lake", "H100") if found.
        3. Cite the Article URL provided in the data.
        4. If the data shows specific internal codenames (like "Lunar Lake"), highlight them as key findings.
        
        Answer:"""
        
        qa_prompt = PromptTemplate(
            input_variables=["context", "question"], 
            template=qa_template
        )

        if self.graph:
            self.chain = GraphCypherQAChain.from_llm(
                llm=self.llm,
                graph=self.graph,
                verbose=True,
                cypher_prompt=cypher_prompt,
                qa_prompt=qa_prompt,
                allow_dangerous_requests=True,
                return_intermediate_steps=True, 
                top_k=10
            )
        else:
            self.chain = None

    def _validate_env(self):
        required_keys = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "OPENAI_API_KEY"]
        missing = [key for key in required_keys if not os.getenv(key)]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {missing}")



    def _classify_intent(self, question):
        try:
            response = self.intent_chain.invoke({"question": question})
            return response.content.strip().upper()
        except: return "DATA" # Default to data if unsure

    def ask(self, question):
        print("\n" + "="*50)
        print(f" Querying: {question}")
        print("="*50)

        # 1. Check Intent
        intent = self._classify_intent(question)
        print(f"🧠 Detected Intent: {intent}")

        if "GENERAL" in intent:
            # Handle Chitchat without DB
            response = self.llm.invoke(f"You are Nvidia Sentinel, a Supply Chain Intelligence AI. The user says: '{question}'. Respond politely and briefly.")
            return {
                "result": response.content,
                "cypher": "None (General Conversation)"
            }

        # 2. Handle Data Query (Existing Logic)
        if self.graph is None:
            return {
                "result": "⚠️ I am currently disconnected from the Knowledge Graph. Please check your Neo4j Connection settings.",
                "cypher": "Connection Error"
            }

        try:
            response = self.chain.invoke({"query": question})
            final_answer = response.get("result", "No answer.")
            
            steps = response.get("intermediate_steps", [])
            generated_cypher = steps[0]["query"] if steps else "None"
            
            # Print for Debugging
            print(f"\n📝 Generated Cypher:\n{generated_cypher}")
            print("-" * 30)
            print(f"💡 Analyst Output:\n{final_answer}")
            print("-" * 30)
            
            return {
                "result": final_answer,
                "cypher": generated_cypher
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"result": "I encountered an error accessing the data grid.", "cypher": "Error"}
            


    def visualize_query_neighborhood(self, question):
        """
        Fetches the immediate graph neighborhood for a visual display.
        """
        if self.graph is None: return None

        try:
            # 1. Identify the Entity
            entity_name = self.entity_chain.invoke({"question": question}).content.strip()
            print(f"🕸️ Visualizing Neighborhood for: {entity_name}")
            
            # 2. Query the Graph
            query = """

            MATCH (n)-[r]-(m)
            WHERE toLower(n.id) CONTAINS toLower($name)
            RETURN n, type(r) as r_type, m LIMIT 25
            """
            data = self.graph.query(query, params={"name": entity_name})
            
            # 3. Format for Streamlit AGraph
            nodes = set()
            edges = []
            
            for record in data:
                n = record['n']
                m = record['m']
                r_type = record['r_type']
                
                # Add Nodes (Use ID as label for simplicity)
                # Handle both object and dict access for safety
                def get_lbl(node_obj):
                    if hasattr(node_obj, 'labels'): return list(node_obj.labels)[0]
                    return node_obj.get('labels', ['Entity'])[0] if isinstance(node_obj, dict) else "Entity"

                def get_id(node_obj):
                    if isinstance(node_obj, dict): return node_obj.get('id', "Unknown")
                    return node_obj.get("id") if "id" in node_obj else str(node_obj)

                n_id = get_id(n)
                m_id = get_id(m)

                nodes.add((n_id, get_lbl(n)))
                nodes.add((m_id, get_lbl(m)))
                
                # Add Edges
                edges.append({
                    "source": n_id,
                    "target": m_id,
                    "type": r_type
                })
            
            return {
                "nodes": [{"id": n[0], "label": n[0], "group": n[1]} for n in nodes],
                "edges": edges
            }

        except Exception as e:
            print(f"❌ Visual Error: {e}")
            return None

if __name__ == "__main__":
    agent = NvidiaSentinelAgent()
    print("\n✅ AGENT READY! Type 'exit' to quit.\n")
    while True:
        user_input = input(">> Enter question: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        agent.ask(user_input)