import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch

from backend.agents.processor import (
    ResultProcessor, ProcessingStage, ProcessingStrategy, 
    ProcessingRule, ProcessingContext
)
from backend.agents.communication import (
    Message, MessageType, MessagePriority, MessageBus
)
from backend.analysis import ResultAggregator, ResultType, ResultPriority


@pytest.fixture
def result_aggregator():
    """Fixture for ResultAggregator."""
    return ResultAggregator()


@pytest.fixture
async def message_bus():
    """Fixture for MessageBus."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def result_processor(result_aggregator, message_bus):
    """Fixture for ResultProcessor."""
    processor = ResultProcessor(message_bus, result_aggregator)
    await processor.start()
    yield processor
    await processor.stop()


@pytest.fixture
async def standalone_processor(result_aggregator):
    """Fixture for standalone ResultProcessor (no message bus)."""
    processor = ResultProcessor(None, result_aggregator)
    await processor.start()
    yield processor
    await processor.stop()


class TestProcessingRule:
    """Tests for the ProcessingRule class."""
    
    def test_init(self):
        """Test rule initialization."""
        rule = ProcessingRule(
            name="test-rule",
            description="Test rule",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: True,
            action=lambda result: result,
            priority=10,
            enabled=True
        )
        
        assert rule.name == "test-rule"
        assert rule.description == "Test rule"
        assert rule.stage == ProcessingStage.FILTERED
        assert rule.priority == 10
        assert rule.enabled is True
        assert rule.condition({"test": True}) is True
        assert rule.action({"test": True}) == {"test": True}


class TestProcessingContext:
    """Tests for the ProcessingContext class."""
    
    def test_init(self):
        """Test context initialization."""
        context = ProcessingContext(
            agent_id="test-agent",
            result_id="test-result",
            timestamp=123456789.0
        )
        
        assert context.agent_id == "test-agent"
        assert context.result_id == "test-result"
        assert context.timestamp == 123456789.0
        assert context.metadata == {}
        assert context.processing_history == []


class TestResultProcessor:
    """Tests for the ResultProcessor class."""
    
    def test_init(self, result_aggregator):
        """Test processor initialization."""
        processor = ResultProcessor(None, result_aggregator)
        
        assert processor.result_aggregator == result_aggregator
        assert processor.message_bus is None
        assert processor.processing_strategy == ProcessingStrategy.SEQUENTIAL
        assert all(stage in processor.rules for stage in ProcessingStage)
        
        # Check default rules
        filter_rules = processor.get_rules(ProcessingStage.FILTERED)
        assert any(rule.name == "filter_empty" for rule in filter_rules)
        
        enrich_rules = processor.get_rules(ProcessingStage.ENRICHED)
        assert any(rule.name == "add_timestamp" for rule in enrich_rules)
    
    @pytest.mark.asyncio
    async def test_add_remove_rule(self, standalone_processor):
        """Test adding and removing rules."""
        # Add rule
        rule = ProcessingRule(
            name="test-rule",
            description="Test rule",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: True,
            action=lambda result: {**result, "modified": True},
            priority=10
        )
        standalone_processor.add_rule(rule)
        
        # Check rule was added
        rules = standalone_processor.get_rules(ProcessingStage.FILTERED)
        assert any(r.name == "test-rule" for r in rules)
        
        # Remove rule
        result = standalone_processor.remove_rule("test-rule")
        assert result is True
        
        # Check rule was removed
        rules = standalone_processor.get_rules(ProcessingStage.FILTERED)
        assert not any(r.name == "test-rule" for r in rules)
        
        # Remove non-existent rule
        result = standalone_processor.remove_rule("non-existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_enable_disable_rule(self, standalone_processor):
        """Test enabling and disabling rules."""
        # Add rule
        rule = ProcessingRule(
            name="test-rule",
            description="Test rule",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: True,
            action=lambda result: {**result, "modified": True},
            priority=10,
            enabled=True
        )
        standalone_processor.add_rule(rule)
        
        # Disable rule
        result = standalone_processor.disable_rule("test-rule")
        assert result is True
        
        # Check rule was disabled
        rules = standalone_processor.get_rules(ProcessingStage.FILTERED)
        test_rule = next((r for r in rules if r.name == "test-rule"), None)
        assert test_rule is not None
        assert test_rule.enabled is False
        
        # Enable rule
        result = standalone_processor.enable_rule("test-rule")
        assert result is True
        
        # Check rule was enabled
        rules = standalone_processor.get_rules(ProcessingStage.FILTERED)
        test_rule = next((r for r in rules if r.name == "test-rule"), None)
        assert test_rule is not None
        assert test_rule.enabled is True
        
        # Enable/disable non-existent rule
        result = standalone_processor.enable_rule("non-existent")
        assert result is False
        result = standalone_processor.disable_rule("non-existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_rules(self, standalone_processor):
        """Test getting rules."""
        # Add rules to different stages
        rule1 = ProcessingRule(
            name="test-rule-1",
            description="Test rule 1",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: True,
            action=lambda result: result
        )
        rule2 = ProcessingRule(
            name="test-rule-2",
            description="Test rule 2",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: result
        )
        standalone_processor.add_rule(rule1)
        standalone_processor.add_rule(rule2)
        
        # Get rules by stage
        filtered_rules = standalone_processor.get_rules(ProcessingStage.FILTERED)
        assert any(r.name == "test-rule-1" for r in filtered_rules)
        assert not any(r.name == "test-rule-2" for r in filtered_rules)
        
        enriched_rules = standalone_processor.get_rules(ProcessingStage.ENRICHED)
        assert not any(r.name == "test-rule-1" for r in enriched_rules)
        assert any(r.name == "test-rule-2" for r in enriched_rules)
        
        # Get all rules
        all_rules = standalone_processor.get_rules()
        assert any(r.name == "test-rule-1" for r in all_rules)
        assert any(r.name == "test-rule-2" for r in all_rules)
    
    @pytest.mark.asyncio
    async def test_set_processing_strategy(self, standalone_processor):
        """Test setting processing strategy."""
        # Default strategy
        assert standalone_processor.processing_strategy == ProcessingStrategy.SEQUENTIAL
        
        # Set strategy
        standalone_processor.set_processing_strategy(ProcessingStrategy.PARALLEL)
        assert standalone_processor.processing_strategy == ProcessingStrategy.PARALLEL
        
        standalone_processor.set_processing_strategy(ProcessingStrategy.BATCH)
        assert standalone_processor.processing_strategy == ProcessingStrategy.BATCH
        
        standalone_processor.set_processing_strategy(ProcessingStrategy.SEQUENTIAL)
        assert standalone_processor.processing_strategy == ProcessingStrategy.SEQUENTIAL
    
    @pytest.mark.asyncio
    async def test_process_result_sequential(self, standalone_processor):
        """Test processing a result with sequential strategy."""
        # Set up test rules
        standalone_processor.add_rule(ProcessingRule(
            name="test-filter",
            description="Test filter rule",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: "filter_me" in result,
            action=lambda result: None  # Filter out
        ))
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich",
            description="Test enrich rule",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "enriched": True}
        ))
        standalone_processor.add_rule(ProcessingRule(
            name="test-prioritize",
            description="Test prioritize rule",
            stage=ProcessingStage.PRIORITIZED,
            condition=lambda result: True,
            action=lambda result: {**result, "priority": "high"}
        ))
        
        # Set strategy
        standalone_processor.set_processing_strategy(ProcessingStrategy.SEQUENTIAL)
        
        # Process result that should pass
        context = ProcessingContext(
            agent_id="test-agent",
            result_id="test-result",
            timestamp=time.time()
        )
        result = {"message": "Test result"}
        processed = await standalone_processor.process_result(result, context)
        
        # Check processed result
        assert processed is not None
        assert processed["message"] == "Test result"
        assert processed["enriched"] is True
        assert processed["priority"] == "high"
        assert "timestamp" in processed  # From default rule
        
        # Process result that should be filtered
        result = {"message": "Test result", "filter_me": True}
        processed = await standalone_processor.process_result(result, context)
        
        # Check result was filtered
        assert processed is None
        
        # Check processing history
        assert len(context.processing_history) > 0
        assert all("stage" in entry for entry in context.processing_history)
        assert all("timestamp" in entry for entry in context.processing_history)
    
    @pytest.mark.asyncio
    async def test_process_result_parallel(self, standalone_processor):
        """Test processing a result with parallel strategy."""
        # Set up test rules
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich-1",
            description="Test enrich rule 1",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "enriched1": True}
        ))
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich-2",
            description="Test enrich rule 2",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "enriched2": True}
        ))
        
        # Set strategy
        standalone_processor.set_processing_strategy(ProcessingStrategy.PARALLEL)
        
        # Process result
        context = ProcessingContext(
            agent_id="test-agent",
            result_id="test-result",
            timestamp=time.time()
        )
        result = {"message": "Test result"}
        processed = await standalone_processor.process_result(result, context)
        
        # Check processed result
        # Note: With parallel processing, only one of the enriched fields might be present
        # depending on which rule's result was chosen last
        assert processed is not None
        assert processed["message"] == "Test result"
        assert "enriched1" in processed or "enriched2" in processed
    
    @pytest.mark.asyncio
    async def test_process_result_batch(self, standalone_processor):
        """Test processing a result with batch strategy."""
        # Set up test rules with different priorities
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich-high",
            description="Test enrich rule with high priority",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "high_priority": True},
            priority=10
        ))
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich-low",
            description="Test enrich rule with low priority",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "low_priority": True},
            priority=1
        ))
        
        # Set strategy
        standalone_processor.set_processing_strategy(ProcessingStrategy.BATCH)
        
        # Process result
        context = ProcessingContext(
            agent_id="test-agent",
            result_id="test-result",
            timestamp=time.time()
        )
        result = {"message": "Test result"}
        processed = await standalone_processor.process_result(result, context)
        
        # Check processed result
        assert processed is not None
        assert processed["message"] == "Test result"
        assert "high_priority" in processed
        assert "low_priority" in processed
    
    @pytest.mark.asyncio
    async def test_process_results_batch(self, standalone_processor):
        """Test processing multiple results in batch."""
        # Set up test rules
        standalone_processor.add_rule(ProcessingRule(
            name="test-filter",
            description="Test filter rule",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: "filter_me" in result,
            action=lambda result: None  # Filter out
        ))
        standalone_processor.add_rule(ProcessingRule(
            name="test-enrich",
            description="Test enrich rule",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "enriched": True}
        ))
        
        # Set strategy
        standalone_processor.set_processing_strategy(ProcessingStrategy.SEQUENTIAL)
        
        # Process multiple results
        results = [
            {"id": 1, "message": "Result 1"},
            {"id": 2, "message": "Result 2", "filter_me": True},  # Should be filtered
            {"id": 3, "message": "Result 3"}
        ]
        
        processed = await standalone_processor.process_results(results)
        
        # Check processed results
        assert len(processed) == 2  # One was filtered out
        assert all("enriched" in result for result in processed)
        assert all(result["id"] in [1, 3] for result in processed)
    
    @pytest.mark.asyncio
    async def test_message_handling(self, result_processor, message_bus):
        """Test handling messages from message bus."""
        # Add test rule
        result_processor.add_rule(ProcessingRule(
            name="test-enrich",
            description="Test enrich rule",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "enriched": True}
        ))
        
        # Create test message with result
        message = Message(
            id="test-message",
            type=MessageType.RESPONSE,
            source="test-agent",
            content={
                "result": {
                    "file": "test.py",
                    "line": 10,
                    "message": "Test issue",
                    "priority": "high"
                }
            }
        )
        
        # Publish message
        await message_bus.publish(message)
        
        # Poll for results with timeout
        timeout = 2.0  # 2 second timeout
        start_time = asyncio.get_event_loop().time()
        results = []
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            results = result_processor.result_aggregator.get_results()
            if len(results) > 0:
                break
            await asyncio.sleep(0.05)  # Small polling interval
        
        # Check result was added to aggregator
        assert len(results) == 1, f"Expected 1 result after {timeout}s, got {len(results)}"
        assert results[0].file_path == "test.py"
        assert results[0].line_number == 10
        assert results[0].message == "Test issue"
        assert results[0].source == "test-agent"
        assert results[0].priority == ResultPriority.HIGH
        assert "enriched" in results[0].data
    
    @pytest.mark.asyncio
    async def test_aggregator_integration(self, result_processor):
        """Test integration with result aggregator."""
        # Process a result directly
        result = {
            "file": "test.py",
            "line": 10,
            "message": "Test issue",
            "priority": "medium"
        }
        
        context = ProcessingContext(
            agent_id="test-agent",
            result_id="test-result",
            timestamp=time.time()
        )
        
        processed = await result_processor.process_result(result, context)
        
        # Check result was processed
        assert processed is not None
        
        # Check aggregator methods
        assert result_processor.get_aggregator() == result_processor.result_aggregator
        
        # Generate summary
        summary = result_processor.generate_summary()
        assert "total" in summary
        assert summary["total"] == 1
        
        # Export results
        exported = result_processor.export_results()
        assert "test.py" in exported
        assert "Test issue" in exported
        
        # Clear results
        result_processor.clear_results()
        assert len(result_processor.result_aggregator.get_results()) == 0