from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_neo4j import Neo4jGraph
from neo4j_graphrag.schema import format_schema

from pydantic import BaseModel, Field
from typing import Callable, List, Dict, Any
from src.common.prompts import CYPHER_GENERATION_PROMPT, CYPHER_QA_PROMPT
from .state import SimpleGraphRAGState
from .utils import CypherQueryCorrector, Schema

import logging

logger = logging.getLogger(__name__)


class GenerateCypher(BaseModel):
    cypher: str = Field(..., description="Cypher statement")
    

class GenerateCypherMiddleWare(AgentMiddleware):

    def __init__(self, 
                 graph: Neo4jGraph, 
                 topk: int = 10,
                 include_types:List[str] = [], 
                 exclude_types:List[str] = []
    ):
        self.graph = graph  # neo4j graph
        self.topk = topk
        if include_types and exclude_types:
            raise ValueError(
                "Either `exclude_types` or `include_types` "
                "can be provided, but not both"
            )
        self.include_types = include_types
        self.exclude_types = exclude_types
        self.cypher_corrector = self.get_cypher_corrector()


    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ):
        model = request.model
        structred_output_model = model.with_structured_output(GenerateCypher)
        state: SimpleGraphRAGState = request.state
        # 1. 获取用户问题
        question = state.get("question")

        # 2. 获取示例 TODO: 从store中获取历史收集的示例exampe
        examples = None

        # 3. schema
        schema = self.construct_schema()

        # 4. prompt
        prompt = CYPHER_GENERATION_PROMPT.format(question=question, examples=examples, schema=schema)

        # 5. 生成cypher
        logger.info(f"generate cypher prompt:{prompt}")
        response = structred_output_model.invoke(prompt)
        cypher = response.cypher

        # 6. 验证cypher
        cypher_corrected = self.cypher_corrector(cypher)
        logger.info(f"generated cypher is {cypher_corrected}")

        # 7. graph neo4j 查询
        context = self.graph.query(cypher_corrected)[:self.topk]
        logger.info(f"graph query result context is: {context}")

        # 8. 修改系统提示词
        system_prompt = CYPHER_QA_PROMPT.format(context)
        return handler(request.override(system_prompt=system_prompt))


    async def awrap_model_call(self, request, handler):
        model = request.model
        structred_output_model = model.with_structured_output(GenerateCypher)
        state: SimpleGraphRAGState = request.state
        # 1. 获取用户问题
        question = state.get("question")

        # 2. 获取示例 TODO: 从store中获取历史收集的示例exampe
        examples = None

        # 3. schema
        schema = self.construct_schema()

        # 4. prompt
        prompt = CYPHER_GENERATION_PROMPT.format(question=question, examples=examples, schema=schema)

        # 5. 生成cypher
        response = await structred_output_model.ainvoke(prompt)
        cypher = response.cypher
        logger.info(f"generated cypher is {cypher}")

        # 6. 验证cypher
        cypher_corrected = self.cypher_corrector(cypher)
        logger.info(f"corrected cypher is {cypher_corrected}")

        # 7. graph neo4j 查询
        context = self.graph.query(cypher_corrected)[:self.topk]
        logger.info(f"graph query result context is: {context}")

        # 8. 修改系统提示词
        system_prompt = CYPHER_QA_PROMPT.format(context=context)
        return await handler(request.override(system_prompt=system_prompt))


    def get_cypher_corrector(self):
        corrector_schema = [
            Schema(el["start"], el["type"], el["end"])
            for el in self.graph.get_structured_schema.get("relationships", [])
        ]
        return CypherQueryCorrector(corrector_schema)

    def construct_schema(self):
        """ filter the schema based on the include_types and exclude_types """
        structured_schema = self.graph.get_structured_schema

        def filter_func(x: str) -> bool:
            return x in self.include_types if self.include_types else x not in self.exclude_types

        filtered_schema: Dict[str, Any] = {
            "node_props": {
                k: v
                for k, v in structured_schema.get("node_props", {}).items()
                if filter_func(k)
            },
            "rel_props": {
                k: v
                for k, v in structured_schema.get("rel_props", {}).items()
                if filter_func(k)
            },
            "relationships": [
                r
                for r in structured_schema.get("relationships", [])
                if all(filter_func(r[t]) for t in ["start", "end", "type"])
            ],
        }
        return format_schema(filtered_schema, self.graph._enhanced_schema)
        





        



        
        
        