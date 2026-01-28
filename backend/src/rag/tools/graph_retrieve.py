from langchain.tools import BaseTool, ToolRuntime
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import TokenTextSplitter
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import EmbeddingsFilter, DocumentCompressorPipeline

from typing import Any, List, Type
from pydantic import BaseModel, Field, ConfigDict

from src.embedding import load_embedding_model
from src.common.cyphers import RETRIEVER_QUERY
from config import settings

import logging
logger = logging.getLogger(__name__)


SEARCH_ENTITY_LIMIT = 40  # 返回实体的个数
SEARCH_EMBEDDING_MIN_MATCH = 0.3  # 匹配的embedding的最小值
SEARCH_EMBEDDING_MAX_MATCH = 0.9  # 匹配的embedding的最大值
SEARCH_ENTITY_LIMIT_MINMAX_CASE = 20  # 匹配的实体个数最小值
SEARCH_ENTITY_LIMIT_MAX_CASE = 40     # 匹配的实体个数最大值


class GraphRetrieveInput(BaseModel):
    question: str = Field(..., description="question to be answered")
    runtime: ToolRuntime = Field(description="Tool runtime injected by langchain")

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )



class GraphRetrieveTool(BaseTool):
    name: str = "GraphRetrieve"
    description: str = "Use this tool to retrieve relevant information from a graph database."
    graph: Neo4jGraph = Field(description="Neo4jGraph instance")
    args_schema: Type[BaseModel] = GraphRetrieveInput


    topk: int = Field(description="Number of top results to return")
    effective_search_ratio: float = Field(description="Effective search ratio")
    score_threshold: float = Field(description="Score threshold")
    
    retriever: BaseRetriever = Field(None, description="ContextualCompressionRetriever instance")

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        file_names: List[str] = kwargs.get("file_names", [])
        self.retriever = self._init_graph_retriever(file_names)


    def _run(self, question: str, runtime: ToolRuntime):
        # 1. 检索文档
        docs = self.retriever.invoke(question)

        # 2. 结构化文档
        format_docs, sources, entities = self._format_documents(docs)

        return format_docs


    async def _arun(self,  question: str, runtime: ToolRuntime):
        # 1. 检索文档
        docs = await self.retriever.ainvoke(question)

        # 2. 结构化文档
        format_docs, sources, entities = self._format_documents(docs)

        return format_docs
    
    def _format_documents(self, docs):
        sorted_documents = sorted(docs, key=lambda doc: doc.state.get("query_similarity_score", 0), reverse=True)

        formatted_docs = list()
        sources = set()
        entities = dict()
        for doc in sorted_documents:
            try:
                source = doc.metadata.get("source", "unkown")
                sources.add(source)
                if 'entities' in doc.metadata:
                    if 'entityids' in doc.metadata['entities']:
                        entities.setdefault('entityids', set()).update(doc.metadata['entities']['entityids'])
                    if 'relationshipids' in doc.metadata['entities']:
                        entities.setdefault('relationshipids', set()).update(doc.metadata['entities']['relationshipids'])
                
                formatted_doc = (
                    "Document start\n"
                    f"This Document belongs to the source {source}\n"
                    f"Content: {doc.page_content}\n"
                    "Document end\n"
                )
                formatted_docs.append(formatted_doc)
            
            except Exception as e:
                logger.error(f"Error formatting document: {e}")
                raise e
        
        return "\n\n".join(formatted_docs), sources, entities

    def _init_graph_retriever(self, file_names: List[str]) -> BaseRetriever:
        """Initialize the graph retriever."""
        
        # 1. 初始化embedding模型
        embedding_model = settings.EMBEDDING_MODEL
        embedding_function, _ = load_embedding_model(embedding_model)

        # 2. cypher retriever query
        retriever_query = RETRIEVER_QUERY.format(
            no_of_entities=SEARCH_ENTITY_LIMIT,
            embedding_match_min=SEARCH_EMBEDDING_MIN_MATCH,
            embedding_match_max=SEARCH_EMBEDDING_MAX_MATCH,
            entity_limit_minmax_case=SEARCH_ENTITY_LIMIT_MINMAX_CASE,
            entity_limit_max_case=SEARCH_ENTITY_LIMIT_MAX_CASE
        )
        
       
        # 3. 创建检索参数
        search_kwargs = {
            'k': self.topk,
            'effective_search_ratio': self.effective_search_ratio,
            'score_threshold':self.score_threshold,
        }

        # 4. 创建 Neo4jVector 
        if file_names and len(file_names) > 0:
            vector = Neo4jVector.from_existing_graph(
                embedding=embedding_function,
                graph=self.graph,
                index_name="vector",
                retrieval_query=retriever_query,
                search_type="hybrid",
                node_label="Chunk",
                embedding_node_property="embedding",
                text_node_properties=["text"],
                keyword_index_name="keyword"
            )
            search_kwargs["fileName"] = {'$in': file_names}
            
        else:
            vector = Neo4jVector.from_existing_graph(
                embedding=embedding_function,
                graph=self.graph,
                index_name="vector",
                retrieval_query=retriever_query,
                node_label="Chunk",
                embedding_node_property="embedding",
                text_node_properties=["text"],
            )

        # 4. 创建 Neo4jRetriever
        retriever = vector.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs
        )


        # 5. 创建Retriever pipeline
        splitter = TokenTextSplitter(chunk_size=3000, chunk_overlap=0)
        embedding_filter = EmbeddingsFilter(
            embeddings=embedding_function,
            similarity_threshold=0.10
        )

        pipeline_compressor = DocumentCompressorPipeline(
            transformers=[splitter, embedding_filter]
        )

        # 6. 组合Retriever
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=pipeline_compressor, base_retriever=retriever
        )

        return compression_retriever

