from src.graph_db_access import GraphDBDataAccess
from src.document_processors.local_file import get_documents_from_file_by_path
from src.document_processors.doc_chunk import CreateChunksofDocument
from src.graph_llm.graph_transform import LLMGraphTransformer
from src.common.prompts import ADDITIONAL_INSTRUCTIONS, GRAPH_CLEANUP_PROMPT
from src.common.exception import GraphBuilderException
from src.llm import get_llm
from src.rag.simple_graph_rag.agent import SimpleGraphRagAgent
from src.embedding import load_embedding_model

from app_entities import Neo4jCredentials, SourceNode, SourceScanExtractParams
from config import *
from utils import (
    sanitize_additional_instruction, 
    clean_nodes_and_relationships, 
    delete_uploaded_local_file
)


from langchain_neo4j import Neo4jGraph
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

import json
import os
import logging
import shutil
import time
from datetime import datetime


logger = logging.getLogger(__name__)


def merge_chunks_local(file_name, total_chunks, chunk_dir, merged_dir):
    """合并chunk文件"""

    if not os.path.exists(merged_dir):
        os.mkdir(merged_dir)
    logger.info(f"Merged File Path: {merged_dir}")

    merged_file_path = os.path.join(merged_dir, file_name)
    with open(merged_file_path, "wb") as write_stream:
        for i in range(1, total_chunks + 1):
            chunk_file_path = os.path.join(chunk_dir, f"{file_name}_part_{i}")
            logger.info(f"Chunk File Path While Merging Parts:{chunk_file_path}")
            with open(chunk_file_path, "rb") as chunk_file:
                shutil.copyfileobj(
                    chunk_file, write_stream
                )  # 将chunk的内容拷贝到 merge上
            os.unlink(chunk_file_path)  # 删除merge过的chunk
    logger.info("Chunks merged successfully and return file size")
    file_size = os.path.getsize(merged_file_path)
    return file_size


def upload_file(
    graph,
    model,
    chunk,
    chunk_number: int,
    total_chunks: int,
    file_name,
    chunk_dir,
    merged_dir,
):
    """上传文件"""

    file_name = file_name.strip() if isinstance(file_name, str) else file_name
    # TODO: OSS上传文件
    OSS = False
    if OSS:
        ...
    else:
        if not os.path.exists(chunk_dir):
            os.mkdir(chunk_dir)
        chunk_file_path = os.path.join(chunk_dir, f"{file_name}_part_{chunk_number}")
        logger.info(f"Chunk File Path:{chunk_file_path}")
        with open(chunk_file_path, "wb") as chunk_file:
            chunk_file.write(chunk.file.read())

    # 文件分块上传完成，需要合并chunk
    if int(chunk_number) == int(total_chunks):
        if OSS:
            ...
        else:
            file_size = merge_chunks_local(file_name, int(total_chunks), chunk_dir, merged_dir)
        logger.info("File merged successfully!")
        file_extension = file_name.split(".")[-1]
        obj_source_node = SourceNode()
        obj_source_node.file_name = file_name
        obj_source_node.file_type = file_extension
        obj_source_node.file_size = file_size
        obj_source_node.file_source = "local file"
        obj_source_node.model = model
        obj_source_node.created_at = datetime.now()
        obj_source_node.chunkNodeCount = 0
        obj_source_node.chunkRelCount = 0
        obj_source_node.entityNodeCount = 0
        obj_source_node.entityEntityRelCount = 0
        obj_source_node.communityNodeCount = 0
        obj_source_node.communityRelCount = 0
        db_access = GraphDBDataAccess(graph)
        db_access.create_source_node(obj_source_node)
        return {
            "file_size": file_size,
            "file_name": file_name,
            "file_extension": file_extension,
            "message": f"Chunk {chunk_number}/{total_chunks} saved",
        }
    return f"Chunk {chunk_number}/{total_chunks} saved"


