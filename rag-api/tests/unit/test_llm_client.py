from unittest.mock import patch, MagicMock

from src.llm.claude_bedrock_client import ClaudeBedrockClient

@patch("src.llm.claude_bedrock_client.settings")
@patch("src.llm.claude_bedrock_client.boto3.client")
def test_llm_answer_parses_text_blocks(mock_boto_client, mock_settings):
    mock_settings.aws_region = "us-east-1"
    mock_settings.bedrock_claude_model = "anthropic.claude-3-haiku-20240307-v1:0"
    
    mock_runtime = MagicMock()
    mock_runtime.invoke_model.return_value = {
        "body": MagicMock(
            read=lambda: b'{"content":[{"type":"text","text":"Part1 "},{"type":"text","text":"Part2"}]}'
        )
    }
    mock_boto_client.return_value = mock_runtime

    client = ClaudeBedrockClient()
    answer = client.answer("question?", ["ctx1", "ctx2"])

    assert "Part1 Part2" in answer
    mock_runtime.invoke_model.assert_called_once()

@patch("src.llm.claude_bedrock_client.settings")
@patch("src.llm.claude_bedrock_client.boto3.client")
def test_llm_summarize_parses_text_blocks(mock_boto_client, mock_settings):
    mock_settings.aws_region = "us-east-1"
    mock_settings.bedrock_claude_model = "anthropic.claude-3-haiku-20240307-v1:0"

    mock_runtime = MagicMock()
    mock_runtime.invoke_model.return_value = {
        "body": MagicMock(
            read=lambda: b'{"content":[{"type":"text","text":"Summary line"}]}'
        )
    }
    mock_boto_client.return_value = mock_runtime

    client = ClaudeBedrockClient()
    summary = client.summarize("summarize this")

    assert summary == "Summary line"
    mock_runtime.invoke_model.assert_called_once()

