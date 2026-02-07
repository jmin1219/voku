"""
Chat service - orchestrates extraction → dedup → graph write pipeline.
"""
from dataclasses import dataclass

from app.services.extraction import ExtractionService, Proposition
from app.services.graph.operations import GraphOperations
from app.services.providers import Provider


@dataclass
class ProcessedMessage:
    """Result of processing a chat message."""
    node_ids: list[str]
    propositions: list[Proposition]
    duplicates_found: int


class ChatService:
    """
    Orchestrates the chat → graph pipeline.
    
    Flow:
    1. Extract propositions from user text
    2. Generate embeddings for each proposition
    3. Semantic deduplication (cosine similarity > 0.95)
    4. Create LeafNodes for unique propositions
    5. Create SIMILAR_TO edges for related nodes (similarity 0.85-0.95)
    """
    
    def __init__(
        self,
        extraction_service: ExtractionService,
        graph_ops: GraphOperations,
        provider: Provider,
    ):
        self.extraction = extraction_service
        self.graph = graph_ops
        self.provider = provider
    
    async def process_message(self, text: str) -> ProcessedMessage:
        """
        Process user message and create graph nodes.
        
        Args:
            text: User's message text
            
        Returns:
            ProcessedMessage with created node IDs and propositions
        """
        # Step 1: Extract propositions
        propositions = await self.extraction.extract(text)
        
        if not propositions:
            return ProcessedMessage(
                node_ids=[],
                propositions=[],
                duplicates_found=0,
            )
        
        # Step 2: Embed each proposition (TODO: implement)
        # embeddings = await self._embed_propositions(propositions)
        
        # Step 3: Semantic dedup (TODO: implement)
        # unique_props, duplicates = await self._deduplicate(propositions, embeddings)
        
        # Step 4: Create LeafNodes (for now, create all - no dedup yet)
        node_ids = await self._create_nodes(propositions)
        
        # Step 5: Create SIMILAR_TO edges (TODO: implement)
        # await self._connect_similar_nodes(node_ids, embeddings)
        
        return ProcessedMessage(
            node_ids=node_ids,
            propositions=propositions,
            duplicates_found=0,  # TODO: actual count
        )
    
    async def _create_nodes(self, propositions: list[Proposition]) -> list[str]:
        """
        Create LeafNodes in graph for each proposition.
        
        Args:
            propositions: List of extracted propositions
            
        Returns:
            List of created node IDs
        """
        node_ids = []
        
        for prop in propositions:
            # Generate semantic slug from proposition content
            # For now, just use first few words
            title = self._generate_title(prop.proposition)
            
            # Create LeafNode
            node = self.graph.create_leaf_node(
                title=title,
                content=prop.proposition,
                source="conversation",
                node_purpose=prop.node_purpose,
                source_type=prop.source_type,
                signal_valence=None,  # TODO: extract from structured_data if present
                confidence=prop.confidence,
            )
            
            node_ids.append(node["id"])
        
        return node_ids
    
    def _generate_title(self, text: str, max_words: int = 5) -> str:
        """
        Generate semantic slug from proposition text.
        
        For now, uses first N words. Future: LLM-generated semantic titles.
        
        Args:
            text: Proposition text
            max_words: Maximum words in title
            
        Returns:
            Lowercase hyphenated title
        """
        words = text.lower().split()[:max_words]
        # Remove punctuation
        words = ["".join(c for c in w if c.isalnum()) for w in words]
        # Filter empty strings
        words = [w for w in words if w]
        return "-".join(words)