def create_graph_database_connection(credentials: Neo4jCredentials, refresh_schema=False):
    """创建数据库连接"""
    enable_user_agent = settings.ENABLE_USER_AGENT
    if enable_user_agent:
        graph = Neo4jGraph(
            url=credentials.uri,
            database=credentials.database,
            username=credentials.userName,
            password=credentials.password,
            refresh_schema=refresh_schema,
            sanitize=True,
            driver_config={"user_agent": "LLM-Graph-Builder"},
        )
    else:
        graph = Neo4jGraph(
            url=credentials.uri,
            database=credentials.database,
            username=credentials.userName,
            password=credentials.password,
            refresh_schema=refresh_schema,
            sanitize=True,
        )
    return graph


def update_exception(graph, file_name, error_message):
    """更新节点错误信息"""
    db_access = GraphDBDataAccess(graph)
    db_access.update_exception_db(file_name, error_message)


def connection_check_and_get_vector_dimensions(graph):
    """数据库连接检查并获取向量维度"""
    dataAccess = GraphDBDataAccess(graph)
    return dataAccess.connection_check_and_get_vector_dimensions()


# =========== 知识图谱抽取 =========
def update_node_relationship_count(credentials, file_name=None):
    graph = create_graph_database_connection(credentials)
    data_access = GraphDBDataAccess(graph)
    return data_access.update_node_relationship_count(file_name)


def get_chunkId_chunkDoc_list(
    data_access: GraphDBDataAccess,
    file_name,
    docs,
    token_chunk_size,
    chunk_overlap,  # 每个chunk的token大小  chunk之间的重叠大小
    retry_condition,
):
    """
    获取Chunk ID 和 对应的 文档Chunk
    /
    首次处理需要分块, 创建ChunkNode relationships
    """

    # 首次处理
    if retry_condition in ["", None] or retry_condition not in [
        DELETE_ENTITIES_AND_START_FROM_BEGINNING,
        START_FROM_LAST_PROCESSED_POSITION,
    ]:
        logger.info("Break down file into chunks")

        # 1. 替换不必要的字符串
        bad_chars = ['"', "\n", "'"]
        for i in range(0, len(docs)):
            text = docs[i].page_content
            for j in bad_chars:
                if j == "\n":
                    text = text.replace(j, " ")
                else:
                    text = text.replace(j, "")
            docs[i] = Document(page_content=str(text), metadata=docs[i].metadata)

        # 2. 切分docs
        create_chunks_obj = CreateChunksofDocument(docs)
        chunks = create_chunks_obj.split_file_into_chunks(
            token_chunk_size, chunk_overlap
        )

        # 3. 创建chunkNode 并建立relationships
        chunkId_chunkDoc_list = data_access.create_relation_between_chunks(
            file_name, chunks
        )
        return len(chunks), chunkId_chunkDoc_list

    # 非首次, 需要根据策略获取filename下没处理完的chunk
    else:
        chunkId_chunkDoc_list = []  # 最终返回的chunk集合
        chunks = data_access.get_chunks_by_fileName(file_name)

        # file的chunk不存在
        if chunks[0]["text"] is None or chunks[0]["text"] == "" or not chunks:
            raise Exception(
                f"Chunks are not created for {file_name}. Please re-upload file or reprocess the file with option Start From Beginning."
            )

        else:
            for chunk in chunks:
                chunk_doc = Document(
                    page_content=chunk["text"],
                    metadata={"id": chunk["id"], "position": chunk["position"]},
                )
                chunkId_chunkDoc_list.append(
                    {"chunk_id": chunk["id"], "chunk_doc": chunk_doc}
                )

            # 从上次处理位置继续
            if retry_condition == START_FROM_LAST_PROCESSED_POSITION:
                logger.info(f"Retry: start from last processed position")
                starting_chunk = data_access.get_last_processed_chunk(file_name)

                # 情况1:  中间位置恢复
                if starting_chunk and starting_chunk[0]["position"] < len(
                    chunkId_chunkDoc_list
                ):
                    return (
                        len(chunks),
                        chunkId_chunkDoc_list[starting_chunk[0]["position"] - 1 :],
                    )

                # 情况2： 全部chunk处理完毕，但是有遗漏的(有的chunk没有提取Entity实体)
                elif starting_chunk and starting_chunk[0]["position"] == len(
                    chunkId_chunkDoc_list
                ):
                    # 查询处没有进行实体抽取的 chunk
                    starting_chunk = (
                        data_access.get_last_processed_without_entity_chunk(file_name)
                    )
                    return (
                        len(chunks),
                        chunkId_chunkDoc_list[starting_chunk[0]["position"] - 1 :],
                    )

                # 情况3: 全部完成
                else:
                    raise Exception(
                        f"All chunks of file {file_name} are already processed. If you want to re-process, Please start from begnning"
                    )

            # 从头开始
            else:
                logger.info(
                    f"Retry : start_from_beginning with chunks {len(chunkId_chunkDoc_list)}"
                )
                return len(chunks), chunkId_chunkDoc_list


