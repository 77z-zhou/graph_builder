from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig

import asyncio
from typing import List, Union, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, create_model

from langchain_neo4j.graphs.graph_document import GraphDocument, Node, Relationship

import logging
logger = logging.getLogger(__name__)


system_prompt = (
    "# Knowledge Graph Instructions\n"
    "## 1. Overview\n"
    "You are a top-tier algorithm designed for extracting information in structured "
    "formats to build a knowledge graph.\n"
    "Try to capture as much information from the text as possible without "
    "sacrificing accuracy. Do not add any information that is not explicitly "
    "mentioned in the text.\n"
    "- **Nodes** represent entities and concepts.\n"
    "- The aim is to achieve simplicity and clarity in the knowledge graph, making it\n"
    "accessible for a vast audience.\n"
    "## 2. Labeling Nodes\n"
    "- **Consistency**: Ensure you use available types for node labels.\n"
    "Ensure you use basic or elementary types for node labels.\n"
    "- For example, when you identify an entity representing a person, "
    "always label it as **'person'**. Avoid using more specific terms "
    "like 'mathematician' or 'scientist'."
    "- **Node IDs**: Never utilize integers as node IDs. Node IDs should be "
    "names or human-readable identifiers found in the text.\n"
    "- **Relationships** represent connections between entities or concepts.\n"
    "Ensure consistency and generality in relationship types when constructing "
    "knowledge graphs. Instead of using specific and momentary types "
    "such as 'BECAME_PROFESSOR', use more general and timeless relationship types "
    "like 'PROFESSOR'. Make sure to use general and timeless relationship types!\n"
    "## 3. Coreference Resolution\n"
    "- **Maintain Entity Consistency**: When extracting entities, it's vital to "
    "ensure consistency.\n"
    'If an entity, such as "John Doe", is mentioned multiple times in the text '
    'but is referred to by different names or pronouns (e.g., "Joe", "he"),'
    "always use the most complete identifier for that entity throughout the "
    'knowledge graph. In this example, use "John Doe" as the entity ID.\n'
    "Remember, the knowledge graph should be coherent and easily understandable, "
    "so maintaining consistency in entity references is crucial.\n"
    "## 4. Strict Compliance\n"
    "Adhere to the rules strictly. Non-compliance will result in termination."
)



def validate_and_get_relationship_type(
        allowed_relationships: Union[List[str], List[Tuple[str, str, str]]], 
        allowed_nodes: List[str]
) -> Optional[str]:
    """ 验证和判断relationship type"""

    # 1. base case, not a list
    if allowed_relationships and not isinstance(allowed_relationships, list):
        raise ValueError("allowed_relationships must be a list")

    # 2. list of strings
    if all(isinstance(item, str) for item in allowed_relationships):
        return "string"
    
    # 3. list of tuples, and each node in allowed_nodes
    if all(
        isinstance(item, tuple)
        and len(item) == 3 
        and all(isinstance(subitem, str) for subitem in item)
        and item[0] in allowed_nodes
        and item[2] in allowed_nodes
        for item in allowed_relationships
    ):
        return "tuple"
    
    raise ValueError(
        "allowed_relationships must be a list of strings or 3-item tuples"
        "For tuples, the first and third items must be strings and must be in allowed_nodes"    
    )


def _get_additional_info(input_type: str):
    """ 正常的规则限制  避免过度抽象 """
    if input_type not in ["node", "relationship"]:
        raise ValueError("input_type must be either 'node' or 'relationship'")
    
    # 要求仅使用 Person 这种标签，不需要更具体的抽象label 如Mathematician, Scientist
    if input_type == "node":
        return (
            "Ensure you use basic or elementary types for node labels.\n"
            "For example, when you identify an entity representing a person, "
            "always label it as **'Person'**. Avoid using more specific terms "
            "like 'Mathematician' or 'Scientist'"
        )
    elif input_type == "relationship":
        return (
            "Instead of using specific and momentary types such as "
            "'BECAME_PROFESSOR', use more general and timeless relationship types "
            "like 'PROFESSOR'. However, do not sacrifice any accuracy for generality"
        )
    elif input_type == "property":
        return ""
    return ""
    
def optional_enum_field(
        enum_values: Optional[Union[List[str], List[Tuple[str, str, str]]]] = None,
        description: str = "",
        input_type: str = "node",
        relationship_type: Optional[str] = None
): 
    parsed_enum_values = enum_values
    if relationship_type == "tuple":
        parsed_enum_values = list({el[1] for el in enum_values})
    
    # 有枚举限制, 则在描述中添加可选枚举值
    if enum_values:
        return Field(...,description=f"{description}. Available options are {parsed_enum_values}")
    
    # 无限制枚举, 则添加额外信息规则
    else:
        additional_info = _get_additional_info(input_type)
        return Field(..., description=description + additional_info)

