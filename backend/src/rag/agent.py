from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.common.prompts import GENERATE_CYPHER_GRPAH_RAG_SYSTEM_PROMPT, GRAPH_RETRIEVE_SYSTEM_PROMPT
from src.llm import get_llm
from .state import SimpleGraphRAGState
from .tools.generate_cypher import GenerateCypherTool
from .tools.graph_retrieve import GraphRetrieveTool


class SimpleGraphRagAgent:

    def __init__(self, 
                 model, 
                 graph, 
                 topk: int=5, 
                 include_types: list[str]=[], 
                 exclude_types: list[str]=[],
                 mode: str = "generate_cypher",
                 file_names: list[str]=[]
    ):
        self.llm,_,callback = get_llm(model)

        self.graph = graph
        self.topk = topk
        self.include_types = include_types
        self.exclude_types = exclude_types

        self.system_prompt = "you are a helpful assistant."

        self.tools = []
        if mode == "generate_cypher":
            generate_cypher_tool = GenerateCypherTool(graph=self.graph,
                                                    topk=self.topk,
                                                    include_types=self.include_types,
                                                    exclude_types=self.exclude_types)
            self.tools.append(generate_cypher_tool)
            self.system_prompt = GENERATE_CYPHER_GRPAH_RAG_SYSTEM_PROMPT

        if mode == "graph_retrieve":
            graph_retrieve_tool = GraphRetrieveTool(graph=self.graph, 
                                                    topk=self.topk, 
                                                    score_threshold=0.5, 
                                                    effective_search_ratio=0.5,
                                                    file_names=file_names)
            self.tools.append(graph_retrieve_tool)
            self.system_prompt = GRAPH_RETRIEVE_SYSTEM_PROMPT
    
    def _create_agent(self):

        checkpoint = InMemorySaver()
        return create_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=checkpoint,
            system_prompt=self.system_prompt,
            state_schema=SimpleGraphRAGState                                
        )