def get_combied_chunks(chunks: list, chunks_to_combine: int):
    """合并小chunk为一个Document"""
    # 1. 按照chunks_to_combine合并文本内容
    combined_chunks_page_content = [
        "".join(
            chunk["chunk_doc"].page_content
            for chunk in chunks[i : i + chunks_to_combine]
        )
        for i in range(0, len(chunks), chunks_to_combine)
    ]

    combined_chunks_ids = [
        [chunk["chunk_id"] for chunk in chunks[i : i + chunks_to_combine]]
        for i in range(0, len(chunks), chunks_to_combine)
    ]

    # 2. 按照合并后的chunk 创建新的doc
    combined_chunk_doc_list = []
    for i in range(len(combined_chunks_page_content)):
        combined_chunk_doc_list.append(
            Document(
                page_content=combined_chunks_page_content[i],
                metadata={"combined_chunk_ids": combined_chunks_ids[i]},
            )
        )
    return combined_chunk_doc_list


async def get_graph_from_llm(chunks: list, params: SourceScanExtractParams):
    """使用LLM提取知识图谱的关系节点"""
    try:
        # 1. 获取LLM
        model = params.model
        llm, model_name, callback_handler = get_llm(model)
        logger.info(f"Using model: {model_name}")

        # 2. 合并chunk
        chunks_to_combine = (
            params.chunks_to_combine
        )  #  多少个chunk合并为一个大chunk用于实体抽取
        combined_chunk_doc_list = get_combied_chunks(chunks, chunks_to_combine)
        logger.info(f"Combined {len(combined_chunk_doc_list)} chunks")

        # 3. 允许的节点Node
        allowedNodes = params.allowedNodes
        allowed_nodes = []
        if allowedNodes:
            for node in allowedNodes.split(","):
                allowed_nodes.append(node.strip())
        logger.info(f"Allowed nodes: {allowed_nodes}")

        # 4. 允许的关系Relationship
        allowedRelationship = params.allowedRelationship # eg: node1, rel1, node2, node3, rel2, node4
        allowed_relationships = []
        if allowedRelationship:
            items = [
                item.strip()
                for item in allowed_relationships.split(",")
                if item.strip()
            ]
            if len(items) % 3 != 0:
                raise Exception(
                    "allowedRelationship must be a multiple of 3 (source, relationship, target)"
                )
            for i in range(0, len(items), 3):
                source, relation, target = items[i : i + 3]
                if source not in allowed_nodes:
                    raise Exception(
                        f"Invalid relationship ({source}, {relation}, {target}): "
                        f"source or target not in allowedNodes"
                    )
                allowed_relationships.append((source, relation, target))
            logger.info(f"Allowed relationships: {allowed_relationships}")

        else:
            # 没有提供允许的关系
            logger.info("No allowed relationships provided")

        # 5. 使用LLM提取知识图谱
        additional_instructions = params.additional_instructions
        additional_instructions = sanitize_additional_instruction(
            additional_instructions
        )
        graph_llm = LLMGraphTransformer(
            llm,
            allowed_nodes,
            allowed_relationships,
            strict_mode=True,
            node_properties=["description"],
            relationship_properties=["description"],
            additional_instructions=(
                ADDITIONAL_INSTRUCTIONS + additional_instructions
                if additional_instructions
                else ""
            ),
        )
        config = RunnableConfig(callbacks=[callback_handler])
        graph_document_list = await graph_llm.convert_to_graph_documents(
            combined_chunk_doc_list, config=config
        )
        usage = callback_handler.report()
        token_usage = usage.get("total_tokens", 0)
        return graph_document_list, token_usage
    except Exception as e:
        logger.error(f"Error in get_graph_from_llm: {e}", exc_info=True)
        raise e


