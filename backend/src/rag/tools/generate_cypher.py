from langchain.tools import BaseTool, ToolRuntime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_neo4j import Neo4jGraph
from neo4j_graphrag.schema import format_schema

import json
from typing import Any, List, Dict, Type, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.common.prompts import CYPHER_GENERATION_PROMPT, ERROR_TOOL_MESSAGE
from src.llm import get_llm
from ..utils import CypherQueryCorrector, Schema
from config import settings



import logging
logger = logging.getLogger(__name__)


class GenerateCypher(BaseModel):
    cypher: str = Field(..., description="Cypher statement")


class GenerateCypherInput(BaseModel):
    question: str = Field(..., description="question to be answered")
    runtime: ToolRuntime = Field(description="Tool runtime injected by langchain")

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

class GenerateCypherTool(BaseTool):
    name: str = "GenerateCypher"
    description: str = "Generate Cypher statement to query a graph database."
    args_schema:Type[BaseModel] = GenerateCypherInput


    graph: Neo4jGraph = Field(description="Neo4jGraph instance")
    topk: int = Field(description="Number of top results to return")
    include_types: List[str] = Field(description="List of node types to include")
    exclude_types: List[str] = Field(description="List of node types to exclude")


    cypher_corrector: Optional[CypherQueryCorrector] = Field(None, description="CypherQueryCorrector instance") # cypher修正器
    generate_cypher_model: Optional[BaseLanguageModel] = Field(None,description="BaseLanguageModel instance used to generate cypher")


    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        if self.include_types and self.exclude_types:
            raise ValueError(
                "Either `exclude_types` or `include_types` "
                "can be provided, but not both"
        )
        self.cypher_corrector = self._init_cypher_corrector()
        self.generate_cypher_model = self._init_generate_cypher_model()


    def _run(self, question: str, runtime: ToolRuntime) -> str:
        """generate cypher."""
        
        # 1. TODO: 从数据库中获取examples 
        examples = ""

        # 2. 获取schema
        graph_schema = self._construct_schema()

        # 3. 获取index
        graph_indexes = self._construct_indexes()

        # 4. 构建prompt
        sys_prompt = CYPHER_GENERATION_PROMPT.format(schema=graph_schema, 
                                                 indexes=graph_indexes,
                                                 examples=examples)
        
        history_messages = [SystemMessage(content=sys_prompt), HumanMessage(content=question)]
        retries = 0
        while retries < 3: # 重试
            flag = False
            # 5. 生成cypher
            response = self.generate_cypher_model.invoke(history_messages)
            cypher_obj = response["parsed"]
            cypher = cypher_obj.cypher
            logger.info(f"【llm generate cypher is】: {cypher}")

            # 6. 修正cypher
            corrected_cypher = self.cypher_corrector(cypher)
            
            if corrected_cypher and corrected_cypher.strip():
                logger.info(f"【cypher corrector result is】: {corrected_cypher}")

                # 7. 根据cypher 查询context
                try:
                    context = self.graph.query(corrected_cypher)[:self.topk]
                    logger.info(f"【graph retrieve context is】: {context}")
                    flag = True
                except Exception as e:
                    logger.error(f"【graph retrieve error】: {e}")

                if flag:
                    break
                
            # 模拟对话模式
            ai_message:AIMessage = response["raw"]
            history_messages.append(ai_message)
            tool_call_id = ai_message.tool_calls[0]["id"]
            tool_msg = ToolMessage(content=ERROR_TOOL_MESSAGE, tool_call_id=tool_call_id)
            history_messages.append(tool_msg)

            retries += 1
        
        if not flag: # 如果修正失败
            return "cypher generate failed"

        return f"graph database retrieve context is: {context}"
    


    async def _arun(self, question: str, runtime: ToolRuntime) -> str:
        """generate cypher asynchronously."""
        
        # 1. TODO: 从数据库中获取examples 
        examples = ""

        # 2. 获取schema
        graph_schema = self._construct_schema()

        # 3. 获取index
        graph_indexes = self._construct_indexes()

        # 4. 构建prompt
        sys_prompt = CYPHER_GENERATION_PROMPT.format(schema=graph_schema, 
                                                 indexes=graph_indexes,
                                                 examples=examples)
        
        history_messages = [SystemMessage(content=sys_prompt), HumanMessage(content=question)]
        retries = 0
        while retries < 3: # 重试
            flag = False
            # 5. 生成cypher
            response = await self.generate_cypher_model.ainvoke(history_messages)
            cypher_obj = response["parsed"]
            cypher = cypher_obj.cypher
            logger.info(f"【llm generate cypher is】: {cypher}")

            # 6. 修正cypher
            corrected_cypher = self.cypher_corrector(cypher)
            
            if corrected_cypher and corrected_cypher.strip():
                logger.info(f"【cypher corrector result is】: {corrected_cypher}")

                # 7. 根据cypher 查询context
                try:
                    context = self.graph.query(corrected_cypher)[:self.topk]
                    logger.info(f"【graph retrieve context is】: {context}")
                    flag = True
                except Exception as e:
                    logger.error(f"【graph retrieve error】: {e}")
                    
                if flag:
                    break
                
            # 模拟对话模式
            ai_message:AIMessage = response["raw"]
            history_messages.append(ai_message)
            tool_call_id = ai_message.tool_calls[0]["id"]
            tool_msg = ToolMessage(content=ERROR_TOOL_MESSAGE, tool_call_id=tool_call_id)
            history_messages.append(tool_msg)

            retries += 1
                
        if not flag: # 如果修正失败
            return "cypher generate failed"
    
        return f"graph database retrieve context is: {context}"

    def _init_generate_cypher_model(self) -> BaseLanguageModel:
        """Initialize the model used to generate cypher."""
        generate_cypher_model = settings.GENERATE_CYPHER_MODEL
        generate_cypher_model, _, _ = get_llm(generate_cypher_model)
        return generate_cypher_model.with_structured_output(GenerateCypher, include_raw=True)


    def _init_cypher_corrector(self):
        corrector_schema = [
            Schema(el["start"], el["type"], el["end"])
            for el in self.graph.get_structured_schema.get("relationships", [])
        ]
        return CypherQueryCorrector(corrector_schema)

    def _construct_indexes(self):
        """Get the indexes for the graph."""
        index_list = self.graph.query("SHOW INDEXES YIELD name, labelsOrTypes, properties, type")
        index_list = [index for index in index_list if index.get("type") not in ["LOOKUP", "VECTOR"]]
        return json.dumps(index_list)


    def _construct_schema(self):
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
        
