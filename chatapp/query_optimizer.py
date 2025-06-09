from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

def decompose_complex_query(query):
    """Break down complex queries into simpler components"""
    
    # Skip decomposition for simple queries
    if len(query.split()) < 10:
        return None
    
    # Initialize LLM
    llm = ChatOllama(model="llama3.1:8b-instruct-q4_0", temperature=0)
    
    # Create decomposition prompt
    decomposition_prompt = ChatPromptTemplate.from_template("""
    You are a query analysis expert. Analyze the following query and determine if it contains 
    multiple questions or requires a multi-step approach to answer properly.
    
    If the query is complex, break it down into 2-3 simpler sub-queries that would help answer 
    the original question when combined. If the query is already simple, respond with "SIMPLE".
    
    Original query: {query}
    
    Format your response as a JSON array of sub-queries or "SIMPLE" if no decomposition is needed.
    Do not include any explanations or additional text.
    """)
    
    # Create and run the chain
    decomposition_chain = decomposition_prompt | llm
    
    try:
        # Get the decomposition result
        result = decomposition_chain.invoke({"query": query})
        content = result.content
        
        # Parse the result
        import json
        if "SIMPLE" in content:
            return None
        
        # Extract the JSON part from the response
        json_start = content.find('[')
        json_end = content.rfind(']') + 1
        if json_start < 0 or json_end < 0:
            return None
            
        sub_queries = json.loads(content[json_start:json_end])
        if isinstance(sub_queries, list) and len(sub_queries) > 0:
            return sub_queries
        return None
        
    except Exception as e:
        print(f"Error in query decomposition: {str(e)}")
        return None