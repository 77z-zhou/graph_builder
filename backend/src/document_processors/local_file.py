from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredFileLoader
from langchain_core.documents import Document
from pathlib import Path
import os

import logging

logger = logging.getLogger(__name__)


def load_document_content(file_path):
    file_extension = Path(file_path).suffix.lower()
    encoding_flag = False

    if file_extension == '.pdf': 
        loader = PyMuPDFLoader(file_path)
        return loader, encoding_flag
    
    if file_extension == ".txt":
        # mode = "elements"  按元素类型分割 返回结构化元素列表
        # autodetect_encoding=True：自动检测文件编码（针对文本文件）
        loader = UnstructuredFileLoader(file_path, mode="elements", autodetect_encoding=True)
        return loader, encoding_flag

    loader = UnstructuredFileLoader(file_path, mode="elements", autodetect_encoding=True)
    return loader, encoding_flag


def get_docs_with_page_numbers(unstructured_docs):
    """ 为除了pdf txt 的文档 添加page_number metadata"""
    docs = []
    page_number = 1
    page_content = ''
    metadata = {}
    for idx, doc in enumerate(unstructured_docs):
        if 'page_number' in doc.metadata:
            if doc.metadata['page_number'] == page_number:
                page_content += doc.page_content
                metadata = {
                    'source': doc.metadata['source'],
                    'page_number': page_number,
                    'filename': doc.metadata['filename'],
                    'filetype': doc.metadata['filetype']
                }
            if doc.metadata['page_number'] > page_number: # 下一页了
                docs.append(Document(page_content=page_content))
                page_number += 1
                page_content = doc.page_content

            if doc == unstructured_docs[-1]:
                docs.append(Document(page_content=page_content))

        elif doc.metadata.get('category') == 'PageBreak' and doc != unstructured_docs[0]:
            page_number += 1
            docs.append(Document(page_content=page_content, metadata=metadata))
            page_content = ''
            metadata = {}
        else:  # 全部合并为 一页
            page_content += doc.page_content
            metadata_with_custom_page_number = {
                'source': doc.metadata['source'],
                'page_number': 1,
                'filename': doc.metadata['filename'],
                'filetype': doc.metadata['filetype']
            }
            if doc == unstructured_docs[-1]:
                docs.append(Document(page_content=page_content, metadata=metadata_with_custom_page_number))
    return docs


def get_documents_from_file_by_path(file_path, file_name):
    """ 加载文件 """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.info('File %s does not exist', file_name)
        raise Exception(f'File {file_name} does not exist')
    logger.info('file %s processing', file_name)

    try:
        loader,_ = load_document_content(file_path)
        file_extension = file_path.suffix.lower()

        # txt pdf 文件
        if file_extension == ".txt" or file_extension == ".pdf":
            docs = loader.load()
        else:
            unstructured_docs = loader.load()
            docs = get_docs_with_page_numbers(unstructured_docs)       
    except Exception as exc:
        raise Exception(f'Error while reading the file content or metadata, {exc}')
    return file_name, docs, file_extension



