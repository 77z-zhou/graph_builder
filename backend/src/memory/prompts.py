
# 检查对话是否连续提示词
CONTINUITY_CHECK_SYSTEM_PROMPT = "You are a conversation continuity detector. Return ONLY 'true' or 'false'."
CONTINUITY_CHECK_USER_PROMPT = ("Determine if these two conversation pages are continuous (true continuation without topic shift).\n"
                                "Return ONLY \"true\" or \"false\".\n\n"
                                "Previous Page:\nUser: {prev_user}\nAssistant: {prev_assistant}\n\n"
                                "Current Page:\nUser: {curr_user}\nAssistant: {curr_assistant}\n\n"
                                "Continuous?")

# 对话总结提示词
SUMMARY_SYSTEM_PROMPT = "You are an expert in analyzing dialogue topics. Generate  concise summaries. No more than two topics. Be as brief as possible."
SUMMARY_USER_PROMPT = ("Please analyze the following dialogue and generate extremely concise subtopic summaries (if applicable), with a maximum of two themes.\n"
                           "Each summary should be very brief - just a few words for the theme and content. Format as JSON:\n"
                           "{{\"theme\": \"Brief theme\", \"keywords\": [\"key1\", \"key2\"], \"content\": \"summary\"}}\n"
                           "\nConversation content:\n{text}")


# 对话元信息提取提示词
META_INFO_SYSTEM_PROMPT = ("""You are a conversation meta-summary updater. Your task is to:
1. Preserve relevant context from previous meta-summary
2. Integrate new information from current dialogue
3. Output ONLY the updated summary (no explanations)""" )

META_INFO_USER_PROMPT = ("""Update the conversation meta-summary by incorporating the new dialogue while maintaining continuity.
        
Guidelines:
1. Start from the previous meta-summary (if exists)
2. Add/update information based on the new dialogue
3. Keep it concise (1-2 sentences max)
4. Maintain context coherence

Previous Meta-summary: {last_meta}
New Dialogue:
{new_dialogue}

Updated Meta-summary:""") 



#  用户画像提示词
PERSONALITY_ANALYSIS_SYSTEM_PROMPT = """You are a professional user preference analysis assistant. Your task is to analyze the user's personality preferences from the given dialogue based on the provided dimensions.

For each dimension:
1. Carefully read the conversation and determine if the dimension is reflected.
2. If reflected, determine the user's preference level: High / Medium / Low, and briefly explain the reasoning, including time, people, and context if possible.
3. If the dimension is not reflected, do not extract or list it.

Focus only on the user's preferences and traits for the personality analysis section.
Output only the user profile section.
"""



PERSONALITY_ANALYSIS_USER_PROMPT = """Please analyze the latest user-AI conversation below and update the user profile based on the 90 personality preference dimensions.

Here are the 90 dimensions and their explanations:

[Psychological Model (Basic Needs & Personality)]
Extraversion: Preference for social activities.
Openness: Willingness to embrace new ideas and experiences.
Agreeableness: Tendency to be friendly and cooperative.
Conscientiousness: Responsibility and organizational ability.
Neuroticism: Emotional stability and sensitivity.
Physiological Needs: Concern for comfort and basic needs.
Need for Security: Emphasis on safety and stability.
Need for Belonging: Desire for group affiliation.
Need for Self-Esteem: Need for respect and recognition.
Cognitive Needs: Desire for knowledge and understanding.
Aesthetic Appreciation: Appreciation for beauty and art.
Self-Actualization: Pursuit of one's full potential.
Need for Order: Preference for cleanliness and organization.
Need for Autonomy: Preference for independent decision-making and action.
Need for Power: Desire to influence or control others.
Need for Achievement: Value placed on accomplishments.

[AI Alignment Dimensions]
Helpfulness: Whether the AI's response is practically useful to the user. (This reflects user's expectation of AI)
Honesty: Whether the AI's response is truthful. (This reflects user's expectation of AI)
Safety: Avoidance of sensitive or harmful content. (This reflects user's expectation of AI)
Instruction Compliance: Strict adherence to user instructions. (This reflects user's expectation of AI)
Truthfulness: Accuracy and authenticity of content. (This reflects user's expectation of AI)
Coherence: Clarity and logical consistency of expression. (This reflects user's expectation of AI)
Complexity: Preference for detailed and complex information.
Conciseness: Preference for brief and clear responses.

[Content Platform Interest Tags]
Science Interest: Interest in science topics.
Education Interest: Concern with education and learning.
Psychology Interest: Interest in psychology topics.
Family Concern: Interest in family and parenting.
Fashion Interest: Interest in fashion topics.
Art Interest: Engagement with or interest in art.
Health Concern: Concern with physical health and lifestyle.
Financial Management Interest: Interest in finance and budgeting.
Sports Interest: Interest in sports and physical activity.
Food Interest: Passion for cooking and cuisine.
Travel Interest: Interest in traveling and exploring new places.
Music Interest: Interest in music appreciation or creation.
Literature Interest: Interest in literature and reading.
Film Interest: Interest in movies and cinema.
Social Media Activity: Frequency and engagement with social media.
Tech Interest: Interest in technology and innovation.
Environmental Concern: Attention to environmental and sustainability issues.
History Interest: Interest in historical knowledge and topics.
Political Concern: Interest in political and social issues.
Religious Interest: Interest in religion and spirituality.
Gaming Interest: Enjoyment of video games or board games.
Animal Concern: Concern for animals or pets.
Emotional Expression: Preference for direct vs. restrained emotional expression.
Sense of Humor: Preference for humorous or serious communication style.
Information Density: Preference for detailed vs. concise information.
Language Style: Preference for formal vs. casual tone.
Practicality: Preference for practical advice vs. theoretical discussion.

**Task Instructions:**
1. Review the existing user profile below
2. Analyze the new conversation for evidence of the 90 dimensions above
3. Update and integrate the findings into a comprehensive user profile
4. For each dimension that can be identified, use the format: Dimension ( Level(High/Medium/Low) )
5. Include brief reasoning for each dimension when possible
6. Maintain existing insights from the old profile while incorporating new observations
7. If a dimension cannot be inferred from either the old profile or new conversation, do not include it

**Existing User Profile:**
{current_user_profile}

**Latest User-AI Conversation:**
{conversation}

**Updated User Profile:**
Please provide the comprehensive updated user profile below, combining insights from both the existing profile and new conversation:"""



# 知识图谱提取提示词
KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT = """You are a knowledge extraction assistant. Your task is to extract user private data and assistant knowledge from conversations.

Focus on:
1. User private data: personal information, preferences, or private facts about the user
2. Assistant knowledge: explicit statements about what the assistant did, provided, or demonstrated

Be extremely concise and factual in your extractions. Use the shortest possible phrases.
"""

KNOWLEDGE_EXTRACTION_USER_PROMPT = """Please extract user private data and assistant knowledge from the latest user-AI conversation below.

Latest User-AI Conversation:
{conversation}

【User Private Data】
Extract personal information about the user. Be extremely concise - use shortest possible phrases:
- [Brief fact]: [Minimal context(Including entities and time)]
- (If no private data found, write "None")

【Assistant Knowledge】
Extract what the assistant demonstrated. Use format "Assistant [action] at [time]". Be extremely brief:
- Assistant [brief action] at [time/context]
- Assistant [brief capability] during [brief context]
- (If no assistant knowledge found, write "None")
"""