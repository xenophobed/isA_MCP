"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the SearchService dataclass and pure logic.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/search_service/search_service.py

Focus: SearchResult dataclass and interface contracts (NOT service initialization)
"""
import pytest


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.search
class TestSearchResultDataclassGolden:
    """
    Golden tests for SearchResult dataclass - DO NOT MODIFY.

    Tests the data structure that SearchService returns.
    """

    def test_search_result_required_fields(self):
        """
        CURRENT BEHAVIOR: SearchResult has required fields.
        """
        from services.search_service.search_service import SearchResult

        result = SearchResult(
            id='test_1',
            type='tool',
            name='test_tool',
            description='A test tool',
            score=0.95,
            db_id=42,
            metadata={}
        )

        assert result.id == 'test_1'
        assert result.type == 'tool'
        assert result.name == 'test_tool'
        assert result.description == 'A test tool'
        assert result.score == 0.95
        assert result.db_id == 42

    def test_search_result_optional_schema_fields(self):
        """
        CURRENT BEHAVIOR: inputSchema, outputSchema, annotations default to None.
        """
        from services.search_service.search_service import SearchResult

        result = SearchResult(
            id='test_1',
            type='tool',
            name='test_tool',
            description='Test',
            score=0.9,
            db_id=1,
            metadata={}
        )

        assert result.inputSchema is None
        assert result.outputSchema is None
        assert result.annotations is None

    def test_search_result_with_schema(self):
        """
        CURRENT BEHAVIOR: Schema fields can be set.
        """
        from services.search_service.search_service import SearchResult

        input_schema = {'type': 'object', 'properties': {'input': {'type': 'string'}}}
        output_schema = {'type': 'string'}
        annotations = {'category': 'utility'}

        result = SearchResult(
            id='test_1',
            type='tool',
            name='test_tool',
            description='Test',
            score=0.9,
            db_id=1,
            metadata={},
            inputSchema=input_schema,
            outputSchema=output_schema,
            annotations=annotations
        )

        assert result.inputSchema == input_schema
        assert result.outputSchema == output_schema
        assert result.annotations == annotations

    def test_search_result_is_dataclass(self):
        """
        CURRENT BEHAVIOR: SearchResult is a dataclass.
        """
        from services.search_service.search_service import SearchResult
        from dataclasses import is_dataclass

        assert is_dataclass(SearchResult)

    def test_search_result_type_values(self):
        """
        CURRENT BEHAVIOR: Valid type values are 'tool', 'prompt', 'resource'.
        """
        from services.search_service.search_service import SearchResult

        # These should all be valid
        for item_type in ['tool', 'prompt', 'resource']:
            result = SearchResult(
                id='test_1',
                type=item_type,
                name='test',
                description='Test',
                score=0.9,
                db_id=1,
                metadata={}
            )
            assert result.type == item_type


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.search
class TestSearchServiceInterfaceGolden:
    """
    Golden tests for SearchService interface - DO NOT MODIFY.

    Tests that SearchService has expected methods.
    """

    def test_search_service_has_search_method(self):
        """
        CURRENT BEHAVIOR: SearchService has search() method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'search')
        assert inspect.iscoroutinefunction(SearchService.search)

    def test_search_service_has_search_tools_method(self):
        """
        CURRENT BEHAVIOR: SearchService has search_tools() convenience method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'search_tools')
        assert inspect.iscoroutinefunction(SearchService.search_tools)

    def test_search_service_has_search_prompts_method(self):
        """
        CURRENT BEHAVIOR: SearchService has search_prompts() convenience method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'search_prompts')
        assert inspect.iscoroutinefunction(SearchService.search_prompts)

    def test_search_service_has_search_resources_method(self):
        """
        CURRENT BEHAVIOR: SearchService has search_resources() convenience method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'search_resources')
        assert inspect.iscoroutinefunction(SearchService.search_resources)

    def test_search_service_has_get_stats_method(self):
        """
        CURRENT BEHAVIOR: SearchService has get_stats() method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'get_stats')
        assert inspect.iscoroutinefunction(SearchService.get_stats)

    def test_search_service_has_initialize_method(self):
        """
        CURRENT BEHAVIOR: SearchService has initialize() method.
        """
        from services.search_service.search_service import SearchService
        import inspect

        assert hasattr(SearchService, 'initialize')
        assert inspect.iscoroutinefunction(SearchService.initialize)

    def test_search_method_signature(self):
        """
        CURRENT BEHAVIOR: search() accepts query, item_type, limit, score_threshold.
        """
        from services.search_service.search_service import SearchService
        import inspect

        sig = inspect.signature(SearchService.search)
        params = list(sig.parameters.keys())

        assert 'query' in params
        assert 'item_type' in params
        assert 'limit' in params
        assert 'score_threshold' in params

    def test_search_default_parameters(self):
        """
        CURRENT BEHAVIOR: search() has specific defaults.
        """
        from services.search_service.search_service import SearchService
        import inspect

        sig = inspect.signature(SearchService.search)

        # Check defaults
        assert sig.parameters['item_type'].default is None
        assert sig.parameters['limit'].default == 10
        assert sig.parameters['score_threshold'].default == 0.3
