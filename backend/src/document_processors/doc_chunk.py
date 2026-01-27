from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph
from config import settings

from langchain_text_splitters import RecursiveCharacterTextSplitter

import re
import logging

logger = logging.getLogger(__name__)

class CreateChunksofDocument:

    def __init__(self, docs: list[Document]):
        self.docs = docs

    
    def split_file_into_chunks(self, token_chunk_size: int, chunk_overlap: int):
        logger.info("Split file into smaller chunks")

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=token_chunk_size, chunk_overlap=chunk_overlap
        )
        max_token_chunk_size = settings.MAX_TOKEN_CHUNK_SIZE
        # chunk_to_be_created = int(max_token_chunk_size / token_chunk_size)

        chunks = []
        first_metadata = self.docs[0].metadata

        if 'page' in first_metadata:
            # PDF 或者 分页文档
            for i, doc in enumerate(self.docs):
                page_number = i + 1
                for chunk in text_splitter.split_documents([doc]):
                    chunks.append(Document(page_content=chunk.page_content, metadata={'page_number': page_number}))
        
        elif 'length' in first_metadata:
            # 视频文档
            if len(self.docs) == 1 or (len(self.docs) > 1 and self.docs[1].page_content.strip() == ''):
                match = re.search(r'(?:v=)([0-9A-Za-z_-]{11})\s*', self.pages[0].metadata.get('source', ''))
            else:
                chunks_without_time_range = text_splitter.split_documents(self.docs)
        
        else:
            # 其他chunk
            logger.info("No metadata found for pages, proceeding with normal chunking")
            chunks = text_splitter.split_documents(self.docs)
        
        logger.info('Total chunks created: %d', len(chunks))
        return chunks

            


        