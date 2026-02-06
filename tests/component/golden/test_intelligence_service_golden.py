"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of Intelligence Services.
If these tests fail, it means behavior has changed unexpectedly.

Services Under Test:
- tools/services/intelligence_service/language/text_generator.py
- tools/services/intelligence_service/language/embedding_generator.py
- tools/services/intelligence_service/vision/image_analyzer.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.llm
class TestTextGeneratorGolden:
    """
    Golden tests for TextGenerator - DO NOT MODIFY.

    Key characteristics:
    - Uses ISA model client for text generation
    - Lazy loads client via _get_client()
    - Returns response.choices[0].message.content
    """

    @pytest.fixture
    def mock_client(self):
        """Create mock model client."""
        client = AsyncMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated text"))]
        ))
        return client

    @pytest.fixture
    def text_generator(self, mock_client):
        """Create TextGenerator with mocked client."""
        with patch('core.clients.model_client.get_isa_client') as mock_get:
            mock_get.return_value = mock_client
            from tools.intelligent_tools.language.text_generator import TextGenerator
            generator = TextGenerator()
            generator._client = mock_client
            return generator

    async def test_generate_returns_string(self, text_generator, mock_client):
        """
        CURRENT BEHAVIOR: generate() returns string content.
        """
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello, world!"))]
        )

        result = await text_generator.generate("Say hello")

        assert isinstance(result, str)
        assert result == "Hello, world!"

    async def test_generate_calls_chat_completions(self, text_generator, mock_client):
        """
        CURRENT BEHAVIOR: Uses chat.completions.create API.
        """
        await text_generator.generate("Test prompt")

        mock_client.chat.completions.create.assert_called()

    async def test_generate_accepts_temperature(self, text_generator, mock_client):
        """
        CURRENT BEHAVIOR: Accepts temperature parameter.
        """
        await text_generator.generate("Test", temperature=0.5)

        mock_client.chat.completions.create.assert_called()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs.get('temperature') == 0.5


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.embedding
class TestEmbeddingGeneratorGolden:
    """
    Golden tests for EmbeddingGenerator - DO NOT MODIFY.

    Key characteristics:
    - Model: text-embedding-3-small (1536D)
    - Handles single string or list of strings
    - Returns vectors
    """

    @pytest.fixture
    def mock_client(self):
        """Create mock model client."""
        client = AsyncMock()
        client.embeddings = MagicMock()
        client.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        ))
        return client

    @pytest.fixture
    def embedding_generator(self, mock_client):
        """Create EmbeddingGenerator with mocked client."""
        with patch('core.clients.model_client.get_isa_client') as mock_get:
            mock_get.return_value = mock_client
            from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator
            generator = EmbeddingGenerator()
            generator._client = mock_client
            return generator

    async def test_embed_returns_vector(self, embedding_generator, mock_client):
        """
        CURRENT BEHAVIOR: embed() returns vector (list of floats).
        """
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )

        result = await embedding_generator.embed("Hello world")

        assert isinstance(result, list)
        assert len(result) == 1536

    async def test_embed_calls_embeddings_create(self, embedding_generator, mock_client):
        """
        CURRENT BEHAVIOR: Uses embeddings.create API.
        """
        await embedding_generator.embed("Test")

        mock_client.embeddings.create.assert_called()


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.vision
class TestImageAnalyzerGolden:
    """
    Golden tests for ImageAnalyzer - DO NOT MODIFY.

    Key characteristics:
    - Accepts image as URL string or bytes
    - Returns ImageAnalysisResult dataclass
    - Uses vision.completions.create API
    """

    @pytest.fixture
    def mock_client(self):
        """Create mock model client."""
        client = AsyncMock()
        # Vision API uses vision.completions.create
        client.vision = MagicMock()
        client.vision.completions = MagicMock()
        client.vision.completions.create = AsyncMock(return_value=MagicMock(
            text="Image description"
        ))
        return client

    @pytest.fixture
    def image_analyzer(self, mock_client):
        """Create ImageAnalyzer with mocked client."""
        with patch('core.clients.model_client.get_isa_client') as mock_get:
            mock_get.return_value = mock_client
            from tools.intelligent_tools.vision.image_analyzer import ImageAnalyzer
            analyzer = ImageAnalyzer()
            analyzer._client = mock_client
            return analyzer

    async def test_analyze_returns_result_object(self, image_analyzer, mock_client):
        """
        CURRENT BEHAVIOR: analyze() returns ImageAnalysisResult with success and response.
        """
        result = await image_analyzer.analyze(
            image="https://example.com/image.jpg",
            prompt="Describe this image"
        )

        assert result is not None
        assert hasattr(result, 'success')

    async def test_analyze_calls_vision_api(self, image_analyzer, mock_client):
        """
        CURRENT BEHAVIOR: Uses vision.completions.create API.
        """
        await image_analyzer.analyze(
            image="https://example.com/image.jpg",
            prompt="Describe"
        )

        mock_client.vision.completions.create.assert_called()


@pytest.mark.golden
@pytest.mark.component
class TestIntelligenceServiceInterfaceGolden:
    """
    Golden tests for intelligence service interface contracts - DO NOT MODIFY.
    """

    def test_text_generator_has_generate_method(self):
        """
        CURRENT BEHAVIOR: TextGenerator has generate() async method.
        """
        from tools.intelligent_tools.language.text_generator import TextGenerator

        assert hasattr(TextGenerator, 'generate')

    def test_embedding_generator_has_embed_method(self):
        """
        CURRENT BEHAVIOR: EmbeddingGenerator has embed() async method.
        """
        from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator

        assert hasattr(EmbeddingGenerator, 'embed')

    def test_image_analyzer_has_analyze_method(self):
        """
        CURRENT BEHAVIOR: ImageAnalyzer has analyze() async method.
        """
        from tools.intelligent_tools.vision.image_analyzer import ImageAnalyzer

        assert hasattr(ImageAnalyzer, 'analyze')
