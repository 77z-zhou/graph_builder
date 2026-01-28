import os
import gc
import time
import logging
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from langchain_neo4j import Neo4jGraph


from utils import formatted_time, validate_file_path
from config import settings
from app_entities import *
from service import *


logger = logging.getLogger(__name__)
CHUNK_DIR = os.path.join(os.path.dirname(__file__), "chunks")
MERGED_DIR = os.path.join(os.path.dirname(__file__), "merged_files")


router = APIRouter()


# ========= 知识图谱聊天 =========
@router.post("/chat")
async def chat_bot(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    model=Form(None),
    question=Form(None),
    document_names=Form(None),
    session_id=Form(None),
    mode=Form(None)
):
    """ 知识图谱聊天 """
    try:
        return StreamingResponse(
            simple_graph_chat(credentials, model, question, document_names, session_id, mode),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    finally:
        gc.collect()


   






    


# =========== 上传相关 ==================
@router.post("/upload")
async def upload_large_file_into_chunks(
    file: UploadFile = File(...),
    chunkNumber=Form(None),
    totalChunks=Form(None),
    originalname=Form(None),
    model=Form(None),
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials)
):
    """ 分块上传 大型文件  为文件创建Document Node"""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials) # 创建数据库连接
        result = await asyncio.to_thread(upload_file, graph, model, file, chunkNumber, totalChunks, originalname, CHUNK_DIR, MERGED_DIR)
        end = time.time()
        elapsed_time = end - start

        # 文件分块传输完成
        if int(chunkNumber) == int(totalChunks):
            json_obj = {'api_name':'upload','db_url':credentials.uri,
                        'userName':credentials.userName, 'database':credentials.database, 
                        'chunkNumber':chunkNumber,'totalChunks':totalChunks,
                        'filename':originalname,'model':model, 'email':credentials.email,
                        'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}'}
            logger.info(f"Upload log obj:{json_obj}")
            return create_api_response('Success', data=result, message='Source Node Created Successfully')
        else:
            return create_api_response('Success', message=result)
    except Exception as e:
        message="Unable to upload file in chunks"
        error_message = str(e)
        graph = create_graph_database_connection(credentials)   
        update_exception(graph, originalname, error_message)
        logger.info(message)
        logger.exception(f'Exception:{error_message}')
        return create_api_response('Failed', message=message + error_message[:100], error=error_message, file_name = originalname)
    finally:
        gc.collect()

@router.post("/url/scan")
async def create_source_knowledge_graph_url():
    ...


# =========== 知识图谱提取相关 =================
@router.post("/extract")  # 核心方法
async def extract_knowledge_graph_from_file(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    params: SourceScanExtractParams = Depends(get_source_scan_extract_params)
):
    """ 从本地文件或者远程URL(bilibil) 等进行知识图谱抽取 """

    try:
        start = time.time()      
        # 1. 本地文件抽取
        if params.source_type == 'local_file':
            file_name = params.file_name
            merged_file_path = validate_file_path(MERGED_DIR, file_name)
            uri_latency, result = await extract_graph_from_file_local_file(credentials, params, merged_file_path)
        
        # 2. web url文件抽取
        elif params.source_type == 'web-url':
            uri_latency, result = await extract_graph_from_web_page(credentials, params)

        # 3. bilibli 抽取
        elif params.source_type == 'bilibili' and params.source_url:
            uri_latency, result = await extract_graph_from_file_bilibili(credentials, params)
        
        # 4. wikipedia抽取
        elif params.source_type == 'Wikipedia' and params.wiki_query:
            uri_latency, result = await extract_graph_from_file_Wikipedia(credentials, params)

        # 5. 不存在的类型
        else:
            return create_api_response('Failed', message='source_type is other than accepted source')
        extract_api_time = time.time() - start
        logger.info(f"extraction completed in {extract_api_time:.2f} seconds for file name {params.file_name}")

        extract_info = result.copy()

        result.update(uri_latency)
        return create_api_response('Success', data=result, file_source=params.source_type)
    except Exception as e:
        message="Unable to extract knowledge graph"
        error_message = str(e)
        logger.error(message)
        return create_api_response('Failed',file_name=params.file_name, message=message + error_message[:100], error=error_message)
    finally:
        gc.collect()



@router.post("/backend_connection_configuration")
async def backend_connection_configuration():
    """ Neo4j 数据库连接 """
    try:
        start = time.time()
        uri = settings.NEO4J_URI
        username = settings.NEO4J_USERNAME
        password = settings.NEO4J_PASSWORD
        database = settings.NEO4J_DATABASE

        if all([uri, username, database, password]):
            graph = Neo4jGraph()
            logger.info(f"login connection status of object: {graph}")

            if graph is not None:
                graph_connection = True
                result = await asyncio.to_thread(connection_check_and_get_vector_dimensions, graph)
                result['uri'] = uri
                end = time.time()
                elapsed_time = end - start
                result['api_name'] = 'backend_connection_configuration'
                result['elapsed_api_time'] = f'{elapsed_time:.2f}'
                result['graph_connection'] = f'{graph_connection}',
                result['connection_from'] = 'backendAPI'
                return create_api_response('Success',message=f"Backend connection successful",data=result)
        else:
            graph_connection = False
            return create_api_response('Success', message=f"Backend connection is not successful",data=graph_connection)
    except Exception as e:
        graph_connection = False
        message="Unable to connect backend DB"
        error_message = str(e)
        logger.error(f'{error_message}')
        return create_api_response("Failed", message=message, error=error_message.rstrip('.') + ', or fill from the login dialog.', data=graph_connection)
    finally:
        gc.collect()


# ========== 索引相关 =========
@router.post("/post_processing")
async def post_processing(
    tasks=Form(None),
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials)
):
    try:
        start = time.time()

        # 实现文本块相似性 
        if "materialize_text_chunk_similarities" in tasks:
            await update_graph(credentials)
            logger.info(f"Updated KNN Graph")

        # 混合搜索和全文搜索
        if "enable_fulltext_search" in tasks:
            await create_vector_fulltext_indexes(credentials)
            logger.info(f"fulltext indexes created")

        # TODO 根据实体创建KNN 和 Vector索引

        # graph schema 整合
        if "graph_schema_consolidation" in tasks:
            await graph_schema_consolidation(credentials)
            logger.info(f"Updated nodes and relationship labels")

        # TODO 创建communities
        # if "enable_communities" in tasks:
        #     await asyncio.to_thread(create_communities, credentials)
        #     logger.info(f"created communities")

        count_res = update_node_relationship_count(credentials)
        if count_res:
            count_res = [{"filename": filename, **counts} for filename, counts in count_res.items()]
            logging.info(f'Updated source node with community related counts')
        
        end = time.time()
        elapsed_time = end - start
        logger.info(f"Post processing completed in {elapsed_time:.2f} seconds")
        return create_api_response('Success', data=count_res, message='All tasks completed successfully')
    except Exception as e:
        job_status = "Failed"
        error_message = str(e)
        message = f"Unable to complete tasks"
        logging.exception(f'Exception in post_processing tasks: {error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()




    






