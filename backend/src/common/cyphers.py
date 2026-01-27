FILTER_LABELS = ["Chunk","Document","__Community__"]



# 节点关系计数(包含Community)
NODEREL_COUNT_QUERY_WITH_COMMUNITY = """
MATCH (d:Document)
WHERE d.fileName IS NOT NULL
OPTIONAL MATCH (d)<-[po:PART_OF]-(c:Chunk)
OPTIONAL MATCH (c)-[he:HAS_ENTITY]->(e:__ENTITY__)
OPTIONAL MATCH (c)-[sim:SIMILAR]->(c2:Chunk)
OPTIONAL MATCH (c)-[nc:NEXT_CHUNK]->(c3:Chunk)
"""

# 获取所有Document节点关系计数(不包含Community) 
NODEREL_COUNT_QUERY_WITHOUT_COMMUNITY = """
MATCH (d:Document)
OPTIONAL MATCH (d)<-[po:PART_OF]-(c:Chunk)
OPTIONAL MATCH (c)-[he:HAS_ENTITY]->(e:__Entity__)
OPTIONAL MATCH (c)-[sim:SIMILAR]->(c2:Chunk)
OPTIONAL MATCH (c)-[nc:NEXT_CHUNK]->(c3:Chunk)
WITH
    d.fileName AS fileName,
    count(DISTINCT c) AS chunkNodeCount,
    count(DISTINCT po) AS partOfRelCount,
    count(DISTINCT he) AS hasEntityRelCount,
    count(DISTINCT sim) AS similarRelCount,
    count(DISTINCT nc) AS nextChunkRelCount,
    count(DISTINCT e) AS entityNodeCount,
    collect(DISTINCT e) AS entities
WITH
    fileName,
    chunkNodeCount,
    partOfRelCount + hasEntityRelCount + similarRelCount + nextChunkRelCount AS chunkRelCount,
    entityNodeCount,
    entities
CALL (entities) {
    UNWIND entities AS e
    RETURN sum(COUNT { (e)-->(e2:__Entity__) WHERE e2 in entities }) AS entityEntityRelCount
}
RETURN 
    fileName,
    COALESCE(chunkNodeCount, 0) AS chunkNodeCount,
    COALESCE(chunkRelCount, 0) AS chunkRelCount,
    COALESCE(entityNodeCount, 0) AS entityNodeCount,
    COALESCE(entityEntityRelCount, 0) AS entityEntityRelCount
"""




# 根据fileName 获取Document节点关系计数(不包含Community) 
NODEREL_COUNT_QUERY_WITHOUT_COMMUNITY_BY_FILE_NAME = """
MATCH (d:Document {fileName:$f_name})
OPTIONAL MATCH (d)<-[po:PART_OF]-(c:Chunk)
OPTIONAL MATCH (c)-[he:HAS_ENTITY]->(e:__Entity__)
OPTIONAL MATCH (c)-[sim:SIMILAR]->(c2:Chunk)
OPTIONAL MATCH (c)-[nc:NEXT_CHUNK]->(c3:Chunk)
WITH
    d.fileName AS fileName,
    count(DISTINCT c) AS chunkNodeCount,
    count(DISTINCT po) AS partOfRelCount,
    count(DISTINCT he) AS hasEntityRelCount,
    count(DISTINCT sim) AS similarRelCount,
    count(DISTINCT nc) AS nextChunkRelCount,
    count(DISTINCT e) AS entityNodeCount,
    collect(DISTINCT e) AS entities
WITH
    fileName,
    chunkNodeCount,
    partOfRelCount + hasEntityRelCount + similarRelCount + nextChunkRelCount AS chunkRelCount,
    entityNodeCount,
    entities
CALL (entities) {
    UNWIND entities AS e
    RETURN sum(COUNT { (e)-->(e2:__Entity__) WHERE e2 in entities }) AS entityEntityRelCount
}
RETURN 
    fileName,
    COALESCE(chunkNodeCount, 0) AS chunkNodeCount,
    COALESCE(chunkRelCount, 0) AS chunkRelCount,
    COALESCE(entityNodeCount, 0) AS entityNodeCount,
    COALESCE(entityEntityRelCount, 0) AS entityEntityRelCount
"""