def create_dynamic_schema(
        allowed_nodes: List[str], 
        allowed_relationships: Union[List[str], List[Tuple[str, str, str]]], 
        node_properties: Union[bool, List[str]], 
        relationship_properties: Union[bool, List[str]], 
        relationship_type: str
):
    
    # 1. 创建 Node
    # 1.1 定义node字段基本属性
    node_fields: Dict[str, Tuple[Any, Any]] = {
        "id": (str, Field(..., description="Name or human-readable unique identifier.")),
        "type": (str, optional_enum_field(allowed_nodes, description="The type or label of the node.", input_type="node"))
    }

    # 1.2node节点其他的属性
    if node_properties:
        if isinstance(node_properties, list) and "id" in node_properties:
            raise ValueError("'id' cannot be included in node_properties")

        node_properties_mapped: List[str] = [] if node_properties is True else node_properties
        
        class Property(BaseModel):
            key: str = optional_enum_field(node_properties_mapped, description="Property key.", input_type="property")
            value: str = Field(..., description="Extracted value. Any date value should be formatted as yyyy-mm-dd")
        
        node_fields["properties"] = (Optional[List[Property]], Field(None, description="List of node properties"))
    # 1.3 创建Node schema
    DynamicNode = create_model("DynamicNode", **node_fields)

    # 2. 创建 Relationship
    relationship_fields: Dict[str, Tuple[Any, Any]] = {
        "source_node_id": (str, Field(..., description="Name or human-readable unique identifier of source node")),
        "source_node_type": (str, optional_enum_field(allowed_nodes, description="The type or label of the source node.", input_type="node")),
        "target_node_id": (str, Field(..., description="Name or human-readable unique identifier of target node")),
        "target_node_type": (str, optional_enum_field(allowed_nodes, description="The type or label of the target node.", input_type="node")),
        "type": (str, optional_enum_field(allowed_relationships, description="The type or label of the relationship.", input_type="relationship", relationship_type=relationship_type))
    }

    # 2.1 relationship 其他的属性
    if relationship_properties:
        if (isinstance(relationship_properties, list) and "id" in relationship_properties):
            raise ValueError("'id' cannot be included in relationship_properties")
    
        relationship_properties_mapped: List[str] = [] if relationship_properties is True else relationship_properties
        class RelationshipProperty(BaseModel):
            key: str = optional_enum_field(relationship_properties_mapped, description="Property key.", input_type="property")
            value: str = Field(..., description="Extracted value. Any date value should be formatted as yyyy-mm-dd")
        relationship_fields["properties"] = (Optional[List[RelationshipProperty]], Field(None, description="List of relationship properties"))

    # 2.2 创建Relationship schema
    DynamicRelationship = create_model("DynamicRelationship", **relationship_fields)
    
    # 2.3 Relationship schema添加文档注释
    if relationship_type == "tuple":
        DynamicRelationship.__doc__ = (
            "Your task is to extract relationships from text strictly adhering "
            "to the provided schema. The relationships can only appear "
            "between specific node types are presented in the schema format "
            "like: (Entity1Type, RELATIONSHIP_TYPE, Entity2Type) /n"
            f"Provided schema is {allowed_relationships}"
        )
    
    class DynamicGraph(BaseModel):
        """Represents a graph document consisting of nodes and relationships."""
        
        nodes: Optional[List[DynamicNode]] = Field(description="List of Nodes")
        relationships: Optional[List[DynamicRelationship]] = Field(description="List of Relationships")

    return DynamicGraph

def format_property_key(s: str) -> str:
    """ 驼峰命名规则转换 """
    words = s.split()
    if not words:
        return s
    first_word = words[0].lower()
    capitalized_words = [word.capitalize() for word in words[1:]]
    return "".join([first_word] + capitalized_words)


def map_to_base_node(node: Any) -> Node:
    """ Node提取 """
    properties = {}
    if hasattr(node, "properties") and node.properties:
        for p in node.properties:
            properties[format_property_key(p.key)] = p.value
    return Node(id=node.id, type=node.type, properties=properties)

def map_to_base_relationship(rel: Any) -> Relationship:
    """ Relationship提取 """
    source = Node(id=rel.source_node_id, type=rel.source_node_type)
    target = Node(id=rel.target_node_id, type=rel.target_node_type)
    properties = {}
    if hasattr(rel, "properties") and rel.properties:
        for p in rel.properties:
            properties[format_property_key(p.key)] = p.value
    return Relationship(
        source=source, target=target, type=rel.type, properties=properties
    )


