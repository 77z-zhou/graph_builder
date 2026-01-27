from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.common.prompts import SIMPLE_GRPAH_RAG_SYSTEM_PROMPT
from src.llm import get_llm
from .middleware import GenerateCypherMiddleWare
from .state import SimpleGraphRAGState
from .tools import GenerateCypherTool


class SimpleGraphRagAgent:

    def __init__(self, 
                 model, 
                 graph, 
                 topk: int=5, 
                 include_types: list[str]=[], 
                 exclude_types: list[str]=[]
    ):
        self.llm,_,callback = get_llm(model)

        self.graph = graph
        self.topk = topk
        self.include_types = include_types
        self.exclude_types = exclude_types

    
    def _create_agent(self):
        # generate_cypher_middleware = GenerateCypherMiddleWare(self.graph, 
        #                                                       topk=self.topk, 
        #                                                       include_types=self.include_types, 
        #                                                       exclude_types=self.exclude_types)
        
        generate_cypher_tool = GenerateCypherTool(graph=self.graph,
                                                  topk=self.topk,
                                                  include_types=self.include_types,
                                                  exclude_types=self.exclude_types)
        checkpoint = InMemorySaver()
        return create_agent(
            model=self.llm,
            tools=[generate_cypher_tool],
            checkpointer=checkpoint,
            system_prompt=SIMPLE_GRPAH_RAG_SYSTEM_PROMPT,
            state_schema=SimpleGraphRAGState                                
        )