from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from .multitask_llm import MultiTaskLLM
from .short_term import ShortTermMemory
from .mid_term import MidTermMemory
from .long_term import LongTermMemory
from .utils import *
from .prompts import *

import logging
logger = logging.getLogger(__name__)

class MemoryUpdater:

    def __init__(self,
                 multitask_llm: MultiTaskLLM,
                 short_term_memory: ShortTermMemory,
                 mid_term_memory: MidTermMemory,
                 long_term_memory: LongTermMemory,
                 topic_similarity_threshold: float,
                 mid_term_heat_threshold: float):
        
        self.multitask_llm = multitask_llm
        self.short_term_memory = short_term_memory
        self.mid_term_memory = mid_term_memory
        self.long_term_memory = long_term_memory

        self.topic_similarity_threshold = topic_similarity_threshold
        self.mid_term_heat_threshold = mid_term_heat_threshold

        self.last_page_for_continuity_dict = defaultdict(lambda: defaultdict(dict))
        


    
    def process_short_term_to_mid_term(self, user_id: str, session_id: str):
        """  短期记忆 到 中期记忆"""

        # 判断短期记忆中是否有超出队列的记忆, 需要进化到中期记忆
        qa_pair = self.short_term_memory.pop_oldest(user_id, session_id)
        if not qa_pair:
            # 没有超出队列的短期记忆
            return
        
        # 创建page(使用短期记忆QA对)
        current_page_obj = {
            "page_id" : generate_id("page"),
            "user": qa_pair.get("user", ""),
            "assistant": qa_pair.get("assistant", ""),
            "timestamp": qa_pair.get("timestamp", get_timestamp()),
            "preloaded": False,
            "analyzed": False,
            "pre_page": None,
            "next_page": None,
            "meta_info": None
        }

        # 判断 是否能组成 page chain
        last_page_obj = self.last_page_for_continuity_dict[user_id][session_id]
        is_continuous = self.multitask_llm.check_conversation_continuity(last_page_obj,current_page_obj)

        if is_continuous and last_page_obj:
            # 连续 page chain
            current_page_obj["pre_page"] = last_page_obj["page_id"]

            # 结合上一个page的meta信息和当前的对话信息 为当前page生成新的meta信息
            last_meta = last_page_obj.get("meta_info")
            new_meta = self.multitask_llm.generate_page_meta_info(last_meta, current_page_obj)
            current_page_obj["meta_info"] = new_meta

            # 判断last_page 是否在中期记忆中
            if last_page_obj.get("page_id") and self.mid_term_memory.get_page_by_id(user_id, last_page_obj["page_id"]):
                # 根据last_page  更新他们一个chain中的meta信息
                self._update_linked_pages_meta_info(user_id, last_page_obj["page_id"], new_meta)

        else:
            # 开启一个新的 page chain  单独生成meta info
            current_page_obj["meta_info"] = self.multitask_llm.generate_page_meta_info(None, current_page_obj)
        

        self.last_page_for_continuity_dict[user_id][session_id] = current_page_obj


        summary = self.multitask_llm.generate_page_summary(current_page_obj)
        
        # 插入page 到中期记忆
        self.mid_term_memory.insert_pages_into_segment(
            user_id=user_id,
            page_summary=summary.content,
            page_summary_keywords=summary.keywords,
            page=current_page_obj,
            similarity_threshold=self.topic_similarity_threshold
        )

        


    def _update_linked_pages_meta_info(self, user_id, start_page_id, new_meta):
        """ 更新 page chain中的meta信息 """
        q = [start_page_id]
        visited = {start_page_id}

        head = 0
        while head < len(q):
            cur_page_id = q[head]
            head += 1
            page = self.mid_term_memory.get_page_by_id(user_id, cur_page_id)
            if page:
                page["meta_info"] = new_meta

                # 向前寻找chain中的page
                prev_id = page.get("pre_page")
                if prev_id and prev_id not in visited:
                    q.append(prev_id)
                    visited.add(prev_id)

                next_id = page.get("next_page")
                if next_id and next_id not in visited:
                    q.append(next_id)
                    visited.add(next_id)
                
        if q:
            self.mid_term_memory.save(user_id)



    def _trigger_profile_and_knowledge_update_if_needed(self, user_id):
        """ 检查中期记忆中的热点segment,若达到阈值则触发用户画像/知识更新。 """
        
        # base case
        if not self.mid_term_memory.heap[user_id]:
            return
        
        # 1. 取出大顶堆的堆顶 (最热门的segment)
        neg_heat, sid = self.mid_term_memory.heap[user_id][0]
        current_heat = -neg_heat

        # 2. 判断是否超过 热度阈值
        if current_heat >= self.mid_term_heat_threshold:
            segment = self.mid_term_memory.segments.get("user_id").get(sid)
            if not segment:
                self.mid_term_memory.rebuild_heap(user_id)
                return
            
            # 3. 获取segment中 没有被分析过的 page
            unanalyzed_pages = [p for p in segment.get("details", []) if not p.get("analyzed", False)]

            if unanalyzed_pages:
                
                # 并行执行两个LLM任务, 用户画像分析、 知识提取
                def task_user_profile_analysis():
                    logger.info("starting parallel user profile analysis and update...")

                    # 获取当前用户画像
                    profile = self.long_term_memory.get_user_profile(user_id)
                    current_profile = profile.get("data",None)
                    if current_profile is None:
                        current_profile = "No existing profile data."
                    
                    # 使用LLM提取用户画像
                    return self.multitask_llm.user_profile_analysis(unanalyzed_pages, current_user_profile=current_profile)
                    
                def task_knowledge_extraction():
                    logger.info("starting parallel knowledge extraction...")
                    return self.multitask_llm.knowledge_extraction(unanalyzed_pages)
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    # 提交两个主要任务
                    future_profile = executor.submit(task_user_profile_analysis)
                    future_knowledge = executor.submit(task_knowledge_extraction)
                    
                    # 等待结果
                    try:
                        updated_user_profile = future_profile.result() 
                        knowledge_result = future_knowledge.result()
                    except Exception as e:
                        print(f"Error in parallel LLM processing: {e}")
                        return
                new_user_private_knowledge = knowledge_result.get("private")
                new_assistant_knowledge = knowledge_result.get("assistant_knowledge")   

                # 更新用户画像
                if updated_user_profile and updated_user_profile != "None":
                    self.long_term_memory.update_user_profile(user_id, updated_user_profile, merge=False)  # 直接替换为新的完整画像
                
                # 更新用户私有信息知识
                if new_user_private_knowledge and new_user_private_knowledge != "None":
                    for line in new_user_private_knowledge.split('\n'):
                         if line.strip() and line.strip().lower() not in ["", "none", "- none", "- none."]:
                            self.long_term_memory.add_user_knowledge(user_id, line.strip())

                # 更新助手知识
                if new_assistant_knowledge and new_assistant_knowledge.lower() != "none":
                    for line in new_assistant_knowledge.split('\n'):
                        if line.strip() and line.strip().lower() not in ["", "none", "- none", "- none."]:
                           self.long_term_memory.add_assistant_knowledge(user_id, line.strip()) # Save to dedicated assistant LTM

                for p in segment["details"]:
                    p["analyzed"] = True

                segment["N_visit"] = 0 # 重置 N_visit
                segment["L_interaction"] = 0 # Reset interaction length contribution
                # segment["R_recency"] = 1.0 # Recency will re-calculate naturally
                segment["H_segment"] = compute_segment_heat(segment) # Recompute heat with reset factors
                segment["last_visit_time"] = get_timestamp() # Update last visit time
                
                self.mid_term_memory.rebuild_heap(user_id) 
                self.mid_term_memory.save()
                logger.info(f"Profile/Knowledge update for segment {sid} complete. Heat reset.")
            else:
                logger.info(f"Hot segment {sid} has no unanalyzed pages. Skipping profile update.")