async def processing_chunks(
    chunks: list,
    data_access: GraphDBDataAccess,
    params: SourceScanExtractParams,
):
    try:
        # 统计处理chunk各步骤的时间
        latency_processing_chunk = {}

        # 1. 构建知识图谱参数基本信息提取
        file_name = params.file_name

        # TODO: 用户 Token使用限制检查

        # 2. 给chunk创建向量嵌入
        start_update_embedding = time.time()
        data_access.create_chunk_embeddings(chunks, file_name)
        end_update_embedding = time.time()
        elapsed_update_embedding = end_update_embedding - start_update_embedding
        logger.info(
            f"Time taken to update embedding in chunk node: {elapsed_update_embedding:.2f} seconds"
        )
        latency_processing_chunk["update_embedding"] = f"{elapsed_update_embedding:.2f}"

        # 3. 使用LLM进行知识图谱提取
        start_entity_extraction = time.time()
        graph_documents, token_usage = await get_graph_from_llm(chunks, params)
        end_entity_extraction = time.time()
        elapsed_entity_extraction = end_entity_extraction - start_entity_extraction
        logger.info(
            f"Time taken to extract enitities from LLM Graph Builder: {elapsed_entity_extraction:.2f} seconds"
        )
        latency_processing_chunk["entity_extraction"] = f"{elapsed_entity_extraction:.2f}"

        # 4. 保存知识图谱到Neo4j数据库
        start_save_graphDocuments = time.time()
        cleaned_graph_documents = clean_nodes_and_relationships(graph_documents)
        data_access.save_graph_documents(cleaned_graph_documents)
        end_save_graphDocuments = time.time()
        elapsed_save_graphDocuments = end_save_graphDocuments - start_save_graphDocuments
        logger.info(
            f"Time taken to save graph document in neo4j: {elapsed_save_graphDocuments:.2f} seconds"
        )
        latency_processing_chunk["save_graphDocuments"] = (
            f"{elapsed_save_graphDocuments:.2f}"
        )

        # 5. 将chunk 和 对应提取的知识图谱 关联起来
        start_relationship = time.time()
        data_access.merge_relationship_between_chunk_and_graph_entities(
            cleaned_graph_documents
        )
        end_relationship = time.time()
        elapsed_relationship = end_relationship - start_relationship
        logger.info(
            f"Time taken to create relationship between chunk and entities: {elapsed_relationship:.2f} seconds"
        )
        latency_processing_chunk["relationship_between_chunk_entity"] = (
            f"{elapsed_relationship:.2f}"
        )

        # 6. 更新Document的node和relationship的数量
        res = data_access.update_node_relationship_count(file_name)
        node_count = res[file_name].get("nodeCount", "0")
        rel_count = res[file_name].get("relationshipCount", "0")

        return node_count, rel_count, latency_processing_chunk, token_usage
    except Exception as e:
        data_access.update_exception_db(file_name, str(e), params.retry_condition)
        raise e

