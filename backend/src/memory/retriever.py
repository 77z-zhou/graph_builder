
from .multitask_llm import MultiTaskLLM
from .short_term import ShortTermMemory
from .mid_term import MidTermMemory
from .long_term import LongTermMemory

from .utils import *

import heapq
from concurrent.futures import ThreadPoolExecutor



import logging
logger = logging.getLogger(__name__)

class MemoryRetriever:

    def __init__(self,
                 short_term_memory: ShortTermMemory,
                 mid_term_memory: MidTermMemory,
                 long_term_memory: LongTermMemory,
                 retrieval_page_topk=7
    ):
        
        self.short_term_memory = short_term_memory
        self.mid_term_memory = mid_term_memory
        self.long_term_memory = long_term_memory

        self.retrieval_page_topk = retrieval_page_topk


    def retriever_memory(self, 
                         user_id: str, 
                         user_query:str,
                         segment_similarity_threshold=0.1,  
                         page_similarity_threshold=0.1,     
                         knowledge_threshold=0.01,          
                         top_k_segments=5,                  
                         top_k_knowledge=20                 
    ):
        
        logger.info(f"Retriever: Starting PARALLEL retrieval for query: '{user_query[:50]}'")

        # 并行执行三个检索任务
        tasks = [
            lambda: self._retrieve_mid_term_memory(user_id, user_query, segment_similarity_threshold, page_similarity_threshold, top_k_segments),
            lambda: self._retrieve_user_knowledge(user_id, user_query, knowledge_threshold, top_k_knowledge),
            lambda: self._retrieve_assistant_knowledge(user_id, user_query, knowledge_threshold, top_k_knowledge)
        ]

        # 使用并行处理
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i, task in enumerate(tasks):
                future = executor.submit(task)
                futures.append((i, future))
            
            results = [None] * 3
            for task_idx, future in futures:
                try:
                    results[task_idx] = future.result()
                except Exception as e:
                    print(f"Error in retrieval task {task_idx}: {e}")
                    results[task_idx] = []
        
        retrieved_mid_term_pages, retrieved_user_knowledge, retrieved_assistant_knowledge = results

        return {
            "retrieved_pages": retrieved_mid_term_pages or [], # List of page dicts
            "retrieved_user_knowledge": retrieved_user_knowledge or [], # List of knowledge entry dicts
            "retrieved_assistant_knowledge": retrieved_assistant_knowledge or [], # List of assistant knowledge entry dicts
            "retrieved_at": get_timestamp()
        } 
    

    def _retrieve_assistant_knowledge(self, user_id, user_query, knowledge_threshold, top_k_knowledge):
        """并行任务：从助手长期知识检索"""
        print("Retriever: Searching assistant long-term knowledge...")
        retrieved_knowledge = self.long_term_memory.search_assistant_knowledge(
            user_id, 
            user_query, 
            threshold=knowledge_threshold, 
            top_k=top_k_knowledge
        )
        print(f"Retriever: Long-term assistant knowledge recalled {len(retrieved_knowledge)} items.")
        return retrieved_knowledge


    def _retrieve_user_knowledge(self, user_id, user_query, knowledge_threshold, top_k_knowledge):
        """并行任务：从用户长期知识检索"""
        print("Retriever: Searching user long-term knowledge...")

        retrieved_knowledge = self.long_term_memory.search_user_knowledge(
            user_id,
            user_query, 
            threshold=knowledge_threshold, 
            top_k=top_k_knowledge
        )
        print(f"Retriever: Long-term user knowledge recalled {len(retrieved_knowledge)} items.")
        return retrieved_knowledge
    


    def _retrieve_mid_term_memory(self, 
                                  user_id: str, 
                                  user_query, 
                                  segment_similarity_threshold, 
                                  page_similarity_threshold, 
                                  top_k_segments
    ):
        """并行任务：从中期记忆检索"""
        print("Retriever: Searching mid-term memory...")

        # 1. 从中期记忆中检索 segments
        matched_segments = self.mid_term_memory.search_segments(
            user_id=user_id,
            query_text=user_query, 
            segment_similarity_threshold=segment_similarity_threshold,
            page_similarity_threshold=page_similarity_threshold,
            top_k_sessions=top_k_segments
        )
        

        # 使用小顶堆来筛选前retrieval_queue_capacity个page
        top_pages_heap = []
        page_counter = 0  
        for segment in matched_segments:
            for page_match in segment.get("matched_pages", []):
                page_data = page_match["page_data"]
                page_score = page_match["score"]
                
                # 组合分数 = page相似度分数 * segment相似度分数
                combined_score = page_score * segment["segment_relevance_score"]

                if len(top_pages_heap) < self.retrieval_page_topk:
                    heapq.heappush(top_pages_heap, (combined_score, page_counter, page_data))
                    page_counter += 1
                elif combined_score > top_pages_heap[0][0]: 
                    heapq.heappop(top_pages_heap)
                    heapq.heappush(top_pages_heap, (combined_score, page_counter, page_data))
                    page_counter += 1
        

        retrieved_pages = [item[2] for item in sorted(top_pages_heap, key=lambda x: x[0], reverse=True)]
        print(f"Mid-term memory recalled {len(retrieved_pages)} pages.")
        return retrieved_pages