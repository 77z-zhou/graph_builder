from fastapi import Form, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

class Neo4jCredentials(BaseModel):
    """ Neo4j 连接凭证信息 """
    uri: Optional[str] = Field(None, description="Neo4j database URI")
    userName: Optional[str] = Field(None, description="Neo4j username")
    password: Optional[str] = Field(None, description="Neo4j password")
    database: Optional[str] = Field(None, description="Neo4j database name")
    email: Optional[str] = Field(None, description="User email for logging")


    def validate_required(self) -> None:
        if not self.uri or not self.userName or not self.password:
            raise HTTPException(
                status_code=400,
                detail="Missing required credentials: uri, userName, and password are required"
            )
      
    model_config = ConfigDict(
       str_strip_whitespace = True  # 自动去除字符串中的 whitespace
    )

async def get_neo4j_credentials(
    uri: Optional[str] = Form(None),
    userName: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    database: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
) -> Neo4jCredentials:

    return Neo4jCredentials(
        uri=uri,
        userName=userName,
        password=password,
        database=database,
        email=email
    )

async def get_neo4j_credentials_from_query(
    uri: Optional[str] = None,
    userName: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    email: Optional[str] = None
) -> Neo4jCredentials:
    """从查询参数获取 Neo4j 凭证"""
    return Neo4jCredentials(
        uri=uri,
        userName=userName,
        password=password,
        database=database,
        email=email
    )

      

class SourceScanExtractParams(BaseModel):
    """ 知识图谱抽取参数 """
    source_url: Optional[str] = Field(None, description="Source URL")
    wiki_query: Optional[str] = Field(None, description="Wikipedia query(维基百科)")
    model: str = Field(..., description="Model name")
    source_type: Optional[str] = Field(None, description="source type")
    file_name: Optional[str] = Field(None, description="File name")
    allowedNodes: Optional[str] = Field(None, description="Allowed nodes")
    allowedRelationship: Optional[str] = Field(None, description="Allowed relationships")
    token_chunk_size: Optional[int] = Field(None, description="Token chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap")
    chunks_to_combine: Optional[int] = Field(None, description="组合Chunk数量, 用于将多个小Chunk组合成大Chunk进行命名实体识别")
    language: Optional[str] = Field(None, description="Language")
    retry_condition: Optional[str] = Field(None, description="Retry condition")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions")

    @field_validator("file_name")
    @classmethod
    def normailize_file_name(cls, v):
        return v.strip() if isinstance(v, str) else v

async def get_source_scan_extract_params(
    source_url: Optional[str] = Form(None),
    wiki_query: Optional[str] = Form(None),
    model: str = Form(...),
    source_type: Optional[str] = Form(None),
    file_name: Optional[str] = Form(None),
    allowedNodes: Optional[str] = Form(None),
    allowedRelationship: Optional[str] = Form(None),
    token_chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    chunks_to_combine: Optional[int] = Form(None),
    language: Optional[str] = Form(None),
    retry_condition: Optional[str] = Form(None),
    additional_instructions: Optional[str] = Form(None),
) -> SourceScanExtractParams:
    return SourceScanExtractParams(
        source_url=source_url,
        wiki_query=wiki_query,
        model=model,
        source_type=source_type,
        file_name=file_name,
        allowedNodes=allowedNodes,
        allowedRelationship=allowedRelationship,
        token_chunk_size=token_chunk_size,
        chunk_overlap=chunk_overlap,
        chunks_to_combine=chunks_to_combine,
        language=language,
        retry_condition=retry_condition,
        additional_instructions=additional_instructions,
    )





@dataclass
class SourceNode:
    file_name: str = ""
    file_size: int = 0
    file_type: str = ""
    file_source: str = ""
    status: str = ""
    url: str = ""
    gcsBucket: str = ""
    gcsBucketFolder: str = ""
    gcsProjectId: str = ""
    awsAccessKeyId: str = ""
    chunkNodeCount: int = 0
    chunkRelCount: int = 0
    entityNodeCount: int = 0
    entityEntityRelCount: int = 0
    communityNodeCount: int = 0
    communityRelCount: int = 0
    node_count: int = 0
    relationship_count: str = "0"
    model: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    processing_time: float = 0.0
    error_message: str = ""
    total_chunks: int = 0
    language: str = ""
    is_cancelled: bool = False
    processed_chunk: int = 0
    access_token: str = ""
    retry_condition: str = ""
    token_usage: int = 0
  


# =========== API Request 实体 ==========
class PostProcessingTask(BaseModel):
   tasks: List[str] = Field(..., description="Task names")



# ===== API 响应构造 ============
def create_api_response(status,success_count=None,failed_count=None, data=None, error=None,message=None,file_source=None,file_name=None):
    response = {"status": status}

    # Set the data of the response
    if data is not None:
      response["data"] = data

    # Set the error message to the response.
    if error is not None:
      response["error"] = error
    
    if success_count is not None:
      response['success_count']=success_count
      response['failed_count']=failed_count
    
    if message is not None:
      response['message']=message

    if file_source is not None:
      response['file_source']=file_source

    if file_name is not None:
      response['file_name']=file_name
      
    return response
