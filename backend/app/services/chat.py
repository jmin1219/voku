"""
Chat service - orchestrates extraction → dedup → graph write pipeline.
"""
from dataclasses import dataclass

from app.services.embeddings import EmbeddingService
from app.services.extraction import ExtractionService, Proposition
from app.services.graph.operations import GraphOperations
from app.services.providers import Provider


@dataclass
class ProcessedMessage:
    """Result of processing a chat message."""

    node_ids: list[str]
    propositions: list[Proposition]
    duplicates_found: int


@dataclass
class PropositionWithEmbedding:
    """Internal data structure pairing propositions with their embeddings."""

    proposition: Proposition
    embedding: list[float]


@dataclass
class CreatedNode:
    """Internal data structure for newly created nodes with embeddings."""

    node_id: str
    embedding: list[float]


class ChatService:
    """
    Orchestrates the chat → graph pipeline.

    Flow:
    1. Extract propositions from user text
    2. Generate embeddings for each proposition
    3. Semantic deduplication (cosine similarity > 0.95)
    4. Create LeafNodes for unique propositions
    5. Store embeddings for created nodes
    6. Create SIMILAR_TO edges for related nodes (similarity 0.85-0.95)
    """

    def __init__(
        self,
        extraction_service: ExtractionService,
        graph_ops: GraphOperations,
        provider: Provider,
        embedding_service: EmbeddingService,
    ):
        self.extraction = extraction_service
        self.graph = graph_ops
        self.provider = provider
        self.embedding = embedding_service

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

        # Step 2: Embed each proposition
        embeddings = self._embed_propositions(propositions)

        # Step 3: Semantic dedup (embed → dedup → create flow)
        unique_items, duplicates_count = self._deduplicate(propositions, embeddings)

        # Step 4: Create LeafNodes for unique propositions and store embeddings
        node_ids, created_nodes = self._create_nodes_with_embeddings(unique_items)

        # Step 5: Create SIMILAR_TO edges for related nodes (0.85-0.95 similarity)
        self._connect_similar_nodes(created_nodes)

        return ProcessedMessage(
            node_ids=node_ids,
            propositions=propositions,  # Return all propositions (including duplicates)
            duplicates_found=duplicates_count,
        )

    def _embed_propositions(
        self, propositions: list[Proposition]
    ) -> list[list[float]]:
        """
        Generate embeddings for all propositions.

        Args:
            propositions: List of extracted propositions

        Returns:
            List of 768-dim embeddings (one per proposition)
        """
        embeddings = []
        for prop in propositions:
            embedding = self.embedding.embed(prop.proposition)
            embeddings.append(embedding)
        return embeddings

    def _deduplicate(
        self, propositions: list[Proposition], embeddings: list[list[float]]
    ) -> tuple[list[PropositionWithEmbedding], int]:
        """
        Deduplicate propositions using semantic similarity.

        For each (proposition, embedding) pair:
        - Search existing embeddings for similar nodes (cosine similarity > 0.95)
        - If match found → skip (duplicate)
        - If no match → include in unique list

        Args:
            propositions: List of extracted propositions
            embeddings: List of embeddings (parallel to propositions)

        Returns:
            Tuple of (unique items to create, duplicates count)
        """
        unique_items: list[PropositionWithEmbedding] = []
        duplicates_count = 0

        for prop, emb in zip(propositions, embeddings):
            # Search for similar nodes in existing graph
            similar_nodes = self.graph.find_similar_nodes(
                embedding=emb,
                embedding_type="content",
                threshold=0.95,  # High threshold for deduplication
            )

            if similar_nodes:
                # Duplicate found - skip creation
                duplicates_count += 1
            else:
                # No match - include in unique list
                unique_items.append(
                    PropositionWithEmbedding(proposition=prop, embedding=emb)
                )

        return unique_items, duplicates_count

    def _create_nodes_with_embeddings(
        self, items: list[PropositionWithEmbedding]
    ) -> tuple[list[str], list[CreatedNode]]:
        """
        Create LeafNodes and store embeddings for unique propositions.

        Args:
            items: List of unique (proposition, embedding) pairs

        Returns:
            Tuple of (node_ids, created_nodes with embeddings)
        """
        node_ids = []
        created_nodes = []

        for item in items:
            prop = item.proposition
            embedding = item.embedding

            # Generate semantic slug from proposition content
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

            # Store embedding for this node
            self.graph.store_embedding(
                node_id=node["id"],
                embedding_type="content",
                embedding=embedding,
                model="bge-base-en-v1.5",
            )

            node_ids.append(node["id"])
            created_nodes.append(CreatedNode(node_id=node["id"], embedding=embedding))

        return node_ids, created_nodes

    def _connect_similar_nodes(self, created_nodes: list[CreatedNode]) -> None:
        """
        Create SIMILAR_TO edges between related nodes.

        For each newly created node:
        - Search for similar nodes in range [0.85, 0.95) similarity
        - Create SIMILAR_TO edges to connect related concepts

        Args:
            created_nodes: List of newly created nodes with embeddings
        """
        for created in created_nodes:
            # Search for related nodes (not duplicates)
            related_nodes = self.graph.find_similar_nodes(
                embedding=created.embedding,
                embedding_type="content",
                threshold=0.85,  # Lower threshold for relatedness
                limit=5,  # Limit connections to top 5 most similar
            )

            for related in related_nodes:
                similarity = related["similarity"]

                # Skip if it's the node itself or if similarity is too high (duplicate range)
                if related["node_id"] == created.node_id or similarity >= 0.95:
                    continue

                # Create SIMILAR_TO edge for related nodes (0.85-0.95 range)
                try:
                    self.graph.create_edge(
                        from_id=created.node_id,
                        to_id=related["node_id"],
                        rel_type="SIMILAR_TO",
                        confidence=similarity,  # Use similarity as confidence score
                    )
                except Exception:
                    # Ignore edge creation errors (e.g., duplicate edges)
                    # This can happen if two nodes are both in the created batch
                    pass

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