async def processing_source(
    credentials, params, docs, file_path=None, is_uploaded_from_local=True
):
    file_name = params.file_name
    response = {} # 最终返回的字典
    uri_latency = {}
    start_time = datetime.now()
    processing_source_start_time = time.time()

    # 1. 创建neo4j数据库连接
    graph = create_graph_database_connection(credentials)

    # 2. 创建图数据库操作类  给chunk创建向量索引
    data_access = GraphDBDataAccess(graph)
    data_access.create_chunk_vector_index()  

    # 3. 分块 并 创建chunkNode 和 RelationShips 并与Document建立关系
    total_chunks, chunkId_chunkDoc_list = get_chunkId_chunkDoc_list(
        data_access,
        file_name,
        docs,
        params.token_chunk_size,
        params.chunk_overlap,
        params.retry_condition,
    )

    # 4. 获取Document node节点
    result = data_access.get_current_status_document_node(file_name)
    
    #  5. 更新Document node的元数据
    select_chunks_with_retry = 0

    # 有Document node 需要处理
    if len(result) > 0:
        # 处理状态非Processing的Document
        if result[0]["Status"] != "Processing":
            obj_source_node = SourceNode()
            status = "Processing"
            obj_source_node.file_name = file_name
            obj_source_node.status = status
            obj_source_node.total_chunks = total_chunks
            obj_source_node.model = params.model
            if params.retry_condition == START_FROM_LAST_PROCESSED_POSITION:
                select_chunks_with_retry = result[0]["processed_chunk"]
            obj_source_node.processed_chunk = select_chunks_with_retry
            logger.info(obj_source_node)

            # 更新Doc的统计计数以及状态
            data_access.update_source_node(obj_source_node)  # 更新状态和进度 状态为; Processing
            data_access.update_node_relationship_count(file_name)  # 校准节点关系计数
           
            logger.info("Update the status as Processing")

            # 核心: 批处理chunk, 从中抽取知识图谱并建立关系
            update_graph_chunk_batch_size = settings.UPDATE_GRPAH_CHUNK_BATCH_SIZE
            is_cancelled_status = False
            job_status = "Completed"
            tokens_per_file = 0
            for i in range(0, len(chunkId_chunkDoc_list), update_graph_chunk_batch_size):
                # 确定批量处理chunk
                select_chunks_upto = i + update_graph_chunk_batch_size
                logger.info(f"Selected Chunks upto:{select_chunks_upto}")
                if len(chunkId_chunkDoc_list) <= select_chunks_upto:
                    select_chunks_upto = len(chunkId_chunkDoc_list)

                selected_chunks = chunkId_chunkDoc_list[i:select_chunks_upto]

                # 再次获取Document node节点, 查看最新的status(防止用户取消)
                result = data_access.get_current_status_document_node(file_name)
                is_cancelled_status = result[0]["is_cancelled"]
                logger.info(f"Value of is_cancelled: {result[0]['is_cancelled']}")

                # 如果用户取消了Doc, 则跳出循环
                if bool(is_cancelled_status) == True:
                    job_status = "Cancelled"
                    break

                # 如果没取消, 则批处理chunk
                else:
                    (node_count, rel_count, latency_processed_chunk, token_usage) = (
                        await processing_chunks(selected_chunks, data_access, params)
                    )
                    logger.info("Token used in processing chunks: %s", token_usage)
                    tokens_per_file += token_usage
                    logger.info("Total token used per file: %s", tokens_per_file)
                    uri_latency[f'processed_chunk_detail_{i}-{select_chunks_upto}'] = latency_processed_chunk
            
                    end_time = datetime.now()
                    processed_time = end_time - start_time
                    obj_source_node = SourceNode()
                    obj_source_node.file_name = file_name
                    obj_source_node.updated_at = end_time
                    obj_source_node.processing_time = processed_time
                    obj_source_node.processed_chunk = select_chunks_upto + select_chunks_with_retry
                    obj_source_node.token_usage = tokens_per_file
                    obj_source_node.node_count = node_count
                    obj_source_node.relationship_count = rel_count
                    data_access.update_source_node(obj_source_node)
                    data_access.update_node_relationship_count(file_name)
            
            
            # TODO 统计用户使用的token
          

            # 获取最新的Document信息
            result = data_access.get_current_status_document_node(file_name)
            is_cancelled_status = result[0]["is_cancelled"]
            if bool(is_cancelled_status) == True:
                logger.info("Document is Cancelled at the end extraction")
                job_status = "Cancelled"
            logger.info(f"Job Status at the end:{job_status}")
            end_time = datetime.now()
            processed_time = end_time - start_time
            obj_source_node = SourceNode()
            obj_source_node.file_name = file_name
            obj_source_node.status = job_status
            obj_source_node.processing_time = processed_time
            obj_source_node.token_usage = tokens_per_file

            # 更新最终doc node 信息
            data_access.update_source_node(obj_source_node)
            data_access.update_node_relationship_count(file_name)
            logger.info('Updated the nodeCount and relCount properties in Document node')
            logger.info(f'file:{params.file_name} extraction has been completed')
            
            # 删除处理完的本地文件
            if is_uploaded_from_local and bool(is_cancelled_status) == False:
                delete_uploaded_local_file(file_path)  
            
            # 计算总共处理Document的用时
            processing_source_func = time.time() - processing_source_start_time
            logger.info(f"Time taken to processing source function completed in {processing_source_func:.2f} seconds for file name {params.file_name}")  
            uri_latency["Processed_source"] = f'{processing_source_func:.2f}'
            
            # 统计本次处理Document的信息
            response["nodeCount"] = node_count
            response["relationshipCount"] = rel_count
            response["chunkNodeCount"] = result[0].get("chunkNodeCount",0)
            response["chunkRelCount"] = result[0].get("chunkRelCount",0)
            response["entityNodeCount"] = result[0].get("entityNodeCount",0)
            response["entityEntityRelCount"] = result[0].get("entityEntityRelCount",0)
            response["communityNodeCount"] = result[0].get("communityNodeCount",0)
            response["communityRelCount"] = result[0].get("communityRelCount",0)
            response["fileName"] = file_name
            response["total_processing_time"] = round(processed_time.total_seconds(),2)
            response["status"] = job_status
            response["model"] = params.model
            response["success_count"] = 1
    
            return uri_latency, response
        else:
            logger.info("Files does not process because its already in Processing status")
            return uri_latency, response
    else:
        err_msg = "Unable to get the Document node"
        logger.info(err_msg)
        raise Exception(err_msg)


