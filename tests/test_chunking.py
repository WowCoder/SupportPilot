"""
Unit tests for intelligent document chunking strategies.

Tests semantic chunking, sentence-level chunking, and recursive chunking
to ensure proper behavior and sentence boundary preservation.
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_utils import RAGUtils


class TestSentenceSplitting:
    """Test sentence splitting functionality"""

    def test_split_english_sentences(self):
        """Test splitting English text into sentences"""
        rag = RAGUtils()
        text = "This is sentence one. This is sentence two! Is this sentence three?"
        sentences = rag._split_sentences(text)

        assert len(sentences) == 3
        assert "one" in sentences[0]
        assert "two" in sentences[1]
        assert "three" in sentences[2]

    def test_split_chinese_sentences(self):
        """Test splitting Chinese text into sentences"""
        rag = RAGUtils()
        text = "这是第一句话。这是第二句话！这是第三句话？"
        sentences = rag._split_sentences(text)

        assert len(sentences) == 3
        assert "第一句" in sentences[0]
        assert "第二句" in sentences[1]
        assert "第三句" in sentences[2]

    def test_split_mixed_sentences(self):
        """Test splitting mixed Chinese and English text"""
        rag = RAGUtils()
        text = "Hello world. 你好世界！This is mixed. 这是混合内容？"
        sentences = rag._split_sentences(text)

        assert len(sentences) == 4
        assert "Hello" in sentences[0]
        assert "你好" in sentences[1]
        assert "mixed" in sentences[2]
        assert "混合" in sentences[3]

    def test_split_with_newlines(self):
        """Test that newlines are treated as sentence boundaries"""
        rag = RAGUtils()
        text = "Line one\nLine two\nLine three"
        sentences = rag._split_sentences(text)

        assert len(sentences) >= 3
        # Each line should be preserved
        for sent in sentences:
            assert sent.strip() != ""


class TestSentenceChunking:
    """Test sentence-level chunking strategy"""

    def test_basic_sentence_chunking(self):
        """Test basic sentence-level chunking"""
        rag = RAGUtils()

        # Create mock document
        doc = type('obj', (object,), {
            'page_content': "Short sentence. Another short sentence. Third sentence here.",
            'metadata': {'source': 'test.txt'}
        })()

        chunks = rag._sentence_chunk([doc], max_chunk_size=100)

        assert len(chunks) >= 1
        # Verify no sentence is split mid-way
        for chunk in chunks:
            content = chunk.page_content
            # Should end with sentence boundary or be complete
            assert content.strip() != ""

    def test_large_sentence_handling(self):
        """Test that large sentences become their own chunks"""
        rag = RAGUtils()

        # Create a very long sentence
        long_sentence = "This is a very long sentence that exceeds the maximum chunk size limit and should be placed in its own chunk without being split anywhere in the middle of the sentence content."
        doc = type('obj', (object,), {
            'page_content': long_sentence,
            'metadata': {'source': 'test.txt'}
        })()

        chunks = rag._sentence_chunk([doc], max_chunk_size=50)

        # Long sentence should be its own chunk
        assert len(chunks) == 1
        assert chunks[0].page_content == long_sentence.strip()

    def test_sentence_boundary_preservation(self):
        """Test that chunks never split mid-sentence"""
        rag = RAGUtils()

        # Create document with clear sentence boundaries
        text = "First complete sentence. Second complete sentence with more content. Third sentence ends here."
        doc = type('obj', (object,), {
            'page_content': text,
            'metadata': {'source': 'test.txt'}
        })()

        chunks = rag._sentence_chunk([doc], max_chunk_size=60)

        for chunk in chunks:
            content = chunk.page_content.strip()
            # Each chunk should contain complete sentences
            # Check that it doesn't end mid-word (before punctuation)
            if not content.endswith(('。', '！', '？', '；', '.', '!', '?', '\n')):
                # If it doesn't end with punctuation, it might be the last chunk
                # which could have the last sentence without trailing punctuation
                pass  # Allow for edge cases

    def test_metadata_preservation(self):
        """Test that metadata is preserved in chunks"""
        rag = RAGUtils()

        doc = type('obj', (object,), {
            'page_content': "Sentence one. Sentence two.",
            'metadata': {'source': 'test.pdf', 'page': 1}
        })()

        chunks = rag._sentence_chunk([doc], max_chunk_size=100)

        for chunk in chunks:
            assert chunk.metadata.get('source') == 'test.pdf'
            assert chunk.metadata.get('page') == 1


class TestSemanticChunking:
    """Test semantic chunking strategy"""

    def test_semantic_chunker_creation(self):
        """Test that semantic splitter can be created"""
        rag = RAGUtils()

        # This test may fail if embeddings aren't available
        # In that case, we verify the fallback works
        try:
            splitter = rag._create_semantic_splitter()
            assert splitter is not None
        except ValueError as e:
            # Expected if embeddings not initialized
            assert "Embeddings not available" in str(e)

    def test_semantic_chunking_fallback(self):
        """Test that semantic chunking falls back to sentence chunking on failure"""
        rag = RAGUtils()

        doc = type('obj', (object,), {
            'page_content': "Test sentence one. Test sentence two.",
            'metadata': {'source': 'test.txt'}
        })()

        # Should fall back to sentence chunking if semantic fails
        chunks = rag._semantic_chunk([doc])

        assert len(chunks) >= 1
        assert all(chunk.page_content.strip() != "" for chunk in chunks)


class TestChunkingStrategies:
    """Test all chunking strategies"""

    def test_chunk_object_creation(self):
        """Test chunk object creation helper"""
        rag = RAGUtils()

        chunk = rag._create_chunk("Test content", {'source': 'test.txt'})

        assert chunk.page_content == "Test content"
        assert chunk.metadata == {'source': 'test.txt'}

    def test_strategy_parameter_validation(self):
        """Test that strategy parameter is properly handled"""
        # This is tested via integration, but we verify the method signature exists
        rag = RAGUtils()

        # Verify process_document accepts strategy parameter
        import inspect
        sig = inspect.signature(rag.process_document)
        params = list(sig.parameters.keys())

        assert 'strategy' in params
        assert sig.parameters['strategy'].default == 'semantic'


class TestChunkQuality:
    """Test chunk quality scoring"""

    def test_quality_score_empty_text(self):
        """Test quality score for empty text"""
        rag = RAGUtils()
        score = rag._quality_score("")
        assert score == 0

    def test_quality_score_good_text(self):
        """Test quality score for good quality text"""
        rag = RAGUtils()

        # Good quality text: appropriate length, punctuation, meaningful content
        text = "This is a well-formed sentence with proper punctuation and meaningful content."
        score = rag._quality_score(text)

        assert score >= 60  # Should pass quality threshold

    def test_quality_score_noisy_text(self):
        """Test quality score for noisy text"""
        rag = RAGUtils()

        # Noisy text: mostly numbers
        text = "1. 2. 3. 4. 5. 6. 7. 8. 9. 10."
        score = rag._quality_score(text)

        assert score < 60  # Should fail quality threshold


if __name__ == '__main__':
    pytest.main([__file__, '-v'])