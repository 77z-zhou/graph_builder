import time
import hashlib
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_neo4j.graphs.graph_document import GraphDocument
from langchain_core.documents import Document
from neo4j.exceptions import TransientError


from config import settings
from .embedding import load_embedding_model
from .common.cyphers import *
from app_entities import SourceNode
import logging

logger = logging.getLogger(__name__)
load_dotenv(override=True)


class GraphDBDataAccess:

    def __init__(self, graph: Neo4jGraph):
        self.graph = graph

    def execute_query(self, query, param: dict = None, max_retries=3, delay=2):
        """重写query, 增加了重试机制"""
        retries = 0
        while retries < max_retries:
            try:
                return self.graph.query(
                    query, param, session_params={"database": self.graph._database}
                )
            except TransientError as e:
                if "DeadlockDetected" in str(e):
                    retries += 1
                    logger.info(
                        f"Deadlock detected. Retrying {retries}/{max_retries} in {delay} seconds..."
                    )
                    time.sleep(delay)  # Wait before retrying
                else:
                    raise
        logger.error(
            "Failed to execute query after maximum retries due to persistent deadlocks."
        )
        raise RuntimeError(
            "Query execution failed after multiple retries due to deadlock."
        )

    def update_exception_db(self, file_name, err_msg, retry_condition=None):
        """ document Node 的错误更新 """
        try:
            job_status = "Failed"
            result = self.get_current_status_document_node(file_name)
            if len(result) > 0:
                is_cancelled_status = result[0]["is_cancelled"]
                if bool(is_cancelled_status) == True:
                    job_status = "Cancelled"

            if retry_condition is not None:
                retry_condition = None
                cypher1 = """MERGE(d:Document {fileName :$fName}) 
                            SET d.status = $status, d.errorMessage = $error_msg, 
                                d.retry_condition = $retry_condition"""
                self.graph.query(
                    cypher1,
                    {
                        "fName": file_name,
                        "status": job_status,
                        "error_msg": err_msg,
                        "retry_condition": retry_condition,
                    },
                    session_params={"database": self.graph._database},
                )
            else:
                cypher2 = """MERGE(d:Document {fileName :$fName}) 
                             SET d.status = $status, d.errorMessage = $error_msg"""
                self.graph.query(
                    cypher2,
                    {"fName": file_name, "status": job_status, "error_msg": err_msg},
                    session_params={"database": self.graph._database},
                )
        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error in updating document node status as failed: {error_message}"
            )
            raise e

    # ========== 新增方法 =================

    # 新增Document Node
    def create_source_node(self, obj_source_node: SourceNode):
        """创建Document Node"""
        try:
            job_status = "New"
            logger.info(f"Creating source node if does not exist in database.")

            create_document_cypher = (
                "MERGE(d:Document{fileName :$fn})"
                "SET d.fileSize = $fs, d.fileType = $ft, d.status = $st,"
                "d.url = $url, d.awsAccessKeyId = $awsacc_key_id, d.fileSource = $f_source,"
                "d.createdAt = $c_at, d.updatedAt = $u_at, d.processingTime = $pt,"
                "d.errorMessage = $e_message, d.nodeCount= $n_count,"
                "d.relationshipCount = $r_count, d.model= $model,"
                "d.gcsBucket=$gcs_bucket, d.gcsBucketFolder= $gcs_bucket_folder, d.gcsProjectId= $gcs_project_id,"
                "d.language= $language, "
                "d.is_cancelled=False, "
                "d.total_chunks=0, d.processed_chunk=0,"
                "d.access_token=$access_token,"
                "d.chunkNodeCount=$chunkNodeCount,d.chunkRelCount=$chunkRelCount,"
                "d.entityNodeCount=$entityNodeCount,d.entityEntityRelCount=$entityEntityRelCount,"
                "d.communityNodeCount=$communityNodeCount,d.communityRelCount=$communityRelCount"
            )
            params = {
                "fn": obj_source_node.file_name,
                "fs": obj_source_node.file_size,
                "ft": obj_source_node.file_type,
                "st": job_status,
                "url": obj_source_node.url,
                "awsacc_key_id": obj_source_node.awsAccessKeyId,
                "f_source": obj_source_node.file_source,
                "c_at": obj_source_node.created_at,
                "u_at": obj_source_node.created_at,
                "pt": 0,
                "e_message": "",
                "n_count": 0,
                "r_count": 0,
                "model": obj_source_node.model,
                # gcs 相关 后面替换成OSS
                "gcs_bucket": obj_source_node.gcsBucket,
                "gcs_bucket_folder": obj_source_node.gcsBucketFolder,
                "gcs_project_id": obj_source_node.gcsProjectId,
                "language": obj_source_node.language,
                "access_token": obj_source_node.access_token,
                "chunkNodeCount": obj_source_node.chunkNodeCount,
                "chunkRelCount": obj_source_node.chunkRelCount,
                "entityNodeCount": obj_source_node.entityNodeCount,
                "entityEntityRelCount": obj_source_node.entityEntityRelCount,
                "communityNodeCount": obj_source_node.communityNodeCount,
                "communityRelCount": obj_source_node.communityRelCount,
            }
            self.graph.query(
                create_document_cypher,
                params,
                session_params={"database": self.graph._database},
            )
        except Exception as e:
            # 创建Node 失败
            error_message = str(e)
            logger.error(f"error_message = {error_message}")
            # 更新Node的状态 为 Cancelled or Failed
            self.update_exception_db(obj_source_node.file_name, error_message)
            raise Exception(error_message)

    # 新增Chunk Node 和 建立 Doc, Chunk 等relationships
    def create_relation_between_chunks(self, file_name, chunks: list[Document]):
        """
        创建Chunk Node 与 Document建立relationship,
        并在Chunks 间建立 relationship
        """

        logger.info("Create First Chunk and Next Chunk relationships between chunks")
        current_chunk_id = ""
        lst_chunks_including_hash = []
        batch_data = []
        relationships = []
        offset = 0
        for i, chunk in enumerate(chunks):
            page_content_shai = hashlib.sha1(chunk.page_content.encode())
            previous_chunk_id = current_chunk_id
            current_chunk_id = page_content_shai.hexdigest()
            position = i + 1
            if i > 0:
                offset += len(chunks[i - 1].page_content)
            if i == 0:
                firstChunk = True
            else:
                firstChunk = False

            # 构造chunk Node 数据
            chunk_data = {
                "id": current_chunk_id,
                "pg_content": chunk.page_content,
                "position": position,
                "length": len(chunk.page_content),
                "f_name": file_name,
                "previous_id": previous_chunk_id,
                "content_offset": offset,
            }
            if "page_number" in chunk.metadata:
                chunk_data["page_number"] = chunk.metadata["page_number"]

            if (
                "start_timestamp" in chunk.metadata
                and "end_timestamp" in chunk.metadata
            ):
                chunk_data["start_time"] = chunk.metadata["start_timestamp"]
                chunk_data["end_time"] = chunk.metadata["end_timestamp"]
            batch_data.append(chunk_data)

            lst_chunks_including_hash.append(
                {"chunk_id": current_chunk_id, "chunk_doc": chunk}
            )

            # 创建chunk间的 relationships
            if firstChunk:
                relationships.append(
                    {"type": "FIRST_CHUNK", "chunk_id": current_chunk_id}
                )
            else:
                relationships.append(
                    {
                        "type": "NEXT_CHUNK",
                        "previous_chunk_id": previous_chunk_id,
                        "current_chunk_id": current_chunk_id,
                    }
                )

        # 1. 创建 chunk Node 并与 Document 建立 relationship(PART_OF)
        create_chunk_and_relation_to_doc = """
            UNWIND $batch_data AS data
            MERGE (c:Chunk {id: data.id})
            SET c.text = data.pg_content, c.position = data.position, c.length = data.length, 
                c.fileName=data.f_name, c.content_offset=data.content_offset,
                c.page_number = CASE WHEN data.page_number IS NOT NULL THEN data.page_number END,
                c.start_time = CASE WHEN data.start_time IS NOT NULL THEN data.start_time END,
                c.end_time = CASE WHEN data.end_time IS NOT NULL THEN data.end_time END
            WITH data, c
            MATCH (d:Document {fileName: data.f_name})
            MERGE (c)-[:PART_OF]->(d)
        """
        self.execute_query(
            create_chunk_and_relation_to_doc, param={"batch_data": batch_data}
        )

        # 2. Document到其第一个Chunk建立relationship为FIRST_CHUNK
        create_first_chunk_relation = """
            UNWIND $relationships AS relationship
            MATCH (d:Document {fileName: $f_name})
            MATCH (c:Chunk {id: relationship.chunk_id})
            FOREACH (r IN CASE WHEN relationship.type = 'FIRST_CHUNK' THEN [1] ELSE [] END |
                    MERGE (d)-[:FIRST_CHUNK]->(c))
        """
        self.execute_query(
            create_first_chunk_relation,
            param={"relationships": relationships, "f_name": file_name},
        )

        # 3. 建立Chunk之间的关系 NEXT_CHUNK
        create_next_chunk_relation_between_chunk = """
            UNWIND $relationships AS relationship
            MATCH (c:Chunk {id: relationship.current_chunk_id})
            WITH c, relationship
            MATCH (pc:Chunk {id: relationship.previous_chunk_id})
            FOREACH (r IN CASE WHEN relationship.type = 'NEXT_CHUNK' THEN [1] ELSE [] END |
                    MERGE (pc)-[:NEXT_CHUNK]->(c))
        """
        self.execute_query(
            create_next_chunk_relation_between_chunk,
            param={"relationships": relationships},
        )

        return lst_chunks_including_hash



    def create_chunk_embeddings(self, chunks, file_name):
        """ 给chunk创建embedding向量 """
        embeddings, dimension = load_embedding_model(settings.EMBEDDING_MODEL)
        logger.info(f"embedding model: {embeddings} and dimension: {dimension}")

        embedding_chunks = []

        for row in chunks:
            embedding_vector = embeddings.embed_query(row['chunk_doc'].page_content)
            embedding_chunks.append({
                "id": row['chunk_id'],
                "embeddings": embedding_vector
            })

        self.execute_query(CREATE_OR_UPDATE_CHUNK_EMBEDDING, param={"data": embedding_chunks, "f_name": file_name})
        

    def save_graph_documents(self, graph_documents: list[GraphDocument], max_retries=3, delay=1):
        """ 保存知识图谱 """
        retries = 0
        while retries < max_retries:
            try: 
                self.graph.add_graph_documents(graph_documents)
                return
            except TransientError as e:
                if "DeadlockDetected" in str(e):
                    retries += 1
                    logger.info(f"Deadlock detected. Retrying {retries}/{max_retries} in {delay} seconds...")
                    time.sleep(delay)  # Wait before retrying
                else:
                    raise
        logger.error("Failed to execute query after maximum retries due to persistent deadlocks.")
        raise RuntimeError("Query execution failed after multiple retries due to deadlock.")


    def merge_relationship_between_chunk_and_graph_entities(self, graph_documents: list[GraphDocument]):
        # 1. 一个graph_doc 对应多个 chunk
        chunk_graph_docs = []
        for graph_doc in graph_documents:
            for chunk_id in graph_doc.source.metadata["combined_chunk_ids"]:
                chunk_graph_docs.append({"graph_doc": graph_doc, "chunk_id": chunk_id})
        
        # 2. 构建入参
        batch_data = []
        for chunk_graph_doc in chunk_graph_docs:
            for node in chunk_graph_doc['graph_doc'].nodes:
                data = {
                    "chunk_id": chunk_graph_doc["chunk_id"],
                    "node_id": node.id,
                    "node_type": node.type
                }
                batch_data.append(data)

        # 3. 批量创建关系
        if batch_data:
            self.execute_query(MERGE_CHUNK_AND_ENTITES_RELATION, param={"batch_data":batch_data})
        

    def node_relationship_consolidation(self,node_mapping, relation_mapping):
        try:
            if node_mapping:
                for old_label, new_label in node_mapping.items():
                    query = f"""
                            MATCH (n:`{old_label}`)
                            SET n:`{new_label}`
                            REMOVE n:`{old_label}`
                            """
                    self.execute_query(query)

            for old_label, new_label in relation_mapping.items():
                query = f"""
                        MATCH (n)-[r:`{old_label}`]->(m)
                        CREATE (n)-[r2:`{new_label}`]->(m)
                        DELETE r
                        """
                self.execute_query(query)
        except Exception as e:
            logger.error(f"Error in node_relationship_consolidation: {e}")
            raise e

    # ========== 更新方法 =================
    def update_source_node(self, obj_source_node: SourceNode):
        try:
            params = {}
            if (
                obj_source_node.file_name is not None
                and obj_source_node.file_name != ""
            ):
                params["fileName"] = obj_source_node.file_name

            if obj_source_node.status is not None and obj_source_node.status != "":
                params["status"] = obj_source_node.status

            if obj_source_node.created_at is not None:
                params["createdAt"] = obj_source_node.created_at

            if obj_source_node.updated_at is not None:
                params["updatedAt"] = obj_source_node.updated_at

            if (
                obj_source_node.processing_time is not None
                and obj_source_node.processing_time != 0
            ):
                params["processingTime"] = round(
                    obj_source_node.processing_time.total_seconds(), 2
                )

            if obj_source_node.node_count is not None:
                params["nodeCount"] = obj_source_node.node_count

            if obj_source_node.relationship_count is not None:
                params["relationshipCount"] = obj_source_node.relationship_count

            if obj_source_node.model is not None and obj_source_node.model != "":
                params["model"] = obj_source_node.model

            if (
                obj_source_node.total_chunks is not None
                and obj_source_node.total_chunks != 0
            ):
                params["total_chunks"] = obj_source_node.total_chunks

            if obj_source_node.is_cancelled is not None:
                params["is_cancelled"] = obj_source_node.is_cancelled

            if obj_source_node.processed_chunk is not None:
                params["processed_chunk"] = obj_source_node.processed_chunk

            if obj_source_node.retry_condition is not None:
                params["retry_condition"] = obj_source_node.retry_condition

            if obj_source_node.token_usage is not None:
                params["token_usage"] = obj_source_node.token_usage
            param = {"props": params}

            cypher = "MERGE (d:Document {fileName: $props.fileName}) SET d += $props"
            self.execute_query(cypher, param=param)
        except Exception as e:
            error_message = str(e)
            self.update_exception_db(obj_source_node.file_name, error_message)
            raise Exception(error_message)

    def update_node_relationship_count(self, file_name):
        """ 校准更新节点和关系数量 """
        logger.info("Updating node and relationship count!!")
        try:
            # 判断__Community__ Label 是否存在
            label_query = """CALL db.labels"""  # 获取所有Node节点标签
            community_flag = {'label': '__Community__'} in self.execute_query(label_query)
            
            # 1. 统计所有文件和community相关信息
            if not file_name and community_flag:
                #TODO 待完善
                result = self.execute_query()
            # 2. 啥也没有
            elif not file_name and not community_flag:
                result = self.execute_query(NODEREL_COUNT_QUERY_WITHOUT_COMMUNITY)
            # 3. 统计指定文件的信息(不包含community)
            else:
                param = {"f_name": file_name}
                result = self.execute_query(NODEREL_COUNT_QUERY_WITHOUT_COMMUNITY_BY_FILE_NAME, param)
            
            response = {}
            if result:
                for record in result:
                    fileName = record.get("fileName")
                    chunkNodeCount = int(record.get("chunkNodeCount",0))
                    chunkRelCount = int(record.get("chunkRelCount",0))
                    entityNodeCount = int(record.get("entityNodeCount",0))
                    entityEntityRelCount = int(record.get("entityEntityRelCount",0))
                    if not fileName and community_flag:
                        communityNodeCount = int(record.get("communityNodeCount",0))
                        communityRelCount = int(record.get("communityRelCount",0))
                    else:
                        communityNodeCount = 0
                        communityRelCount = 0
                    nodeCount = int(chunkNodeCount) + int(entityNodeCount) + int(communityNodeCount)
                    relationshipCount = int(chunkRelCount) + int(entityEntityRelCount) + int(communityRelCount)
                    param = {
                        "f_name": fileName,
                        "chunkNodeCount": chunkNodeCount,
                        "chunkRelCount": chunkRelCount,
                        "entityNodeCount": entityNodeCount,
                        "entityEntityRelCount": entityEntityRelCount,
                        "communityNodeCount": communityNodeCount,
                        "communityRelCount": communityRelCount,
                        "nodeCount": nodeCount,
                        "relationshipCount": relationshipCount
                    }
                    
                    # 更新Document的统计数量
                    self.execute_query(UPDATE_DOCUMENT_NODE, param)
                    response[fileName] = {
                        "chunkNodeCount": chunkNodeCount,
                        "entityNodeCount": entityNodeCount,
                        "entityEntityRelCount": entityEntityRelCount,
                        "communityNodeCount": communityNodeCount,
                        "communityRelCount": communityRelCount,
                        "nodeCount": nodeCount,
                        "relationshipCount": relationshipCount
                    }
            return response          
        except Exception as e:
            error_message = str(e)
            self.update_exception_db(file_name, error_message)
            raise e
   


    # ========= 查询方法 ================
    def get_current_status_document_node(self, file_name):
        """查询文档节点的当前状态"""
        query = """
                MATCH(d:Document {fileName : $file_name}) 
                RETURN d.status AS Status , d.processingTime AS processingTime, 
                d.model as model,
                d.nodeCount AS nodeCount,
                d.relationshipCount as relationshipCount,
                d.total_chunks AS total_chunks , d.fileSize as fileSize, 
                d.processed_chunk as processed_chunk, d.fileSource as fileSource,
                d.chunkNodeCount AS chunkNodeCount,
                d.chunkRelCount AS chunkRelCount,
                d.entityNodeCount AS entityNodeCount,
                d.entityEntityRelCount AS entityEntityRelCount,
                d.communityNodeCount AS communityNodeCount,
                d.communityRelCount AS communityRelCount,
                d.createdAt AS created_time,
                d.is_cancelled as is_cancelled,
                coalesce(d.token_usage, 0) AS token_usage
                """
        param = {"file_name": file_name}
        return self.execute_query(query, param)

    def get_chunks_by_fileName(self, file_name):
        """根据文件名 获取其chunks"""

        query_chunks_by_fileName = """
            MATCH (d:Document {fileName: $f_name})
            WITH d
            OPTIONAL MATCH (d)<-[:PART_OF]-(c:Chunk)
            RETURN c.id as id, c.text as text, c.position as position
        """
        return self.execute_query(query_chunks_by_fileName, param={"f_name": file_name})

    def get_last_processed_chunk(self, file_name):
        """根据文件名 找到第一个还没有Embedding的chunk"""
        cypher = """
            MATCH (d:Document {fileName: $f_name})
            WITH d
            MATCH (c:Chunk)-[:PART_OF]->(d)
            WHERE c.embedding IS NULL
            RETURN c.id as id, c.position as position
            ORDER BY c.position LIMIT 1
        """
        return self.execute_query(cypher, param={"f_name": file_name})

    def get_last_processed_without_entity_chunk(self, file_name):
        """根据文件名 找到还没有进行 Entity实体抽取的 chunk"""
        cypher = """
            MATCH (d:Document {fileName: $f_name})
            WITH d
            MATCH (c:Chunk)-[:PART_OF]->(d)
            WHERE NOT exists {(c)-[:HAS_ENTITY]->()}
            RETURN c.id as id, c.position as position
            ORDER BY c.position LIMIT 1
        """
        return self.execute_query(cypher, param={"f_name": file_name})

    def get_nodelabels_relationships(self):
        """ 获取所有节点标签和关系类型 """
        try:
            node_result = self.execute_query(GET_NODE_LABELS)
            node_labels = [record["label"] for record in node_result]

            relationship_result = self.execute_query(GET_RELATIONSHIPS)
            relationship_types = [record["relationshipType"] for record in relationship_result]
            
            return node_labels, relationship_types
        except Exception as e:
            logger.error(f"Error in getting node labels/relationship types from db: {e}")
            return []



    # ========= 连接相关 ===================
    def check_gds_version(self):
        """
        GDS 是 Neo4j 的 图数据科学库，
        提供了丰富的图算法和机器学习功能，用于分析图数据中的模式、关系和结构。
        """

        try:
            gds_procedure_count = """
            SHOW FUNCTIONS YIELD name WHERE name STARTS WITH 'gds.version' RETURN COUNT(*) AS totalGdsProcedures
            """
            result = self.graph.query(
                gds_procedure_count, session_params={"database": self.graph._database}
            )
            total_gds_procedures = result[0]["totalGdsProcedures"] if result else 0

            if total_gds_procedures > 0:
                logger.info("GDS is available in the database.")
                return True
            else:
                logger.info("GDS is not available in the database.")
                return False
        except Exception as e:
            logger.error(f"An error occurred while checking GDS version: {e}")
            return False
    
    def connection_check_and_get_vector_dimensions(self):

        # 查询 vector 索引的 维度
        cypher1 = (
            "SHOW INDEXES YIELD *"
            "WHERE type = 'VECTOR' AND name = 'vector'"
            "RETURN options.indexConfig['vector.dimensions'] AS vector_dimensions"
        )
        db_vector_dimension = self.graph.query(
            cypher1, session_params={"database": self.graph._database}
        )

        # 查询embedding chunk的分布
        cypher2 = (
            "MATCH (c:Chunk)"
            "return SIZE(c.embedding) as embeddingSize, COUNT(*) as chunks, COUNT(c.embedding) as hasEmbedding"
        )
        result_chunks = self.graph.query(
            cypher2, session_params={"database": self.graph._database}
        )

        embedding_model = settings.EMBEDDING_MODEL
        _, application_dimension = load_embedding_model(embedding_model)

        gds_status = self.check_gds_version()

        if self.graph:
            if len(db_vector_dimension) > 0:
                return {
                    "db_vector_dimension": db_vector_dimension[0]["vector_dimensions"],
                    "application_dimension": application_dimension,
                    "message": "Connection Successful",
                    "gds_status": gds_status,
                    "write_access": True,
                }
            else:
                if len(db_vector_dimension) == 0 and len(result_chunks) == 0:
                    logger.info("Chunks and vector index does not exists in database")
                    return {
                        "db_vector_dimension": 0,
                        "application_dimension": application_dimension,
                        "message": "Connection Successful",
                        "chunks_exists": False,
                        "gds_status": gds_status,
                        "write_access": True,
                    }
                elif (
                    len(db_vector_dimension) == 0
                    and result_chunks[0]["hasEmbedding"] == 0
                    and result_chunks[0]["chunks"] > 0
                ):
                    return {
                        "db_vector_dimension": 0,
                        "application_dimension": application_dimension,
                        "message": "Connection Successful",
                        "chunks_exists": True,
                        "gds_status": gds_status,
                        "write_access": True,
                    }
                else:
                    return {
                        "message": "Connection Successful",
                        "gds_status": gds_status,
                        "write_access": True,
                    }



    # ========= 索引相关 ===================
    def create_chunk_vector_index(self):
        """ 给chunk创建向量索引 """
        
        start_time = time.time()
        try:
            cypher = (
                "SHOW INDEXES YIELD name, type, labelsOrTypes, properties "
                "WHERE name = 'vector' AND type = 'VECTOR'"
                "AND 'Chunk' IN labelsOrTypes AND 'embedding' IN properties "
                "RETURN name"
            )

            vector_index = self.execute_query(cypher)
            if not vector_index:
                EMBEDDING_FUNCTION, EMBEDDING_DIMENSION = load_embedding_model(
                    settings.EMBEDDING_MODEL
                )

                # 创建 neo4j向量
                vector_store = Neo4jVector(
                    embedding=EMBEDDING_FUNCTION,
                    graph=self.graph,
                    node_label="Chunk",
                    embedding_node_property="embedding",
                    index_name="vector",
                    embedding_dimension=EMBEDDING_DIMENSION,
                )
                vector_store.create_new_index()
                logger.info(
                    f"Index created successfully. Time taken: {time.time() - start_time:.2f} seconds"
                )
            else:
                logger.info(
                    f"Index already exist,Skipping creation. Time taken: {time.time() - start_time:.2f} seconds"
                )
        except Exception as e:
            if "EquivalentSchemaRuleAlreadyExists" in str(
                e
            ) or "An equivalent index already exists" in str(e):
                logger.info("Vector index already exists, skipping creation.")
            else:
                raise

   
    def update_KNN_graph(self):
        """ 根据embedding分数匹配更新具有相似关系的图节点 """

        # 1. 获取vector索引
        index = self.execute_query(GET_VECTOR_INDEX)

        # 建立KNN相似度阈值
        knn_min_score = settings.KNN_MIN_SCORE

        if len(index) > 0:
            logger.info("Update KNN Graph")
            # 2. 创建或更新相似关系
            self.execute_query(CREATE_OR_UPDATE_SIMILAR_CHUNK_RELATIONSHIP, param={"score":knn_min_score})
    
        else:
            logger.info("No vector index found, so KNN not update")
        

    def create_fulltext_indexes(self, type):
        """ 建立全文索引 """
        start = time.time()
        driver = self.graph._driver
        try:
            with driver.session() as session:
                # 1. drop
                try:
                    start_step = time.time()
                    if type == "entities":
                        drop_cypher = DROP_INDEX_ENTITIES
                    elif type == "hybrid":
                        drop_cypher = DROP_INDEX_HYBRID_SEARCH
                    else:
                        drop_cypher = DROP_INDEX_COMMUNITY
                    session.run(drop_cypher)
                    logger.info(f"Dropped existing index (if any) in {time.time() - start_step:.2f} seconds.")
                except Exception as e:
                    logger.error(f"Failed to drop index type:{type}, error:{e}")
                    return

                # 2. 针对 entities 过滤不需要创建fulltext的标签
                try:
                    if type == "entities":
                        start_step = time.time()
                        result = session.run("CALL db.labels()") # 查询所有标签
                        labels = [record["label"] for record in result if record["label"] not in FILTER_LABELS]
                         
                        if labels:
                            labels_str = ":" + "|".join([f"`{label}`" for label in labels])
                            logger.info(f"Labels to be indexed: {labels_str}")
                            logger.info(f"Fetched labels in {time.time() - start_step:.2f} seconds.")
                        else:
                            logger.info("Full text index is not created as labels are empty")
                            return
                except Exception as e:
                    logger.error(f"Failed to fetch labels: {e}")
                    return
                
                # 3. 创建索引
                try:
                    start_step = time.time()
                    if type == "entities":
                        fulltext_cypher = CREATE_FULL_TEXT_INDEX_ENTITIES.format(labels_str=labels_str)
                    elif type == "hybrid":
                        fulltext_cypher = CREATE_FULL_TEXT_INDEX_HYBRID_SEARCH
                    else:
                        fulltext_cypher = CREATE_FULL_TEXT_INDEX_COMMUNITY
                    logger.info(f"Creating fulltext_cypher : {fulltext_cypher}")
                    session.run(fulltext_cypher)
                    logger.info(f"Created full-text index in {time.time() - start_step:.2f} seconds.")
                except Exception as e:
                    logger.error(f"Failed to create full-text index: {e}")
                    return
        except Exception as e:
            logger.error(f"An error occurred during the session: {e}")
            raise e
        finally:
            logger.info(f"Process completed in {time.time() - start:.2f} seconds.")