# 更新Document节点
UPDATE_DOCUMENT_NODE = """
MATCH (d:Document {fileName:$f_name})
SET d.chunkNodeCount = $chunkNodeCount,
    d.chunkRelCount = $chunkRelCount,
    d.entityNodeCount = $entityNodeCount,
    d.entityEntityRelCount = $entityEntityRelCount,
    d.communityNodeCount = $communityNodeCount,
    d.communityRelCount = $communityRelCount,
    d.nodeCount = $nodeCount,
    d.relationshipCount = $relationshipCount
"""


# 更新或创建Chunk Node的 embedding
CREATE_OR_UPDATE_CHUNK_EMBEDDING = """
UNWIND $data AS row
MATCH (d:Document {fileName: $f_name})
MERGE (c:Chunk {id: row.id})
SET c.embedding = row.embeddings
MERGE (c)-[:PART_OF]->(d)
"""


# 知识图谱实体与chunk建立关系
MERGE_CHUNK_AND_ENTITES_RELATION = """
UNWIND $batch_data AS data
MATCH (c:Chunk {id: data.chunk_id})
CALL apoc.merge.node([data.node_type], {id: data.node_id}) YIELD node as n
MERGE (c)-[:HAS_ENTITY]->(n)
"""



# 获取向量索引
GET_VECTOR_INDEX = """
SHOW INDEXES yield * 
WHERE type = 'VECTOR' and name = 'vector'
"""

# 给每个Chunk找到相似度大于$score的相邻chunk,并让他们建立[:SIMILAR]关系
CREATE_OR_UPDATE_SIMILAR_CHUNK_RELATIONSHIP = """
MATCH (c:Chunk)
WHERE c.embedding IS NOT NULL AND COUNT { (c)-[:SIMILAR]-() } < 5
CALL db.index.vector.queryNodes('vector', 6, c.embedding) yield node, score
WHERE node <> c and score >= $score 
MERGE (c)-[rel:SIMILAR]-(node)
SET rel.score = score
"""


DROP_INDEX_ENTITIES = """
DROP INDEX entities IF EXISTS
"""

DROP_INDEX_HYBRID_SEARCH = """
DROP INDEX keyword IF EXISTS
"""

DROP_INDEX_COMMUNITY = """
DROP INDEX community_keyword IF EXISTS
"""

# 给entities建立full_text
CREATE_FULL_TEXT_INDEX_ENTITIES = """
CREATE FULLTEXT INDEX entities 
FOR (n{labels_str}) ON EACH [n.id, n.description]
"""

# 给chunk的text建立 full_text
CREATE_FULL_TEXT_INDEX_HYBRID_SEARCH = """
CREATE FULLTEXT INDEX keyword 
FOR (n:Chunk) ON EACH [n.text]
"""

CREATE_FULL_TEXT_INDEX_COMMUNITY = """
CREATE FULLTEXT INDEX community_keyword 
FOR (n:`__Community__`) ON EACH [n.summary]
"""


GET_NODE_LABELS = """
CALL db.labels() YIELD label
WITH label
WHERE NOT label IN ['Document', 'Chunk', '_Bloom_Perspective_', '__Community__', '__Entity__']
CALL apoc.cypher.run("MATCH (n:`" + label + "`) RETURN count(n) AS count",{}) YIELD value
WHERE value.count > 0
RETURN label order by label
"""

GET_RELATIONSHIPS = """
CALL db.relationshipTypes() YIELD relationshipType
WHERE NOT relationshipType  IN ['PART_OF', 'NEXT_CHUNK', 'HAS_ENTITY', '_Bloom_Perspective_','FIRST_CHUNK','SIMILAR','IN_COMMUNITY','PARENT_COMMUNITY'] 
RETURN relationshipType order by relationshipType
"""