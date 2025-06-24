import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.toolkits import DeepResearchTool


class TestDeepResearchTool:
    """Test cases for DeepResearchTool"""

    @pytest.fixture
    def deep_research_tool(self):
        """Create a DeepResearchTool instance for testing"""
        return DeepResearchTool()

    def test_tool_initialization(self, deep_research_tool):
        """Test that the tool initializes correctly"""
        assert deep_research_tool.name == "deep_research"
        assert "深度研究任务" in deep_research_tool.description
        assert deep_research_tool.args_schema is not None

    def test_input_schema(self, deep_research_tool):
        """Test the input schema validation"""
        # Test valid input
        valid_input = deep_research_tool.args_schema(
            query="武汉天气如何？",
            debug=True,
            max_plan_iterations=3,
            max_step_num=20,
            enable_background_investigation=False
        )
        assert valid_input.query == "武汉天气如何？"
        assert valid_input.debug is True
        assert valid_input.max_plan_iterations == 3

        # Test default values
        minimal_input = deep_research_tool.args_schema(query="测试查询")
        assert minimal_input.debug is False
        assert minimal_input.max_plan_iterations == 3
        assert minimal_input.max_step_num == 20
        assert minimal_input.enable_background_investigation is False

    def test_sync_run_not_implemented(self, deep_research_tool):
        """Test that synchronous run raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            deep_research_tool._run()

    @pytest.mark.asyncio
    async def test_arun_empty_query(self, deep_research_tool):
        """Test that empty query returns appropriate error"""
        result = await deep_research_tool._arun("")
        assert "查询不能为空" in result

    @pytest.mark.asyncio
    async def test_arun_import_error(self, deep_research_tool):
        """Test handling of import errors"""
        with patch('sys.path'):
            with patch('os.path.join', return_value="/nonexistent/path"):
                result = await deep_research_tool._arun("测试查询")
                assert "无法导入DeerFlow模块" in result

    @pytest.mark.asyncio
    async def test_arun_successful_execution(self, deep_research_tool):
        """Test successful execution with mocked DeerFlow"""
        # Mock the graph and its astream method
        mock_graph = MagicMock()
        mock_astream_result = [
            {"other_key": "value"},
            {"final_report": "这是一个测试报告"}
        ]
        mock_graph.astream = AsyncMock(return_value=iter(mock_astream_result))
        
        # Mock the build_graph function
        with patch('deer_flow.src.graph.build_graph', return_value=mock_graph):
            with patch('os.path.join', return_value="/mocked/deer_flow/path"):
                with patch('sys.path'):
                    result = await deep_research_tool._arun("武汉天气如何？")
                    assert "这是一个测试报告" in result

    @pytest.mark.asyncio
    async def test_arun_no_final_report(self, deep_research_tool):
        """Test case where no final report is generated"""
        # Mock the graph without final_report
        mock_graph = MagicMock()
        mock_astream_result = [
            {"other_key": "value"},
            {"messages": [{"content": "test"}]}
        ]
        mock_graph.astream = AsyncMock(return_value=iter(mock_astream_result))
        
        with patch('deer_flow.src.graph.build_graph', return_value=mock_graph):
            with patch('os.path.join', return_value="/mocked/deer_flow/path"):
                with patch('sys.path'):
                    result = await deep_research_tool._arun("测试查询")
                    assert "研究过程中未能生成最终报告" in result

    @pytest.mark.asyncio
    async def test_arun_with_custom_parameters(self, deep_research_tool):
        """Test execution with custom parameters"""
        mock_graph = MagicMock()
        mock_astream_result = [{"final_report": "自定义参数测试报告"}]
        mock_graph.astream = AsyncMock(return_value=iter(mock_astream_result))
        
        with patch('deer_flow.src.graph.build_graph', return_value=mock_graph):
            with patch('os.path.join', return_value="/mocked/deer_flow/path"):
                with patch('sys.path'):
                    result = await deep_research_tool._arun(
                        query="测试查询",
                        debug=True,
                        max_plan_iterations=5,
                        max_step_num=30,
                        enable_background_investigation=True
                    )
                    assert "自定义参数测试报告" in result

    @pytest.mark.asyncio
    async def test_arun_exception_handling(self, deep_research_tool):
        """Test general exception handling"""
        with patch('deer_flow.src.graph.build_graph', side_effect=Exception("测试异常")):
            with patch('os.path.join', return_value="/mocked/deer_flow/path"):
                with patch('sys.path'):
                    result = await deep_research_tool._arun("测试查询")
                    assert "深度研究执行失败" in result
                    assert "测试异常" in result


@pytest.mark.asyncio
async def test_real_deerflow_integration():
    """Integration test with real DeerFlow (requires deer_flow directory)"""
    # This test only runs if deer_flow directory exists
    deer_flow_path = os.path.join(os.getcwd(), "deer_flow")
    if not os.path.exists(deer_flow_path):
        pytest.skip("deer_flow directory not found, skipping integration test")
    
    tool = DeepResearchTool()
    
    # Test with a simple query
    result = await tool._arun(
        query="简单测试：什么是人工智能？（请用一句话回答）",
        debug=False,
        max_plan_iterations=1,
        max_step_num=3,
        enable_background_investigation=False
    )
    
    # Check that we got some kind of response
    assert isinstance(result, str)
    assert len(result) > 0
    assert "无法导入DeerFlow模块" not in result


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])