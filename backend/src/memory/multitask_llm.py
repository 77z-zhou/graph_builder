from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from .prompts import *
from pydantic import BaseModel, Field


class ConversationContinuous(BaseModel):
    is_continuous: bool = Field(description="conversation is continuity? 'true' or 'false'") 

class MetaInfo(BaseModel):
    meta_info: str = Field(description="meta summary")

class SummaryInfo(BaseModel):
    theme: str = Field(description="conversation theme")
    keywords: list[str] = Field(default_factory=list, description="conversation keywords")
    content: str = Field(description="conversation summary content")

class KnowledgeInfo(BaseModel):
    user_private_data: str = Field(description="user private data")
    assistant_knowledge: str = Field(description="assistant knowledge")



class MultiTaskLLM:
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm


    def generate_segment_summary(self,pages):
        """ 对segments 下的 pages 生成摘要"""

        input_text_for_summary = "\n".join([
            f"User: {p.get('user','')}\nAssistant: {p.get('assistant','')}" 
            for p in pages
        ])

        structure_output_llm = self.llm.with_structured_output(SummaryInfo)
        messages = [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=SUMMARY_USER_PROMPT.format(
                text=input_text_for_summary
            ))
        ]
        summary = structure_output_llm.invoke(messages)
        return summary


    def generate_page_summary(self, current_page):
        """ 生成摘要 """
        conversation = f"User: {current_page.get('user','')}\nAssistant: {current_page.get('assistant', '')}"
        
        structure_output_llm = self.llm.with_structured_output(SummaryInfo)
        messages = [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=SUMMARY_USER_PROMPT.format(
                text=conversation
            ))
        ]
        summary = structure_output_llm.invoke(messages)
        return summary


    def generate_page_meta_info(self, last_meta, current_page):
        """ 生成 page meta info """
        current_conversation = f"User: {current_page.get('user','')}\nAssistant: {current_page.get('assistant', '')}"
        structure_output_llm = self.llm.with_structured_output(MetaInfo)
        messages = [
            SystemMessage(content=META_INFO_SYSTEM_PROMPT),
            HumanMessage(content=META_INFO_USER_PROMPT.format(
                last_meta=last_meta if last_meta else "None",
                new_dialogue=current_conversation
            ))
        ]
        response = structure_output_llm.invoke(messages)
        return response.meta_info

    def check_conversation_continuity(self, previous_page, current_page):
        """ 判断 会话是否连续 """
        prev_user = previous_page.get("user", "")
        prev_assistant = previous_page.get("assistant", "")

        structure_output_llm = self.llm.with_structured_output(ConversationContinuous)
        messages = [
            SystemMessage(content=CONTINUITY_CHECK_SYSTEM_PROMPT),
            HumanMessage(content=CONTINUITY_CHECK_USER_PROMPT.format(
                prev_user=prev_user,
                prev_assistant=prev_assistant,
                curr_user=current_page.get("user", ""),
                curr_assistant=current_page.get("assistant", "")
            ))
        ]
        response = structure_output_llm.invoke(messages)
        return response.is_continuous
    


    def user_profile_analysis(self, dialogs, current_user_profile="None"):
        """ 结合当前用户画像和新对话, 通过LLM得到最新的画像 """

        conversation = "\n".join([f"User: {d.get('user','')} (Timestamp: {d.get('timestamp', '')})\nAssistant: {d.get('assistant','')} (Timestamp: {d.get('timestamp', '')})" for d in dialogs])
        
        messages = [
            SystemMessage(content=PERSONALITY_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=PERSONALITY_ANALYSIS_USER_PROMPT.format(
                conversation=conversation,
                current_user_profile=current_user_profile
            ))
        ]

        response = self.llm.invoke(messages)
        profile = response.content.strip()
        return profile if profile else "None"
    

    def knowledge_extraction(self, dialogs):
        """ 提取知识图谱 """
        conversation = "\n".join([f"User: {d.get('user','')} (Timestamp: {d.get('timestamp', '')})\nAssistant: {d.get('assistant','')} (Timestamp: {d.get('timestamp', '')})" for d in dialogs])
        
        messages = [
            SystemMessage(content=KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=KNOWLEDGE_EXTRACTION_USER_PROMPT.format(
                conversation=conversation
            ))
        ]
        structure_output_llm = self.llm.with_structured_output(KnowledgeInfo)
        knowledge_info: KnowledgeInfo = structure_output_llm.invoke(messages)

        user_private_data = knowledge_info.user_private_data
        assistant_knowledge = knowledge_info.assistant_knowledge
        return {
            "private": user_private_data if user_private_data else "None",
            "assistant_knowledge": assistant_knowledge if assistant_knowledge else "None"
        }