async def extract_graph_from_file_local_file(credentials, params, file_path):
    logger.info(f"Process file name: {params.file_name} from local file system!")

    # 重试策略
    if params.retry_condition in ["", None] or params.retry_condition not in [
        DELETE_ENTITIES_AND_START_FROM_BEGINNING,
        START_FROM_LAST_PROCESSED_POSITION,
    ]:  
        # 1. loader文件 -> docs
        file_name, docs, _ = get_documents_from_file_by_path(
            file_path, params.file_name
        )
        if docs == None or len(docs) == 0:
            raise Exception(f"File content is not available for file : {file_name}")
        
        # 2. 分块docs -> chunks 并入库
        return await processing_source(credentials, params, docs, file_path, True)
    else:
        return await processing_source(credentials, params, [], file_path, True)


async def extract_graph_from_web_page(credentials, params): ...


async def extract_graph_from_file_bilibili(credentials, params): ...


async def extract_graph_from_file_Wikipedia(credentials, params): ...


async def graph_schema_consolidation(credentials):
    """ 整合图数据库的schema """
    graph = create_graph_database_connection(credentials)
    data_access = GraphDBDataAccess(graph)

    # 1. 获取原来的 node, relationship labels
    node_labels, relationship_labels = data_access.get_nodelabels_relationships()

    graph_clean_model = settings.GRAPH_CLEAN_MODEL
    llm,_,_ = get_llm(graph_clean_model)

    # 2. 构建LLM chain
    parser = JsonOutputParser()
    chain = llm | parser
    human_input = {'nodes': node_labels, 'relationships': relationship_labels}
    prompt = [SystemMessage(content=GRAPH_CLEANUP_PROMPT),
              HumanMessage(content=f"{human_input}")]
    
    # 3. 利用LLM来去重 node,relationship 进行清理
    mappings = await chain.ainvoke(prompt)
    node_mapping = {old: new for new, old_list in mappings['nodes'].items() for old in old_list if new != old}
    relation_mapping = {old: new for new, old_list in mappings['relationships'].items() for old in old_list if new != old}
    
    logger.info(f"Node Labels: Total = {len(node_labels)}, Reduced to = {len(set(node_mapping.values()))} (from {len(node_mapping)})")
    logger.info(f"Relationship Types: Total = {len(relationship_labels)}, Reduced to = {len(set(relation_mapping.values()))} (from {len(relation_mapping)})")

    # 4. 根据LLM的结果，重建node relationship
    data_access.node_relationship_consolidation(node_mapping, relation_mapping)





