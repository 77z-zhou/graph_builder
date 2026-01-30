from .base import BaseStorage
from ..utils import ensure_directory_exists, ensure_file_exists

import os
import json
import numpy as np
from collections import defaultdict, deque

import logging
logger = logging.getLogger(__name__)

class FileStorage(BaseStorage):

    def __init__(self, storage_dir: str):
        super().__init__()
        self.storage_dir = storage_dir

        self.short_term_dir = os.path.join(storage_dir, "short_term")
        self.mid_term_dir = os.path.join(storage_dir, "mid_term")
        self.long_term_dir = os.path.join(storage_dir, "long_term")
        
    
    def add_short_term_memory(self, user_id, session_id, memory):
        try: 
            user_short_term_path = os.path.join(self.short_term_dir, f"{user_id}.json")
            ensure_directory_exists(user_short_term_path)
            
            load_memory = {}
            if ensure_file_exists(user_short_term_path):
                # 1. 先读取记忆
                with open(user_short_term_path, "r", encoding="utf8") as f:
                    load_memory = json.load(f)
                # 2. 追加记忆
                if session_id in load_memory:
                    load_memory[session_id].append(memory)
                else:
                    load_memory[session_id] = [memory]
     
            else:
                load_memory[session_id] = [memory]

            # 3. 保存
            with open(user_short_term_path, "w", encoding="utf8") as f:
                json.dump(load_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"Error saving ShortTermMemory to {user_short_term_path}: {e}")
            raise e

    
    def get_short_term_memory(self):
        try:
            users_short_terms = os.listdir(self.short_term_dir)

            user_session_memory = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))

            for user_short_term in users_short_terms:
                user_id = user_short_term.split(".")[0]
                user_short_term_path = os.path.join(self.short_term_dir, user_short_term)
                with open(user_short_term_path, "r", encoding="utf8") as f:
                    session_memory = json.load(f)

                for session_id, memory in session_memory.items():
                    for mem in memory:
                        user_session_memory[user_id][session_id].append(mem)        
            return user_session_memory
        except Exception as e:
            logger.info(f"Error loading ShortTermMemory from {self.short_term_dir}: {e}")
            raise e
    

    def pop_oldest_short_term_memory(self, user_id, session_id):
        try: 
            user_short_term_path = os.path.join(self.short_term_dir, f"{user_id}.json")
            ensure_directory_exists(user_short_term_path)
            if not ensure_file_exists(user_short_term_path): 
                return
            # 1. 先读取记忆
            with open(user_short_term_path, "r", encoding="utf8") as f:
                load_memory = json.load(f)

            # 2. 删除最早进来的记忆
            if session_id not in load_memory:
                return 
            load_memory[session_id].pop(0)
            
            # 3. 保存
            with open(user_short_term_path, "w", encoding="utf8") as f:
                json.dump(load_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"Error saving ShortTermMemory to {user_short_term_path}: {e}")
            raise e



    def add_mid_term_memory(self, user_id, segments: dict, access_frequency: dict):
        """ 全量保存中期记忆 """
        try:
            user_mid_term_path = os.path.join(self.mid_term_dir, f"{user_id}.json")
            ensure_directory_exists(user_mid_term_path)
            save_memory = {
                "segments": segments,
                "access_frequency": access_frequency
            }
            with open(user_mid_term_path, "w", encoding="utf8") as f:
                json.dump(save_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"Error saving MidTermMemory to {user_mid_term_path}: {e}")
            raise e
        

    def search_mid_term_segment(self, user_id, query_embedding, topk: int=5):
        try:
            # 1. 加载用户的所有segments
            user_mid_term_path = os.path.join(self.mid_term_dir, f"{user_id}.json")
            ensure_directory_exists(user_mid_term_path)

            with open(user_mid_term_path, "r", encoding="utf8") as f:
                mid_metadata = json.load(f)
            segments = mid_metadata.get("segments")
            if not segments:  # 如果没有segments，则返回None
                return None
            
            # 2. 计算query_embedding与segment的相似度
            similar_segments = []
            for segment_id, segment in segments.items():
                semantic_sim = float(np.dot(query_embedding, segment["summary_embedding"]))
                seg = {"segment_id": segment_id, "segment_relevance_score": semantic_sim}
                similar_segments.append(seg)
        
            # 3. 排序
            similar_segments = sorted(similar_segments, key=lambda x: x["segment_relevance_score"], reverse=True)[:topk]

            return similar_segments
        except Exception as e:
            logger.info(f"Error search MidTermMemory from {user_mid_term_path}: {e}")  
            raise e
        

    def load_mid_term_memory(self):
        try:
            users_mid_terms = os.listdir(self.mid_term_dir)
            segments = defaultdict(lambda: defaultdict(dict))  # {user_id: {segment_id: segment_obj}}
            access_frequency = defaultdict(lambda: defaultdict(int)) # {user_id: {segment_id: access_count_for_lfu}}

            for user_mid_term in users_mid_terms:
                user_id = user_mid_term.split(".")[0]
                user_mid_term_path = os.path.join(self.mid_term_dir, user_mid_term)
                with open(user_mid_term_path, "r", encoding="utf8") as f:
                    mid_metadata = json.load(f)

                user_segments = mid_metadata.get("segments")
                user_access_frequency = mid_metadata.get("access_frequency")
                for segment_id, segment in user_segments.items():
                    segments[user_id][segment_id] = segment
                    access_frequency[user_id][segment_id] = user_access_frequency[segment_id]
                 
            return segments, access_frequency
        except Exception as e:
            logger.info(f"Error loading MidTermMemory from {self.mid_term_dir}: {e}")  
            raise e   
        

    # =========  长期记忆相关 ==========
    def add_long_term_memory(self, user_id, user_profile, user_knowledge, assistant_knowledge):
        """ 全量保存长期记忆 """
        try:
            user_long_term_path = os.path.join(self.long_term_dir, f"{user_id}.json")
            ensure_directory_exists(user_long_term_path)
            save_memory = {
                "user_profile": user_profile,
                "user_knowledge": user_knowledge,
                "assistant_knowledge": assistant_knowledge
            }
            with open(user_long_term_path, "w", encoding="utf8") as f:
                json.dump(save_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"Error saving LongTermMemory to {user_long_term_path}: {e}")
            raise e

    
    def load_long_term_memory(self, knowledge_capacity: int):
        try:
            users_long_terms = os.listdir(self.long_term_dir)
            user_profiles = defaultdict(dict)  # {user_id: {data: "profile_string", "last_updated": "timestamp"}}
            user_knowledge = defaultdict(lambda: deque(maxlen=knowledge_capacity))
            assistant_knowledge = defaultdict(lambda: deque(maxlen=knowledge_capacity))

            for user_long_term in users_long_terms:
                user_id = user_long_term.split(".")[0]
                user_long_term_path = os.path.join(self.long_term_dir, user_long_term)
                with open(user_long_term_path, "r", encoding="utf8") as f:
                    long_metadata = json.load(f)

                user_profile = long_metadata.get("user_profile")
                user_knowledge_list = long_metadata.get("user_knowledge")
                assistant_knowledge_list = long_metadata.get("assistant_knowledge")

                user_profiles[user_id] = user_profile
                for knowlege in user_knowledge_list:
                    user_knowledge[user_id].append(knowlege)
                
                for knowlege in assistant_knowledge_list:
                    assistant_knowledge.append(knowlege)
                 
            return user_profiles, user_knowledge, assistant_knowledge
        except Exception as e:
            logger.info(f"Error loading MidTermMemory from {self.mid_term_dir}: {e}")  
            raise e   