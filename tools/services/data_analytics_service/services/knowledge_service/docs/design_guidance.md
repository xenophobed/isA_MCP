Neo4j GraphRAG Best Practices Solution (2025)

  1. Graph Data Model Architecture

  -- Entity nodes with embeddings
  CREATE (e:Entity {
      name: "Apple Inc",
      type: "ORGANIZATION",
      canonical_form: "Apple Inc.",
      confidence: 0.95,
      source_document: "doc_123",
      embedding: [0.1, 0.2, ...] // 1536 dimensions
  })

  -- Document chunks as separate nodes
  CREATE (d:Document {
      id: "doc_123_chunk_1",
      text: "Apple Inc. was founded...",
      chunk_index: 1,
      source_document: "doc_123",
      embedding: [0.3, 0.4, ...] // 1536 dimensions
  })

  -- Attributes as properties or separate nodes
  CREATE (a:Attribute {
      entity_id: "apple_inc",
      name: "founded_year",
      value: "1976",
      type: "DATE",
      confidence: 0.9,
      embedding: [0.5, 0.6, ...] // 1536 dimensions
  })

  2. Vector Index Configuration

  -- Entity embeddings index
  CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
  FOR (e:Entity) ON e.embedding
  OPTIONS { indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
  }}

  -- Document chunk embeddings index
  CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
  FOR (d:Document) ON d.embedding
  OPTIONS { indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
  }}

  -- Relation embeddings index
  CREATE VECTOR INDEX relation_embeddings IF NOT EXISTS
  FOR ()-[r:RELATES_TO]-() ON r.embedding
  OPTIONS { indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
  }}

  3. Embedding Generation Strategy

  # For entities: canonical_form + type + key attributes
  entity_text = f"{entity.canonical_form} {entity.entity_type.value}"
  if entity.attributes:
      key_attrs = " ".join([f"{k}:{v}" for k,v in entity.attributes.items()])
      entity_text += f" {key_attrs}"

  # For relations: subject + predicate + object + context
  relation_text = f"{relation.subject.text} {relation.predicate} 
  {relation.object.text}"
  if relation.context:
      relation_text += f" context: {relation.context}"

  # For documents: original text chunks
  document_text = chunk.text

  4. Recommended Graph Constructor Refactor

  @dataclass
  class GraphNode:
      id: str
      entity: Entity
      attributes: Dict[str, Attribute]
      embedding: List[float]  # NEW: 1536-dim embedding
      node_type: str = "entity"
      metadata: Dict[str, Any] = None

  @dataclass 
  class GraphEdge:
      id: str
      source_id: str
      target_id: str
      relation: Relation
      embedding: List[float]  # NEW: 1536-dim embedding
      edge_type: str = "relation"
      weight: float = 1.0
      metadata: Dict[str, Any] = None

  class GraphConstructor(BaseService):
      def __init__(self, config: Optional[Dict[str, Any]] = None):
          super().__init__("GraphConstructor")
          self.config = config or {}
          self.embedding_generator = EmbeddingGenerator()  # NEW

      async def construct_graph(self, 
                               entities: List[Entity],
                               relations: List[Relation],
                               entity_attributes: Dict[str, Dict[str, Attribute]],
                               source_text: str = "") -> KnowledgeGraph:

          nodes = {}
          edges = {}

          # Generate embeddings for entities
          entity_texts = []
          for entity in entities:
              attributes = entity_attributes.get(entity.text, {})
              entity_text = self._create_entity_text(entity, attributes)
              entity_texts.append(entity_text)

          # Batch generate embeddings
          entity_embeddings = await self.embedding_generator.embed_batch(entity_texts)

          # Create nodes with embeddings
          for i, entity in enumerate(entities):
              node_id = self._generate_node_id(entity)
              attributes = entity_attributes.get(entity.text, {})

              node = GraphNode(
                  id=node_id,
                  entity=entity,
                  attributes=attributes,
                  embedding=entity_embeddings[i],  # NEW
                  metadata={
                      "entity_type": entity.entity_type.value,
                      "confidence": entity.confidence,
                      "canonical_form": entity.canonical_form,
                      "aliases": entity.aliases
                  }
              )
              nodes[node_id] = node

          # Generate embeddings for relations
          relation_texts = []
          for relation in relations:
              relation_text = self._create_relation_text(relation)
              relation_texts.append(relation_text)

          relation_embeddings = await
  self.embedding_generator.embed_batch(relation_texts)

          # Create edges with embeddings
          entity_to_node_id = {e.text: nodes[self._generate_node_id(e)].id for e in
  entities}

          for i, relation in enumerate(relations):
              source_id = entity_to_node_id.get(relation.subject.text)
              target_id = entity_to_node_id.get(relation.object.text)

              if source_id and target_id:
                  edge_id = self._generate_edge_id(relation)

                  edge = GraphEdge(
                      id=edge_id,
                      source_id=source_id,
                      target_id=target_id,
                      relation=relation,
                      embedding=relation_embeddings[i],  # NEW
                      weight=relation.confidence,
                      metadata={
                          "relation_type": relation.relation_type.value,
                          "predicate": relation.predicate,
                          "confidence": relation.confidence,
                          "context": relation.context
                      }
                  )
                  edges[edge_id] = edge

          return KnowledgeGraph(nodes=nodes, edges=edges, ...)

      def _create_entity_text(self, entity: Entity, attributes: Dict[str, Attribute]) 
  -> str:
          """Create text representation for entity embedding"""
          text_parts = [entity.canonical_form, entity.entity_type.value]

          # Add key attributes
          for attr_name, attr in attributes.items():
              if attr.confidence > 0.8:  # Only high-confidence attributes
                  text_parts.append(f"{attr_name}:{attr.normalized_value}")

          return " ".join(text_parts)

      def _create_relation_text(self, relation: Relation) -> str:
          """Create text representation for relation embedding"""
          text = f"{relation.subject.text} {relation.predicate} 
  {relation.object.text}"
          if relation.context:
              text += f" context: {relation.context}"
          return text

  5. Storage Format for Neo4j

  def export_for_neo4j_storage(self, graph: KnowledgeGraph) -> Dict[str, Any]:
      """Export graph in Neo4j-ready format with embeddings"""
      return {
          "entities": [
              {
                  "id": node.id,
                  "name": node.entity.text,
                  "type": node.entity.entity_type.value,
                  "canonical_form": node.entity.canonical_form,
                  "confidence": node.entity.confidence,
                  "embedding": node.embedding,  # For vector index
                  "attributes": {
                      name: {
                          "value": attr.normalized_value,
                          "type": attr.attribute_type.value,
                          "confidence": attr.confidence
                      } for name, attr in node.attributes.items()
                  }
              } for node in graph.nodes.values()
          ],
          "relations": [
              {
                  "id": edge.id,
                  "source_id": edge.source_id,
                  "target_id": edge.target_id,
                  "type": edge.relation.relation_type.value,
                  "predicate": edge.relation.predicate,
                  "confidence": edge.relation.confidence,
                  "embedding": edge.embedding,  # For vector index
                  "context": edge.relation.context
              } for edge in graph.edges.values()
          ]
      }

  6. Retrieval Strategy

  # Multi-modal retrieval combining:
  # 1. Vector similarity on entities
  # 2. Vector similarity on relations  
  # 3. Graph traversal for context
  # 4. Original document chunks

  retriever = VectorCypherRetriever(
      driver=neo4j_driver,
      index_name="entity_embeddings",
      embedder=embedding_generator,
      retrieval_query="""
      MATCH (entity)-[r]-(connected)
      OPTIONAL MATCH (entity)-[:EXTRACTED_FROM]->(doc:Document)
      RETURN entity, r, connected, doc
      """,
      return_properties=["name", "type", "confidence", "attributes"]
  )

  Key Benefits of This Approach:

  1. Multi-Vector Strategy: Separate embeddings for entities, relations, and documents
  2. Graph-Native: Leverages Neo4j's graph structure + vector capabilities
  3. Retrieval Flexibility: Vector similarity + graph traversal + original text
  4. Official Support: Uses Neo4j's 2025 GraphRAG package
  5. Scalable: Handles large documents through chunking and batch processing

  This solution provides the most comprehensive and Neo4j-native approach for GraphRAG
   in 2025.