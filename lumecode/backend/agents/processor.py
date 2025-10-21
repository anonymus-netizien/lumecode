import logging
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Set
from dataclasses import dataclass, field
import json
import time

from ..analysis import ResultAggregator, ResultType, ResultPriority
from .communication import Message, MessageType, MessagePriority, MessageBus

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Stages of result processing."""
    RAW = "raw"                   # Raw results from agents
    FILTERED = "filtered"         # Results after filtering
    ENRICHED = "enriched"         # Results after enrichment
    PRIORITIZED = "prioritized"   # Results after prioritization
    GROUPED = "grouped"           # Results after grouping
    FINAL = "final"               # Final processed results


class ProcessingStrategy(Enum):
    """Strategies for processing results."""
    SEQUENTIAL = "sequential"     # Process results sequentially
    PARALLEL = "parallel"         # Process results in parallel
    BATCH = "batch"               # Process results in batches


@dataclass
class ProcessingRule:
    """Rule for processing results."""
    name: str                                      # Rule name
    description: str                               # Rule description
    stage: ProcessingStage                         # Processing stage
    condition: Callable[[Dict[str, Any]], bool]    # Condition to apply rule
    action: Callable[[Dict[str, Any]], Dict[str, Any]]  # Action to take
    priority: int = 0                              # Rule priority (higher runs first)
    enabled: bool = True                           # Whether rule is enabled


@dataclass
class ProcessingContext:
    """Context for result processing."""
    agent_id: str                                  # ID of agent that produced the result
    result_id: str                                 # ID of the result
    timestamp: float                               # Timestamp of processing
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    processing_history: List[Dict[str, Any]] = field(default_factory=list)  # Processing history


class ResultProcessor:
    """Processes results from agents.
    
    Applies processing rules to agent results to filter, enrich, prioritize, and group them.
    """
    
    def __init__(self, message_bus: Optional[MessageBus] = None, 
                result_aggregator: Optional[ResultAggregator] = None):
        """Initialize the result processor.
        
        Args:
            message_bus: Message bus for communication
            result_aggregator: Result aggregator for storing processed results
        """
        self.message_bus = message_bus
        self.result_aggregator = result_aggregator or ResultAggregator()
        self.rules: Dict[ProcessingStage, List[ProcessingRule]] = {
            stage: [] for stage in ProcessingStage
        }
        self.processing_strategy = ProcessingStrategy.SEQUENTIAL
        self.processing_lock = asyncio.Lock()
        self._running = False
        self._worker_task = None
        self._queue = asyncio.Queue()
        
        # Register default rules
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default processing rules."""
        # Filter out empty results
        self.add_rule(ProcessingRule(
            name="filter_empty",
            description="Filter out empty results",
            stage=ProcessingStage.FILTERED,
            condition=lambda result: not result or not result.get("data"),
            action=lambda result: None  # Return None to filter out
        ))
        
        # Add timestamp to results
        self.add_rule(ProcessingRule(
            name="add_timestamp",
            description="Add timestamp to results",
            stage=ProcessingStage.ENRICHED,
            condition=lambda result: True,
            action=lambda result: {**result, "timestamp": time.time()}
        ))
    
    def add_rule(self, rule: ProcessingRule):
        """Add a processing rule.
        
        Args:
            rule: Processing rule to add
        """
        self.rules[rule.stage].append(rule)
        # Sort rules by priority (higher first)
        self.rules[rule.stage].sort(key=lambda r: -r.priority)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a processing rule.
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            True if rule was removed, False otherwise
        """
        for stage, rules in self.rules.items():
            for i, rule in enumerate(rules):
                if rule.name == rule_name:
                    self.rules[stage].pop(i)
                    return True
        return False
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a processing rule.
        
        Args:
            rule_name: Name of rule to enable
            
        Returns:
            True if rule was enabled, False otherwise
        """
        for stage, rules in self.rules.items():
            for rule in rules:
                if rule.name == rule_name:
                    rule.enabled = True
                    return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a processing rule.
        
        Args:
            rule_name: Name of rule to disable
            
        Returns:
            True if rule was disabled, False otherwise
        """
        for stage, rules in self.rules.items():
            for rule in rules:
                if rule.name == rule_name:
                    rule.enabled = False
                    return True
        return False
    
    def get_rules(self, stage: Optional[ProcessingStage] = None) -> List[ProcessingRule]:
        """Get processing rules.
        
        Args:
            stage: Processing stage to get rules for (None for all)
            
        Returns:
            List of processing rules
        """
        if stage is None:
            # Flatten all rules
            return [rule for rules in self.rules.values() for rule in rules]
        return self.rules.get(stage, [])
    
    def set_processing_strategy(self, strategy: ProcessingStrategy):
        """Set the processing strategy.
        
        Args:
            strategy: Processing strategy to use
        """
        self.processing_strategy = strategy
    
    async def start(self):
        """Start the result processor."""
        if self._running:
            return
            
        self._running = True
        
        # Start worker task if using message bus
        if self.message_bus:
            self._worker_task = asyncio.create_task(self._process_queue())
            self.message_bus.subscribe("*", self._handle_message)
            logger.info("Result processor started with message bus integration")
        else:
            logger.info("Result processor started in standalone mode")
    
    async def stop(self):
        """Stop the result processor."""
        if not self._running:
            return
            
        self._running = False
        
        # Stop worker task if using message bus
        if self.message_bus:
            self.message_bus.unsubscribe("*", self._handle_message)
            
            if self._worker_task:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Result processor stopped")
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages.
        
        Args:
            message: Incoming message
        """
        # Only process result messages
        if message.type != MessageType.RESPONSE:
            return
            
        # Check if message contains results
        if "result" not in message.content:
            return
            
        # Queue result for processing
        context = ProcessingContext(
            agent_id=message.source,
            result_id=message.id,
            timestamp=message.timestamp
        )
        await self._queue.put((message.content["result"], context))
    
    async def _process_queue(self):
        """Process results from the queue."""
        while self._running:
            try:
                result, context = await self._queue.get()
                
                try:
                    processed_result = await self.process_result(result, context)
                    if processed_result:
                        # Store processed result
                        self.result_aggregator.add_result(
                            result_type=ResultType.AGENT,
                            file_path=processed_result.get("file"),
                            line_number=processed_result.get("line"),
                            message=processed_result.get("message"),
                            source=context.agent_id,
                            priority=ResultPriority.from_str(processed_result.get("priority", "medium")),
                            data=processed_result
                        )
                except Exception as e:
                    logger.error(f"Error processing result: {e}")
                
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in result processor worker: {e}")
    
    async def process_result(self, result: Dict[str, Any], 
                           context: Optional[ProcessingContext] = None) -> Optional[Dict[str, Any]]:
        """Process a result.
        
        Args:
            result: Result to process
            context: Processing context
            
        Returns:
            Processed result, or None if result was filtered out
        """
        if context is None:
            context = ProcessingContext(
                agent_id="unknown",
                result_id=str(time.time()),
                timestamp=time.time()
            )
        
        # Make a copy of the result to avoid modifying the original
        processed = result.copy() if result else {}
        
        # Process through each stage
        for stage in ProcessingStage:
            processed = await self._apply_stage(stage, processed, context)
            if processed is None:
                # Result was filtered out
                return None
            
            # Record processing history
            context.processing_history.append({
                "stage": stage.value,
                "timestamp": time.time()
            })
        
        return processed
    
    async def _apply_stage(self, stage: ProcessingStage, result: Dict[str, Any],
                         context: ProcessingContext) -> Optional[Dict[str, Any]]:
        """Apply a processing stage to a result.
        
        Args:
            stage: Processing stage to apply
            result: Result to process
            context: Processing context
            
        Returns:
            Processed result, or None if result was filtered out
        """
        if result is None:
            return None
            
        # Get rules for this stage
        rules = [r for r in self.rules[stage] if r.enabled]
        
        # Apply rules based on strategy
        if self.processing_strategy == ProcessingStrategy.PARALLEL:
            return await self._apply_rules_parallel(rules, result, context)
        elif self.processing_strategy == ProcessingStrategy.BATCH:
            return await self._apply_rules_batch(rules, result, context)
        else:  # SEQUENTIAL
            return await self._apply_rules_sequential(rules, result, context)
    
    async def _apply_rules_sequential(self, rules: List[ProcessingRule], 
                                    result: Dict[str, Any],
                                    context: ProcessingContext) -> Optional[Dict[str, Any]]:
        """Apply rules sequentially.
        
        Args:
            rules: Rules to apply
            result: Result to process
            context: Processing context
            
        Returns:
            Processed result, or None if result was filtered out
        """
        processed = result
        
        for rule in rules:
            try:
                # Check if rule applies
                if rule.condition(processed):
                    # Apply rule
                    processed = rule.action(processed)
                    if processed is None:
                        # Result was filtered out
                        return None
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {e}")
        
        return processed
    
    async def _apply_rules_parallel(self, rules: List[ProcessingRule],
                                  result: Dict[str, Any],
                                  context: ProcessingContext) -> Optional[Dict[str, Any]]:
        """Apply rules in parallel.
        
        Args:
            rules: Rules to apply
            result: Result to process
            context: Processing context
            
        Returns:
            Processed result, or None if result was filtered out
        """
        # Filter rules that apply
        applicable_rules = [rule for rule in rules if rule.condition(result)]
        
        if not applicable_rules:
            return result
            
        # Apply rules in parallel
        async def apply_rule(rule):
            try:
                return rule.action(result.copy())
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {e}")
                return result.copy()
        
        results = await asyncio.gather(*[apply_rule(rule) for rule in applicable_rules])
        
        # Merge results (last non-None result wins)
        processed = result
        for r in results:
            if r is not None:
                processed = r
        
        return processed
    
    async def _apply_rules_batch(self, rules: List[ProcessingRule],
                               result: Dict[str, Any],
                               context: ProcessingContext) -> Optional[Dict[str, Any]]:
        """Apply rules in batches.
        
        Args:
            rules: Rules to apply
            result: Result to process
            context: Processing context
            
        Returns:
            Processed result, or None if result was filtered out
        """
        # Group rules by priority
        priority_groups: Dict[int, List[ProcessingRule]] = {}
        for rule in rules:
            if rule.priority not in priority_groups:
                priority_groups[rule.priority] = []
            priority_groups[rule.priority].append(rule)
        
        # Sort priorities (higher first)
        priorities = sorted(priority_groups.keys(), reverse=True)
        
        # Apply rules by priority group
        processed = result
        for priority in priorities:
            # Apply rules in this priority group in parallel
            group_rules = priority_groups[priority]
            processed = await self._apply_rules_parallel(group_rules, processed, context)
            if processed is None:
                # Result was filtered out
                return None
        
        return processed
    
    async def process_results(self, results: List[Dict[str, Any]],
                            context_factory: Optional[Callable[[Dict[str, Any]], ProcessingContext]] = None) -> List[Dict[str, Any]]:
        """Process multiple results.
        
        Args:
            results: Results to process
            context_factory: Factory function to create processing contexts
            
        Returns:
            List of processed results (filtered results are excluded)
        """
        processed_results = []
        
        # Process based on strategy
        if self.processing_strategy == ProcessingStrategy.PARALLEL:
            # Process all results in parallel
            async def process_one(result):
                ctx = context_factory(result) if context_factory else ProcessingContext(
                    agent_id="batch",
                    result_id=str(time.time()),
                    timestamp=time.time()
                )
                return await self.process_result(result, ctx)
            
            processed = await asyncio.gather(*[process_one(result) for result in results])
            processed_results = [r for r in processed if r is not None]
        elif self.processing_strategy == ProcessingStrategy.BATCH:
            # Process in batches by stage
            current_batch = results
            
            for stage in ProcessingStage:
                # Process this stage for all results
                next_batch = []
                
                for result in current_batch:
                    ctx = context_factory(result) if context_factory else ProcessingContext(
                        agent_id="batch",
                        result_id=str(time.time()),
                        timestamp=time.time()
                    )
                    
                    processed = await self._apply_stage(stage, result, ctx)
                    if processed is not None:
                        next_batch.append(processed)
                        
                        # Record processing history
                        ctx.processing_history.append({
                            "stage": stage.value,
                            "timestamp": time.time()
                        })
                
                current_batch = next_batch
            
            processed_results = current_batch
        else:  # SEQUENTIAL
            # Process each result sequentially
            for result in results:
                ctx = context_factory(result) if context_factory else ProcessingContext(
                    agent_id="batch",
                    result_id=str(time.time()),
                    timestamp=time.time()
                )
                
                processed = await self.process_result(result, ctx)
                if processed is not None:
                    processed_results.append(processed)
        
        return processed_results
    
    def get_aggregator(self) -> ResultAggregator:
        """Get the result aggregator.
        
        Returns:
            Result aggregator
        """
        return self.result_aggregator
    
    def clear_results(self):
        """Clear all processed results."""
        self.result_aggregator.clear_results()
    
    def export_results(self, format_type: str = "json") -> str:
        """Export processed results.
        
        Args:
            format_type: Format type (json, csv, etc.)
            
        Returns:
            Exported results as string
        """
        return self.result_aggregator.export_results(format_type)
    
    def generate_summary(self, group_by: Optional[str] = None) -> Dict[str, Any]:
        """Generate a summary of processed results.
        
        Args:
            group_by: Field to group results by
            
        Returns:
            Summary of results
        """
        return self.result_aggregator.generate_summary(group_by)