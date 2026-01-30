from collections import defaultdict
import heapq
import numpy as np

import faiss
from langchain_core.embeddings import Embeddings

from .multitask_llm import MultiTaskLLM
from .storage.base import BaseStorage
from .utils import *

import logging

logger = logging.getLogger(__name__)





class MidTermMemory:

    def __init__(self, 
                 multitask_llm: MultiTaskLLM,
                 embedding_func: Embeddings, 
                 storage:BaseStorage, 
                 max_capacity: int = 2000
    ):
        self.multitask_llm = multitask_llm
        self.embedding_func = embedding_func
        self.max_capacity = max_capacity
        self.storage = storage

        # 定义存储结构
        self.segments = defaultdict(lambda: defaultdict(dict))  # {user_id: {segment_id: segment_obj}}
        self.access_frequency = defaultdict(lambda: defaultdict(int)) # {user_id: {segment_id: access_count_for_lfu}}
        self.heap = defaultdict(list)  # {user_id: []}

        self.storage = storage
    def get_page_by_id(self, user_id, page_id):
        user_segments = self.segments[user_id]
        for segment in user_segments.values():
            for page in segment.get("details", []):
                if page_id == page.get("page_id"):
                    return page
        return None
    
    def update_page_connections(self, user_id, page):
        current_page_id = page.get("page_id")
        if page.get("pre_page"):
            pre_page_id = page["pre_page"]
            prev_page = self.get_page_by_id(user_id, pre_page_id)
            if prev_page:
                prev_page["next_page"] = current_page_id
        
        if page.get("next_page"):
            next_page_id = page["next_page"]
            next_page = self.get_page_by_id(user_id, next_page_id)
            if next_page:
                next_page["pre_page"] = current_page_id
        

    def add_new_segment(self, user_id, page_summary, page_summary_keywords, page):
        segment_id = generate_id("segment")
        page_summary_vec = self.embedding_func.embed_documents([page_summary])[0]
        page_summary_vec = normalize_vector(page_summary_vec)  # L2归一化后  dot =  余弦相似度 
        page_summary_keywords = page_summary_keywords if page_summary_keywords is not None else []
        
        # 处理page 
        page_id = page.get("page_id", generate_id("page"))
        # page embedding
        if "page_embedding" in page and page["page_embedding"]:
            inp_vec = page["page_embedding"]
            if isinstance(inp_vec, list):
                inp_vec_np = np.array(inp_vec, dtype=np.float32)
                # 检查是否需要重新normalize 防御性判断, L2归一不会完全等于1
                if np.linalg.norm(inp_vec_np) > 1.1 or np.linalg.norm(inp_vec_np) < 0.9:  
                    inp_vec = normalize_vector(inp_vec_np).tolist()
        else:
            full_text = f"User: {page.get('user','')} Assistant: {page.get('assistant','')}"
            inp_vec = self.embedding_func.embed_documents([full_text])[0]
            inp_vec = normalize_vector(inp_vec)

        if "page_keywords" in page and page["page_keywords"]:
            page_keywords = page["page_keywords"]
        else:
            page_keywords = page_summary_keywords
        
        processed_page = {
            **page,
            "page_id":page_id,
            "page_embedding": inp_vec.tolist(),
            "page_keywords": page_keywords,
            "preloaded": page.get("preloaded", False),
            "analyzed": page.get("analyzed", False),
        }

        current_ts = get_timestamp()
        segment_obj = {
            "id": segment_id,
            "summary": page_summary,
            "summary_keywords": page_summary_keywords,
            "summary_embedding": page_summary_vec.tolist(),
            "details": [processed_page],
            "L_interaction": 1,
            "R_recency": 1.0, # Initial recency
            "N_visit": 0,
            "H_segment": 0.0, # Initial heat, will be computed
            "timestamp": current_ts, # Creation timestamp
            "last_visit_time": current_ts, # Also initial last_visit_time for recency calc
            "access_count_lfu": 0 # For LFU eviction policy
        }
        # 计算热力值
        segment_obj["H_segment"] = compute_segment_heat(segment_obj)

        self.segments[user_id][segment_id] = segment_obj
        self.access_frequency[user_id][segment_id] = 0  # 初始化 LFU
        heapq.heappush(self.heap[user_id], (-segment_obj["H_segment"], segment_id)) # 大顶堆

        # segments 超过最大容量, 需要弹出访问次数最小的segment
        if len(self.segments[user_id]) > self.max_capacity:
            self.evict_lfu(user_id)

        return segment_id
        




    def insert_pages_into_segment(
        self,
        user_id,
        page_summary,
        page_summary_keywords,
        page,
        similarity_threshold=0.6,
        keyword_similarity_alpha=1.0,
    ):
        user_segments = self.segments[user_id]

        if not user_segments:
            # 初次进来的page
            logger.info(
                f"MidTermMemory: 【user】:{user_id}, not existing segment. Creating new segment."
            )
            self.add_new_segment(user_id, page_summary, page_summary_keywords, page)

        # 用户已有segments
        else:
            page_summary_vec = self.embedding_func.embed_documents([page_summary])[0]
            page_summary_vec = normalize_vector(page_summary_vec)

            best_sid = None
            best_overall_score = -1

            # 查询相似的 segments
            similar_segments = self.storage.search_mid_term_segment(user_id, page_summary_vec.tolist(), topk=5)

            # 遍历相似的前topk个segments
            for similar_segment in similar_segments:
                segment_id = similar_segment["segment_id"]
                if segment_id not in self.segments[user_id]:
                     continue
                     
                segment = self.segments[user_id][segment_id]

                # 获取语义相似度
                semantic_sim = similar_segment.get("segment_relevance_score")

                # 计算关键词相似度
                segment_keywords = set(segment.get("summary_keywords", []))
                page_keywords = set(page_summary_keywords)
                s_topic_keywords = 0
                if segment_keywords and page_keywords:
                    intersection = len(segment_keywords.intersection(page_keywords))
                    union = len(segment_keywords.union(page_keywords))
                    if union > 0:
                        s_topic_keywords = intersection / union 

                # 计算总分值 = 语义相似度 + 关键词相似度
                overall_score = semantic_sim + keyword_similarity_alpha * s_topic_keywords

                if overall_score > best_overall_score:
                    best_overall_score = overall_score
                    best_sid = segment_id

            # 分值最大的segment超过阈值, 加入该segment中
            if best_sid and best_overall_score >= similarity_threshold:
                
                # 插入page 到segment中
                page_id = page.get("page_id", generate_id("page"))
                # page embedding
                if "page_embedding" in page and page["page_embedding"]:
                    inp_vec = page["page_embedding"]
                    if isinstance(inp_vec, list):
                        inp_vec_np = np.array(inp_vec, dtype=np.float32)
                        # 检查是否需要重新normalize 防御性判断, L2归一不会完全等于1
                        if np.linalg.norm(inp_vec_np) > 1.1 or np.linalg.norm(inp_vec_np) < 0.9:  
                            inp_vec = normalize_vector(inp_vec_np).tolist()
                else:
                    full_text = f"User: {page.get('user','')} Assistant: {page.get('assistant','')}"
                    inp_vec = self.embedding_func.embed_documents([full_text])[0]
                    inp_vec = normalize_vector(inp_vec).tolist()

                if "page_keywords" in page and page["page_keywords"]:
                    page_keywords_current = page["page_keywords"]
                else:
                    page_keywords_current = page_summary_keywords

                processed_page = {
                    **page,
                    "page_id":page_id,
                    "page_embedding": inp_vec,
                    "page_keywords": page_keywords_current
                }

                target_segment = self.segments[user_id][best_sid]
                target_segment["details"].append(processed_page)
                segment_summary =  self.multitask_llm.generate_segment_summary(target_segment.get("details",[]))
                target_segment["summary"] = segment_summary.summary
                summary_embed = self.embedding_func.embed_documents([target_segment["summary"]])[0]
                target_segment["summary_embedding"] = normalize_vector(summary_embed).tolist()
                target_segment["summary_keywords"] = segment_summary.keywords
                target_segment["L_interaction"] += 1
                target_segment["last_visit_time"] = get_timestamp() # Update last visit time on modification
                target_segment["H_segment"] = compute_segment_heat(target_segment)

                # 重建堆
                self.rebuild_heap(user_id)
            
            # 分值最大的segment没有超过阈值, 创建一个新的segment
            else:
                self.add_new_segment(user_id, page_summary, page_summary_keywords, page)

        # 更新page chain 前后page的指针
        self.update_page_connections(user_id, page)

        # 中期记忆入库
        self.save(user_id)



    def evict_lfu(self, user_id):
        # base case
        if not self.access_frequency[user_id] or not self.segments[user_id]:
            return
        
        # 获取访问次数小的segment_id
        lfu_sid = min(self.access_frequency[user_id], key=self.access_frequency[user_id].get)
        logger.info(f"MidTermMemory: LFU eviction. user:{user_id}, Segment {lfu_sid} has lowest access frequency.")

        if lfu_sid not in self.segments[user_id]: # 删除的segment可能不存在
            del self.access_frequency[user_id][lfu_sid]
            self.rebuild_heap(user_id)
            return
        
        # 移出访问次数小的segment
        segment_to_delete = self.segments[user_id].pop(lfu_sid)  
        del self.access_frequency[user_id][lfu_sid]

        # TODO 清理 page的外部链接


        self.rebuild_heap(user_id)



    def search_segments(self, 
                        user_id,
                        query_text, 
                        segment_similarity_threshold=0.1, 
                        page_similarity_threshold=0.1, 
                        top_k_segments=5, 
                        keyword_alpha=1.0
    ):
        # base case
        if not self.segments[user_id]:
            return []
        
        query_vec = self.embedding_func.embed_query(query_text)
        query_vec = normalize_vector(query_vec)

        segment_ids = list(self.segments[user_id].keys)

        summary_embeddings_list = [self.segments[user_id][sid]["summary_embedding"] for sid in segment_ids]
        summary_embeddings_np = np.array(summary_embeddings_list, dtype=np.float32)

        dim = len(query_vec)
        index = faiss.IndexFlatIP(dim)
        index.add(summary_embeddings_np)
        query_arr_np = np.array([query_vec], dtype=np.float32)
        distances, indices = index.search(query_arr_np, min(top_k_segments, len(segment_ids)))
        index.reset() # 清空内存中的索引

        results = []
        current_time_str =  get_timestamp()

        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            
            sid = segment_ids[idx]
            segment = self.segments[user_id][sid]
            semantic_sim_score = float(distances[0][i])

            if semantic_sim_score >= segment_similarity_threshold:
                matched_pages = []
                pages = segment.get("details",[])
                if not pages: 
                    continue
                page_embeddings = [page["page_embedding"] for page in pages]
                page_embeddings_np = np.array(page_embeddings, dtype=np.float32)
                index.add(page_embeddings_np)
                page_distance, page_indices = index.search(query_arr_np)

                for p_i, p_idx in enumerate(page_indices):
                    page_semantic_sim_score = float(page_distance[0][p_i])
                    page = pages[p_idx]
                    if page_semantic_sim_score >= page_similarity_threshold:
                        matched_pages.append({"page_data":page, "score": page_semantic_sim_score})
                
                if matched_pages:
                    segment["N_visit"] += 1
                    segment["last_visit_time"] = current_time_str
                    segment["access_count_lfu"] = segment.get("access_count_lfu", 0) + 1
                    self.access_frequency[user_id][sid] = segment["access_count_lfu"]
                    segment["H_segment"] = compute_segment_heat(segment)
                    
                    results.append({
                        "segment_id": sid,
                        "segment_summary": segment["summary"],
                        "segment_relevance_score": semantic_sim_score,
                        "matched_pages": sorted(matched_pages, key=lambda x: x["score"], reverse=True) # Sort pages by score
                    })

        self.rebuild_heap(user_id)
        self.save(user_id)
        return sorted(results, key=lambda x: x["segment_relevance_score"], reverse=True)


        


        
        



    
    def rebuild_heap(self, user_id):
        """ 重建单个用户堆 """
        self.heap[user_id] = []
        user_segments = self.segments[user_id]
        for sid, segment in user_segments.items():
            heapq.heappush(self.heap[user_id], (-segment["H_segment"], sid))

    def rebuild_all_user_heap(self):
        """ 重建所有用户堆 """
        for user_id in self.segments.keys():
            for sid, segment in self.segments[user_id].items():
                heapq.heappush(self.heap[user_id], (-segment["H_segment"], sid))

    def save(self, user_id):
        self.storage.add_mid_term_memory(user_id, self.segments[user_id], self.access_frequency[user_id])
        
    
    def load(self):
        try:
            segments, access_frequency = self.storage.load_mid_term_memory()
            self.segments = segments
            self.access_frequency = access_frequency
            self.rebuild_all_user_heap()
        except Exception as e:
            logger.error(f"MidTermMemory: Error loading: {e}. Initializing new memory.")