def _format_nodes(nodes: List[Node]) -> List[Node]:
    return [
        Node(
            id=el.id.title() if isinstance(el.id, str) else el.id,
            type=el.type.capitalize()  
            if el.type
            else "Node",  
            properties=el.properties,
        )
        for el in nodes
    ]


def _format_relationships(rels: List[Relationship]) -> List[Relationship]:
    return [
        Relationship(
            source=_format_nodes([el.source])[0],
            target=_format_nodes([el.target])[0],
            type=el.type.replace(" ", "_").upper(),
            properties=el.properties,
        )
        for el in rels
    ]


def convert_to_graph_document(raw_schema: Dict[Any, Any]):
    parsed = raw_schema.get("parsed")
    if not parsed:
        raise ValueError("No parsed data found in the raw schema.")
    
    nodes = [map_to_base_node(node) for node in parsed.nodes if node.id] if parsed.nodes else []
    relationships = ([map_to_base_relationship(rel) for rel in parsed.relationships 
                     if rel.type and rel.source_node_id and rel.target_node_id] 
                     if parsed.relationships else [])
    
    return _format_nodes(nodes), _format_relationships(relationships)

class LLMGraphTransformer:
    """ 用于从Document中提取关系图 """ 

    def __init__(self, 
                 llm: BaseLanguageModel, 
                 allowed_nodes: List[str] = [],
                 allowed_relationships: Union[List[str], List[Tuple[str, str, str]]] = [],
                 strict_mode: bool = True, # 控制是否需要过滤nodes relationships
                 node_properties: Union[bool, List[str]] = False,
                 relationship_properties: Union[bool, List[str]] = False,
                 additional_instructions: str = ""
                 ):
        """
           node_properties: 是否需要获取节点属性  eg ["name","age"] 要求多抽取节点的name 和 age属性
           relationship_properties: 同上
        """
        
        # 校验relationships
        self._relationship_type = validate_and_get_relationship_type(allowed_relationships, allowed_nodes)

        self.allowed_nodes = allowed_nodes
        self.allowed_relationships = allowed_relationships
        self.strict_mode = strict_mode
        self.additional_instructions = additional_instructions
        
        # struct output 
        schema = create_dynamic_schema(
            allowed_nodes,
            allowed_relationships,
            node_properties,
            relationship_properties,
            self._relationship_type
        )
        self.llm = llm.with_structured_output(schema, include_raw=True)
        
    async def process_response(self, 
                          document: Document, 
                          config: Optional[RunnableConfig] = None
    ) -> GraphDocument:
        text = document.page_content
        input = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=self.additional_instructions 
                                +  " Tip: Make sure to answer in the correct format and do "
                                "not include any explanations. "
                                "Use the given format to extract information from the "
                                f"following input: {text}")
                ]
        logger.info(f"llm starting extract input:{input}")
        raw_schema = await self.llm.ainvoke(input, config=config)
        nodes, relationships = convert_to_graph_document(raw_schema)
        logger.info(f"llm extract nodes:{nodes}")
        logger.info(f"llm extract relationships:{relationships}")

        if self.strict_mode:
            if self.allowed_nodes:
                lower_allowed_nodes = [el.lower() for el in self.allowed_nodes]
                nodes = [
                    node for node in nodes if node.type.lower() in lower_allowed_nodes
                ]
                relationships = [
                    rel
                    for rel in relationships
                    if rel.source.type.lower() in lower_allowed_nodes
                    and rel.target.type.lower() in lower_allowed_nodes
                ]

            if self.allowed_relationships:
                if self._relationship_type == "tuple":
                    relationships = [
                        rel
                        for rel in relationships
                        if (
                            (
                                rel.source.type.lower(),
                                rel.type.lower(),
                                rel.target.type.lower(),
                            )
                            in [  # type: ignore
                                (s_t.lower(), r_t.lower(), t_t.lower())
                                for s_t, r_t, t_t in self.allowed_relationships
                            ]
                        )
                    ]
                else:  # Filter by type only
                    relationships = [
                        rel
                        for rel in relationships
                        if rel.type.lower()
                        in [el.lower() for el in self.allowed_relationships]  # type: ignore
                    ]
        return GraphDocument(nodes=nodes, relationships=relationships, source=document)

    async def convert_to_graph_documents(self, 
                                         documents: List[Document], 
                                         config: Optional[RunnableConfig] = None
    ) -> List[GraphDocument]:
        tasks = [
            asyncio.create_task(self.process_response(document, config))
            for document in documents
        ]
        results = await asyncio.gather(*tasks)
        return results
