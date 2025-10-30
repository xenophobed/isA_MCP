#!/usr/bin/env python3
"""
RAG Diagnostic Service
Diagnoses issues in the RAG pipeline: storage -> retrieval -> generation

Uses evaluation metrics to identify problems and suggest fixes.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .metrics_service import RAGMetricsService
from tools.services.intelligence_service.vector_db.supabase_vector_db import SupabaseVectorDB


@dataclass
class DiagnosticResult:
    """Result of a single diagnostic step"""
    step_name: str
    success: bool
    status: str  # "pass", "warning", "fail"
    message: str
    metrics: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


class RAGDiagnosticService:
    """
    Diagnostic service for RAG systems
    Performs step-by-step diagnosis and quality assessment
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.metrics_service = RAGMetricsService(model=model)
        self.vector_db = SupabaseVectorDB()
        self.diagnostic_history: List[DiagnosticResult] = []

    async def diagnose_storage(self, user_id: str) -> DiagnosticResult:
        """
        Step 1: Diagnose data storage
        Checks if data exists in vector database and analyzes distribution
        """
        try:
            # Query vector database - use the configured table name
            table_name = self.vector_db.table_name  # Get actual table name from vector_db
            result = self.vector_db.supabase.client.schema(self.vector_db.schema).table(table_name) \
                .select('*') \
                .eq('user_id', user_id) \
                .execute()

            records = result.data if hasattr(result, 'data') else []

            if len(records) == 0:
                return DiagnosticResult(
                    step_name="Storage Check",
                    success=False,
                    status="fail",
                    message=f"No data found for user_id: {user_id}",
                    suggestions=[
                        "Check if you used the correct user_id when storing data",
                        "Try querying with a different user_id (e.g., 'testuser')",
                        "Run store_knowledge to ingest PDFs"
                    ],
                    data={'record_count': 0}
                )

            # Analyze data distribution
            pdf_counts = {}
            page_counts = {}
            chunk_counts = {}

            for record in records:
                metadata = record.get('metadata', {})
                pdf_name = metadata.get('pdf_name', 'unknown')
                page_num = metadata.get('page_number', 'N/A')
                chunk_idx = metadata.get('chunk_index')

                pdf_counts[pdf_name] = pdf_counts.get(pdf_name, 0) + 1

                if pdf_name not in page_counts:
                    page_counts[pdf_name] = set()
                if page_num != 'N/A':
                    page_counts[pdf_name].add(page_num)

                if chunk_idx is not None:
                    chunk_counts[pdf_name] = chunk_counts.get(pdf_name, 0) + 1

            # Build statistics
            stats = {
                'total_records': len(records),
                'pdf_count': len(pdf_counts),
                'pdfs': {
                    pdf: {
                        'records': count,
                        'pages': len(page_counts.get(pdf, set())),
                        'chunks': chunk_counts.get(pdf, 0)
                    }
                    for pdf, count in pdf_counts.items()
                }
            }

            # Sample records
            sample_records = []
            for record in records[:3]:
                metadata = record.get('metadata', {})
                sample_records.append({
                    'pdf': metadata.get('pdf_name', 'N/A'),
                    'page': metadata.get('page_number', 'N/A'),
                    'chunk': metadata.get('chunk_index', 'N/A'),
                    'text_preview': record.get('text', '')[:150]
                })

            return DiagnosticResult(
                step_name="Storage Check",
                success=True,
                status="pass",
                message=f"Found {len(records)} records for user {user_id}",
                metrics=stats,
                data={'sample_records': sample_records}
            )

        except Exception as e:
            return DiagnosticResult(
                step_name="Storage Check",
                success=False,
                status="fail",
                message=f"Database query failed: {str(e)}",
                suggestions=["Check database connection", "Verify Supabase credentials"]
            )

    async def diagnose_retrieval(
        self,
        rag_service: Any,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> DiagnosticResult:
        """
        Step 2: Diagnose retrieval quality
        Tests retrieval and evaluates context relevance
        """
        try:
            # Execute retrieval
            retrieval_result = await rag_service.retrieve(
                user_id=user_id,
                query=query,
                top_k=top_k
            )

            if not retrieval_result.get('success'):
                return DiagnosticResult(
                    step_name="Retrieval Check",
                    success=False,
                    status="fail",
                    message=f"Retrieval failed: {retrieval_result.get('error')}",
                    suggestions=["Check embedding service", "Verify vector database connection"]
                )

            page_results = retrieval_result.get('page_results', [])

            if len(page_results) == 0:
                return DiagnosticResult(
                    step_name="Retrieval Check",
                    success=False,
                    status="fail",
                    message="Retrieval returned 0 results",
                    suggestions=[
                        "Query may be semantically distant from document content",
                        "Try more general query terms",
                        "Check if documents contain relevant information",
                        "Consider adjusting chunking strategy"
                    ],
                    data={'query': query, 'results_count': 0}
                )

            # Evaluate retrieval quality
            contexts = [r.get('text', '') for r in page_results]

            context_relevance, context_precision = await asyncio.gather(
                self.metrics_service.compute_context_relevance(query, contexts),
                self.metrics_service.compute_context_precision(query, contexts)
            )

            metrics = {
                'results_count': len(page_results),
                'context_relevance': context_relevance,
                'context_precision': context_precision,
                'avg_similarity': sum(r.get('similarity_score', 0) for r in page_results) / len(page_results)
            }

            # Determine status
            if context_relevance < 0.5:
                status = "warning"
                message = f"Low context relevance ({context_relevance:.2f}). Retrieved pages may not be relevant."
                suggestions = [
                    "Optimize retrieval strategy (e.g., hybrid search)",
                    "Adjust chunking parameters",
                    "Use query expansion or reformulation"
                ]
            elif context_relevance < 0.7:
                status = "warning"
                message = f"Moderate context relevance ({context_relevance:.2f}). Room for improvement."
                suggestions = ["Fine-tune retrieval parameters", "Consider reranking"]
            else:
                status = "pass"
                message = f"Good context relevance ({context_relevance:.2f})"
                suggestions = []

            # Build result summary
            result_summaries = []
            for idx, result in enumerate(page_results[:3], 1):
                result_summaries.append({
                    'rank': idx,
                    'page': result.get('page_number'),
                    'pdf': result.get('metadata', {}).get('pdf_name', 'N/A'),
                    'similarity': result.get('similarity_score', 0),
                    'text_preview': result.get('text', '')[:150]
                })

            return DiagnosticResult(
                step_name="Retrieval Check",
                success=True,
                status=status,
                message=message,
                metrics=metrics,
                suggestions=suggestions,
                data={'top_results': result_summaries}
            )

        except Exception as e:
            return DiagnosticResult(
                step_name="Retrieval Check",
                success=False,
                status="fail",
                message=f"Retrieval diagnostic failed: {str(e)}",
                suggestions=["Check RAG service configuration"]
            )

    async def diagnose_generation(
        self,
        rag_service: Any,
        user_id: str,
        query: str,
        retrieval_result: Dict[str, Any]
    ) -> DiagnosticResult:
        """
        Step 3: Diagnose generation quality
        Tests answer generation and evaluates faithfulness/relevance
        """
        try:
            # Execute generation
            generation_result = await rag_service.generate(
                user_id=user_id,
                query=query,
                retrieval_result=retrieval_result,
                generation_config={
                    'model': 'gpt-4o-mini',
                    'provider': 'yyds',
                    'temperature': 0.3
                }
            )

            if not generation_result.get('success'):
                return DiagnosticResult(
                    step_name="Generation Check",
                    success=False,
                    status="fail",
                    message=f"Generation failed: {generation_result.get('error')}",
                    suggestions=["Check LLM service", "Verify API keys"]
                )

            answer = generation_result.get('answer', '')
            sources = generation_result.get('sources', {})
            page_results = retrieval_result.get('page_results', [])
            contexts = [r.get('text', '') for r in page_results]

            # Check for degraded response
            is_degraded = any([
                'Based on your knowledge base' in answer,
                'I cannot find' in answer,
                '无法找到' in answer,
                '没有找到' in answer,
                len(contexts) == 0
            ])

            # Evaluate answer quality
            faithfulness, answer_relevance = await asyncio.gather(
                self.metrics_service.compute_faithfulness(answer, contexts),
                self.metrics_service.compute_answer_relevance(query, answer)
            )

            metrics = {
                'faithfulness': faithfulness,
                'answer_relevance': answer_relevance,
                'is_degraded': is_degraded,
                'source_count': sources.get('page_count', 0),
                'photo_count': sources.get('photo_count', 0)
            }

            # Determine status
            if is_degraded:
                status = "fail"
                message = "Degraded response detected. Retrieved context cannot answer the question."
                suggestions = [
                    "Query may be out of scope for the knowledge base",
                    "Try broader query terms",
                    "Check if documents contain relevant information"
                ]
            elif faithfulness < 0.6:
                status = "warning"
                message = f"Low faithfulness ({faithfulness:.2f}). Answer may contain hallucinations."
                suggestions = [
                    "Adjust LLM temperature (lower for more factual)",
                    "Improve prompt engineering",
                    "Use stricter grounding instructions"
                ]
            elif answer_relevance < 0.6:
                status = "warning"
                message = f"Low answer relevance ({answer_relevance:.2f}). Answer may not address the query."
                suggestions = [
                    "Improve context selection",
                    "Refine generation prompt",
                    "Check if retrieved contexts are relevant"
                ]
            else:
                status = "pass"
                message = f"Good answer quality (faithfulness: {faithfulness:.2f}, relevance: {answer_relevance:.2f})"
                suggestions = []

            return DiagnosticResult(
                step_name="Generation Check",
                success=True,
                status=status,
                message=message,
                metrics=metrics,
                suggestions=suggestions,
                data={'answer': answer[:500]}
            )

        except Exception as e:
            return DiagnosticResult(
                step_name="Generation Check",
                success=False,
                status="fail",
                message=f"Generation diagnostic failed: {str(e)}",
                suggestions=["Check generation configuration"]
            )

    async def diagnose_query_match(
        self,
        query: str,
        records: List[Dict[str, Any]]
    ) -> DiagnosticResult:
        """
        Step 4: Analyze query-document matching
        Checks if query keywords appear in documents
        """
        try:
            # Extract query keywords
            query_keywords = set(query.lower().split())

            # Find matching records
            matching_records = []
            for record in records:
                text = record.get('text', '').lower()
                matched_keywords = [kw for kw in query_keywords if kw in text]

                if matched_keywords:
                    matching_records.append({
                        'pdf': record.get('metadata', {}).get('pdf_name', 'N/A'),
                        'page': record.get('metadata', {}).get('page_number', 'N/A'),
                        'matched_keywords': matched_keywords,
                        'text_preview': record.get('text', '')[:200]
                    })

            match_rate = len(matching_records) / len(records) if records else 0

            if len(matching_records) == 0:
                status = "warning"
                message = f"No documents contain query keywords: {query_keywords}"
                suggestions = [
                    "Documents may not contain relevant information",
                    "Try synonyms or related terms",
                    "Use more general query terms",
                    "Semantic search may still find relevant content"
                ]
            elif match_rate < 0.1:
                status = "warning"
                message = f"Only {len(matching_records)} out of {len(records)} records contain query keywords ({match_rate:.1%})"
                suggestions = ["Query may be specific - semantic search will help"]
            else:
                status = "pass"
                message = f"Found {len(matching_records)} records with query keywords ({match_rate:.1%})"
                suggestions = []

            return DiagnosticResult(
                step_name="Query Match Analysis",
                success=True,
                status=status,
                message=message,
                metrics={
                    'query_keywords': list(query_keywords),
                    'matching_records': len(matching_records),
                    'total_records': len(records),
                    'match_rate': match_rate
                },
                suggestions=suggestions,
                data={'top_matches': matching_records[:5]}
            )

        except Exception as e:
            return DiagnosticResult(
                step_name="Query Match Analysis",
                success=False,
                status="fail",
                message=f"Query match analysis failed: {str(e)}"
            )

    async def run_full_diagnostic(
        self,
        rag_service: Any,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Run complete diagnostic pipeline
        Returns comprehensive diagnostic report
        """
        print("\n" + "="*80)
        print("🏥 RAG System Diagnostic Report")
        print("="*80)
        print(f"\nUser ID: {user_id}")
        print(f"Query: {query}")

        results = {}

        # Step 1: Storage
        print("\n" + "-"*80)
        print("STEP 1: Storage Diagnostic")
        print("-"*80)
        storage_result = await self.diagnose_storage(user_id)
        results['storage'] = storage_result
        self._print_result(storage_result)

        if storage_result.status == "fail":
            print("\n🛑 Stopping diagnostic: Storage issue detected")
            return self._build_report(results, overall_status="fail")

        # Get records for later analysis
        table_name = self.vector_db.table_name
        records_result = self.vector_db.supabase.client.schema(self.vector_db.schema).table(table_name) \
            .select('*') \
            .eq('user_id', user_id) \
            .execute()
        records = records_result.data if hasattr(records_result, 'data') else []

        # Step 2: Retrieval
        print("\n" + "-"*80)
        print("STEP 2: Retrieval Diagnostic")
        print("-"*80)
        retrieval_result = await self.diagnose_retrieval(rag_service, user_id, query, top_k)
        results['retrieval'] = retrieval_result
        self._print_result(retrieval_result)

        if retrieval_result.status == "fail":
            # Still run query match analysis
            print("\n" + "-"*80)
            print("STEP 4: Query Match Analysis")
            print("-"*80)
            match_result = await self.diagnose_query_match(query, records)
            results['query_match'] = match_result
            self._print_result(match_result)

            print("\n🛑 Stopping diagnostic: Retrieval issue detected")
            return self._build_report(results, overall_status="fail")

        # Get retrieval result data
        retrieval_data = retrieval_result.data or {}
        raw_retrieval_result = {
            'success': True,
            'page_results': []  # Would need to pass through from rag_service
        }

        # Step 3: Generation
        print("\n" + "-"*80)
        print("STEP 3: Generation Diagnostic")
        print("-"*80)
        # Note: Need to get actual retrieval_result from rag_service
        # For now, skip generation if we can't get it
        try:
            # Re-execute retrieval to get full result
            full_retrieval = await rag_service.retrieve(user_id=user_id, query=query, top_k=top_k)
            generation_result = await self.diagnose_generation(rag_service, user_id, query, full_retrieval)
            results['generation'] = generation_result
            self._print_result(generation_result)
        except Exception as e:
            print(f"⚠️  Could not run generation diagnostic: {e}")

        # Step 4: Query Match
        print("\n" + "-"*80)
        print("STEP 4: Query Match Analysis")
        print("-"*80)
        match_result = await self.diagnose_query_match(query, records)
        results['query_match'] = match_result
        self._print_result(match_result)

        # Determine overall status
        statuses = [r.status for r in results.values()]
        if "fail" in statuses:
            overall_status = "fail"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "pass"

        return self._build_report(results, overall_status)

    def _print_result(self, result: DiagnosticResult):
        """Pretty print diagnostic result"""
        status_icons = {"pass": "✅", "warning": "⚠️", "fail": "❌"}
        icon = status_icons.get(result.status, "❓")

        print(f"\n{icon} {result.step_name}: {result.message}")

        if result.metrics:
            print("\n📊 Metrics:")
            for key, value in result.metrics.items():
                if isinstance(value, float):
                    print(f"    {key}: {value:.2f}")
                elif isinstance(value, dict):
                    print(f"    {key}:")
                    for k, v in value.items():
                        print(f"      {k}: {v}")
                else:
                    print(f"    {key}: {value}")

        if result.suggestions:
            print("\n💡 Suggestions:")
            for suggestion in result.suggestions:
                print(f"    • {suggestion}")

    def _build_report(self, results: Dict[str, DiagnosticResult], overall_status: str) -> Dict[str, Any]:
        """Build final diagnostic report"""
        print("\n" + "="*80)
        print("📋 DIAGNOSTIC SUMMARY")
        print("="*80)

        status_icons = {"pass": "✅", "warning": "⚠️", "fail": "❌"}

        for step_name, result in results.items():
            icon = status_icons.get(result.status, "❓")
            print(f"{icon} {result.step_name}: {result.status.upper()}")

        print(f"\n🎯 Overall Status: {overall_status.upper()}")

        return {
            'overall_status': overall_status,
            'results': {k: v.__dict__ for k, v in results.items()},
            'timestamp': asyncio.get_event_loop().time()
        }


async def example_usage():
    """Example usage of diagnostic service"""
    from tools.services.data_analytics_service.services.digital_service.patterns.custom_rag_service import (
        get_custom_rag_service
    )

    # Initialize services
    rag_service = get_custom_rag_service()
    diagnostic_service = RAGDiagnosticService(model="gpt-4o-mini")

    # Run diagnostic
    report = await diagnostic_service.run_full_diagnostic(
        rag_service=rag_service,
        user_id="test_user_rag_page",
        query="乙肝可以存干细胞么",
        top_k=5
    )

    print("\n" + "="*80)
    print("Diagnostic complete!")


if __name__ == "__main__":
    asyncio.run(example_usage())