# ============ 知识图谱索引构建 =================
async def update_graph(credentials):
    graph = create_graph_database_connection(credentials)
    data_access = GraphDBDataAccess(graph)
    data_access.update_KNN_graph()


async def create_vector_fulltext_indexes(credentials):
    """ 对entity和chunk建立fulltext索引 """
    types = ["entities", "hybrid"]
    logger.info("Starting the process of creating full-text indexes.")

    graph = create_graph_database_connection(credentials)
    data_access = GraphDBDataAccess(graph)
    
    # 创建fulltext索引
    for index_type in types:
        data_access.create_fulltext_indexes(index_type)
    


# ============= Graph Chat相关 ===============
async def simple_graph_chat(credentials, model, question, document_names, session_id):
    """ 简单的图数据库聊天(cypher 生成)  """
    graph = create_graph_database_connection(credentials,refresh_schema=True)
    simple_rag_agent = SimpleGraphRagAgent(model, graph)
    agent = simple_rag_agent._create_agent()
    input = {
        "question": question,
        "messages": [HumanMessage(content=question)]
    }
    config = {"configurable": {"thread_id": session_id}}
    logger.info(f"input:{input}")
    try:
        async for event in agent.astream(input, config, stream_mode="updates"):
            # 遍历每个节点
            for node_name, node_data in event.items():
                if "messages" in node_data:
                    for msg in node_data["messages"]:
                        # 处理工具调用
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:

                            if msg.content:
                                yield json.dumps({
                                    "type": "assistant",
                                    "content": msg.content
                                }) + "\n"

                            for tool_call in msg.tool_calls:
                                tool_name = tool_call.get('name', 'unknown')
                                tool_args = tool_call.get('args', {})

                                # 发送工具调用事件
                                yield json.dumps({
                                    "type": "tool_call",
                                    "content": {
                                        "name": tool_name,
                                        "args": tool_args
                                    }
                                }) + "\n"

                        # 处理工具结果
                        elif isinstance(msg, ToolMessage):
                            tool_name = getattr(msg, 'name', 'tool')
                            tool_result = str(msg.content)

                            # 发送工具结果事件
                            yield json.dumps({
                                "type": "tool_result",
                                "content": {
                                    "name": tool_name,
                                    "result": tool_result
                                }
                            }) + "\n"

                        # 处理 AI 消息
                        elif isinstance(msg, AIMessage) and msg.content:
                            # 发送 AI 响应事件
                            yield json.dumps({
                                "type": "assistant",
                                "content": msg.content
                            }) + "\n"

        # 发送完成事件
        yield json.dumps({"type": "done", "content": None}) + "\n"

    except Exception as e:
        # 发送错误事件
        yield json.dumps({
            "type": "error",
            "content": str(e)
        }) + "\n"
        raise e
 


