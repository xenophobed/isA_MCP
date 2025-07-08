#!/usr/bin/env python
"""
Comprehensive Memory Resources for MCP Server
Provides access to all memory types: factual, procedural, episodic, semantic, working, and session memories
"""
import json
from datetime import datetime
from typing import Dict, Any, List

from resources.base_resource import BaseResource, SecurityLevel, create_simple_resource_registration
from core.logging import get_logger

logger = get_logger(__name__)

@create_simple_resource_registration("register_memory_resources")
class MemoryResources(BaseResource):
    """Memory resources with all memory types"""
    
    def register_all_resources(self, mcp):
        """Register all memory resources"""
        
        # ========== SESSION MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://session/{session_id}", 
            self.get_session_memory, SecurityLevel.LOW
        )
        
        self.register_resource(
            mcp, "memory://sessions/{user_id}", 
            self.get_user_sessions, SecurityLevel.LOW
        )
        
        # ========== FACTUAL MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://factual/{user_id}", 
            self.get_factual_memories, SecurityLevel.LOW
        )
        
        self.register_resource(
            mcp, "memory://factual/{user_id}/{fact_type}", 
            self.get_factual_by_type, SecurityLevel.LOW
        )
        
        # ========== PROCEDURAL MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://procedural/{user_id}", 
            self.get_procedural_memories, SecurityLevel.LOW
        )
        
        # ========== EPISODIC MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://episodic/{user_id}", 
            self.get_episodic_memories, SecurityLevel.LOW
        )
        
        # ========== SEMANTIC MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://semantic/{user_id}", 
            self.get_semantic_memories, SecurityLevel.LOW
        )
        
        # ========== WORKING MEMORY RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://working/{user_id}", 
            self.get_working_memories, SecurityLevel.LOW
        )
        
        # ========== MEMORY STATISTICS RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://statistics/{user_id}", 
            self.get_memory_statistics, SecurityLevel.LOW
        )
        
        # ========== MEMORY SEARCH RESOURCES ==========
        
        self.register_resource(
            mcp, "memory://search/{user_id}", 
            self.get_search_guidance, SecurityLevel.LOW
        )
    
    # ========== SESSION MEMORY METHODS ==========
    
    async def get_session_memory(self, session_id: str) -> str:
        """Get complete session memory including summary, context, and tasks"""
        result = self.supabase.table('session_memories')\
            .select('*')\
            .eq('session_id', session_id)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://session/{session_id}", "session memory"
            )
        
        memory = result.data[0]
        
        return f"""# Session Memory: {session_id}

## Summary
{memory.get('conversation_summary', 'No summary available')}

## User Context
- **Current Project**: {memory.get('user_context', {}).get('current_project', 'Not specified')}
- **Technical Stack**: {', '.join(memory.get('user_context', {}).get('technical_stack', []))}
- **Working Directory**: {memory.get('user_context', {}).get('working_directory', 'Not specified')}
- **Goals**: {', '.join(memory.get('user_context', {}).get('main_goals', []))}

## Key Decisions ({len(memory.get('key_decisions', []))})
{chr(10).join([f"- **{d.get('decision', '')}**: {d.get('reasoning', '')}" for d in memory.get('key_decisions', [])])}

## Tasks ({len(memory.get('ongoing_tasks', []))})
{chr(10).join([f"- [{t.get('status', 'pending').upper()}] {t.get('task', '')} (Priority: {t.get('priority', 'medium')})" for t in memory.get('ongoing_tasks', [])])}

## Preferences
- **Coding Style**: {memory.get('user_preferences', {}).get('coding_style', 'Not specified')}
- **Tools**: {', '.join(memory.get('user_preferences', {}).get('preferred_tools', []))}

## Important Facts ({len(memory.get('important_facts', []))})
{chr(10).join([f"- {f.get('fact', '')} ({f.get('category', 'general')})" for f in memory.get('important_facts', [])])}

---
*Last Updated: {memory.get('updated_at', 'Unknown')} | Messages: {memory.get('total_messages', 0)}*
"""
    
    async def get_user_sessions(self, user_id: str) -> str:
        """Get all session memories for a user"""
        result = self.supabase.table('session_memories')\
            .select('session_id,conversation_summary,created_at,updated_at,total_messages,is_active')\
            .eq('user_id', user_id)\
            .order('updated_at', desc=True)\
            .limit(20)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://sessions/{user_id}", "sessions for this user"
            )
        
        output = f"""# User Sessions: {user_id}

Found {len(result.data)} session(s):

"""
        
        for session in result.data:
            status = "🟢 ACTIVE" if session.get('is_active') else "⚪ INACTIVE"
            summary = session.get('conversation_summary', 'No summary')
            if len(summary) > 100:
                summary = summary[:100] + "..."
            
            output += f"""## {session['session_id']} {status}
- **Summary**: {summary}
- **Created**: {session.get('created_at', 'Unknown')}
- **Messages**: {session.get('total_messages', 0)}

"""
        
        return output
    
    # ========== FACTUAL MEMORY METHODS ==========
    
    async def get_factual_memories(self, user_id: str) -> str:
        """Get factual memories for a user"""
        result = self.supabase.table('factual_memories')\
            .select('fact_type,subject,predicate,object_value,confidence,importance_score,created_at')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .order('importance_score', desc=True)\
            .limit(50)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://factual/{user_id}", "factual memories"
            )
        
        # Group by fact_type
        by_type = {}
        for fact in result.data:
            fact_type = fact['fact_type']
            if fact_type not in by_type:
                by_type[fact_type] = []
            by_type[fact_type].append(fact)
        
        output = f"""# Factual Memories: {user_id}

Found {len(result.data)} factual memories across {len(by_type)} categories:

"""
        
        for fact_type, facts in by_type.items():
            output += f"""## {fact_type.replace('_', ' ').title()} ({len(facts)})
{chr(10).join([f"- **{f['subject']}** {f['predicate']} {f['object_value']} (Confidence: {f['confidence']:.2f})" for f in facts[:10]])}

"""
            if len(facts) > 10:
                output += f"... and {len(facts) - 10} more\n\n"
        
        return output
    
    async def get_factual_by_type(self, user_id: str, fact_type: str) -> str:
        """Get factual memories of a specific type"""
        result = self.supabase.table('factual_memories')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('fact_type', fact_type)\
            .eq('is_active', True)\
            .order('importance_score', desc=True)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://factual/{user_id}/{fact_type}", f"{fact_type} memories"
            )
        
        output = f"""# {fact_type.replace('_', ' ').title()} Memories: {user_id}

Found {len(result.data)} {fact_type} memories:

"""
        
        for fact in result.data:
            output += f"""## {fact['subject']}
- **{fact['predicate']}**: {fact['object_value']}
- **Context**: {fact.get('context', 'N/A')}
- **Confidence**: {fact['confidence']:.2f}
- **Importance**: {fact['importance_score']:.2f}
- **Last Confirmed**: {fact.get('last_confirmed_at', 'Never')}

"""
        
        return output
    
    # ========== PROCEDURAL MEMORY METHODS ==========
    
    async def get_procedural_memories(self, user_id: str) -> str:
        """Get procedural memories for a user"""
        result = self.supabase.table('procedural_memories')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('usage_count', desc=True)\
            .limit(20)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://procedural/{user_id}", "procedural memories"
            )
        
        output = f"""# Procedural Memories: {user_id}

Found {len(result.data)} procedures:

"""
        
        for proc in result.data:
            steps = proc.get('steps', [])
            output += f"""## {proc['procedure_name']} ({proc['domain']})
- **Success Rate**: {proc.get('success_rate', 0):.1%}
- **Used**: {proc.get('usage_count', 0)} times
- **Difficulty**: {proc.get('difficulty_level', 'N/A')}/5
- **Estimated Time**: {proc.get('estimated_time_minutes', 'N/A')} minutes
- **Steps**: {len(steps)} steps
- **Expected Outcome**: {proc.get('expected_outcome', 'Not specified')}

### Procedure Steps:
{chr(10).join([f"{i+1}. {step.get('action', step) if isinstance(step, dict) else step}" for i, step in enumerate(steps[:5])])}
{f"... and {len(steps) - 5} more steps" if len(steps) > 5 else ""}

---
"""
        
        return output
    
    # ========== EPISODIC MEMORY METHODS ==========
    
    async def get_episodic_memories(self, user_id: str) -> str:
        """Get episodic memories for a user"""
        result = self.supabase.table('episodic_memories')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('occurred_at', desc=True)\
            .limit(20)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://episodic/{user_id}", "episodic memories"
            )
        
        output = f"""# Episodic Memories: {user_id}

Found {len(result.data)} episodes:

"""
        
        for episode in result.data:
            participants = episode.get('participants', [])
            key_events = episode.get('key_events', [])
            
            output += f"""## {episode['episode_title']}
- **When**: {episode.get('occurred_at', 'Unknown')}
- **Location**: {episode.get('location', 'Not specified')}
- **Participants**: {', '.join(participants) if participants else 'None specified'}
- **Emotional Context**: {episode.get('emotional_context', 'Neutral')}
- **Intensity**: {episode.get('emotional_intensity', 0.5):.1f}/1.0

### Summary
{episode.get('summary', 'No summary available')}

### Key Events
{chr(10).join([f"- {event.get('event', event) if isinstance(event, dict) else event}" for event in key_events[:3]])}
{f"... and {len(key_events) - 3} more events" if len(key_events) > 3 else ""}

### Lessons Learned
{episode.get('lessons_learned', 'None recorded')}

---
"""
        
        return output
    
    # ========== SEMANTIC MEMORY METHODS ==========
    
    async def get_semantic_memories(self, user_id: str) -> str:
        """Get semantic memories for a user"""
        result = self.supabase.table('semantic_memories')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('mastery_level', desc=True)\
            .limit(30)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://semantic/{user_id}", "semantic memories"
            )
        
        # Group by category
        by_category = {}
        for concept in result.data:
            category = concept['concept_category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(concept)
        
        output = f"""# Semantic Memories: {user_id}

Found {len(result.data)} concepts across {len(by_category)} categories:

"""
        
        for category, concepts in by_category.items():
            output += f"""## {category.title()} ({len(concepts)})
{chr(10).join([f"- **{c['concept_name']}** (Mastery: {c.get('mastery_level', 0.5):.1%}): {c['definition'][:100]}{'...' if len(c['definition']) > 100 else ''}" for c in concepts[:5]])}

"""
            if len(concepts) > 5:
                output += f"... and {len(concepts) - 5} more concepts\n\n"
        
        return output
    
    # ========== WORKING MEMORY METHODS ==========
    
    async def get_working_memories(self, user_id: str) -> str:
        """Get active working memories for a user"""
        result = self.supabase.table('working_memories')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .order('priority', desc=True)\
            .execute()
        
        if not result.data:
            return self.create_not_found_response(
                f"memory://working/{user_id}", "active working memories"
            )
        
        output = f"""# Working Memories: {user_id}

Found {len(result.data)} active working memories:

"""
        
        for work in result.data:
            next_actions = work.get('next_actions', [])
            progress = work.get('progress_percentage', 0)
            
            output += f"""## {work['context_type']}: {work['context_id']}
- **Current Step**: {work.get('current_step', 'Not specified')}
- **Progress**: {progress:.1%}
- **Priority**: {work.get('priority', 3)}/5
- **Expires**: {work.get('expires_at', 'No expiration')}

### State Data
```json
{json.dumps(work.get('state_data', {}), indent=2)[:200]}{'...' if len(str(work.get('state_data', {}))) > 200 else ''}
```

### Next Actions
{chr(10).join([f"- {action}" for action in next_actions[:3]])}
{f"... and {len(next_actions) - 3} more actions" if len(next_actions) > 3 else ""}

---
"""
        
        return output
    
    # ========== MEMORY STATISTICS METHODS ==========
    
    async def get_memory_statistics(self, user_id: str) -> str:
        """Get comprehensive memory statistics for a user"""
        # Get counts for each memory type
        memory_counts = {}
        tables = ['factual_memories', 'procedural_memories', 'episodic_memories', 'semantic_memories', 'working_memories', 'session_memories']
        
        for table in tables:
            result = self.supabase.table(table)\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .execute()
            memory_counts[table] = result.count or 0
        
        # Get memory metadata stats
        metadata_result = self.supabase.table('memory_metadata')\
            .select('access_count,accuracy_score,relevance_score,completeness_score')\
            .eq('user_id', user_id)\
            .execute()
        
        total_accesses = sum(item.get('access_count', 0) for item in metadata_result.data) if metadata_result.data else 0
        
        # Get recent activity
        recent_result = self.supabase.table('memory_extraction_logs')\
            .select('created_at', count='exact')\
            .eq('user_id', user_id)\
            .gte('created_at', (datetime.now().replace(day=1)).isoformat())\
            .execute()
        
        recent_extractions = recent_result.count or 0
        
        output = f"""# Memory Statistics: {user_id}

## Memory Counts
- **Factual Memories**: {memory_counts['factual_memories']}
- **Procedural Memories**: {memory_counts['procedural_memories']}
- **Episodic Memories**: {memory_counts['episodic_memories']}
- **Semantic Memories**: {memory_counts['semantic_memories']}
- **Working Memories**: {memory_counts['working_memories']}
- **Session Memories**: {memory_counts['session_memories']}

**Total Memories**: {sum(memory_counts.values())}

## Activity Stats
- **Total Memory Accesses**: {total_accesses}
- **Memory Extractions This Month**: {recent_extractions}

## Quality Metrics
"""
        
        if metadata_result.data:
            scores = [item for item in metadata_result.data if item.get('accuracy_score') is not None]
            if scores:
                avg_accuracy = sum(item['accuracy_score'] for item in scores) / len(scores)
                avg_relevance = sum(item.get('relevance_score', 0) for item in scores) / len(scores)
                avg_completeness = sum(item.get('completeness_score', 0) for item in scores) / len(scores)
                
                output += f"""- **Average Accuracy**: {avg_accuracy:.1%}
- **Average Relevance**: {avg_relevance:.1%}
- **Average Completeness**: {avg_completeness:.1%}
"""
            else:
                output += "- No quality metrics available yet\n"
        else:
            output += "- No quality metrics available yet\n"
        
        output += f"""
---
*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return output
    
    # ========== MEMORY SEARCH METHODS ==========
    
    async def get_search_guidance(self, user_id: str) -> str:
        """Provide guidance on how to search memories"""
        return f"""# Memory Search Guide: {user_id}

To search memories, use the memory search tools with these patterns:

## Available Memory Types
- **factual**: Facts about the user (preferences, skills, experiences)
- **procedural**: Step-by-step procedures and workflows
- **episodic**: Specific events and experiences
- **semantic**: Concepts, definitions, and knowledge
- **working**: Current tasks and active work contexts
- **session**: Conversation summaries and session context

## Search Examples
- Search for technical skills: "Python programming experience"
- Find procedures: "deployment workflow" or "code review process"
- Recall experiences: "last project meeting" or "debugging session"
- Look up concepts: "REST API" or "machine learning"
- Check current work: "active tasks" or "current project"

## Available Resources
- `memory://factual/{user_id}` - All factual memories
- `memory://factual/{user_id}/skill` - Just skill-related facts
- `memory://procedural/{user_id}` - All procedures
- `memory://episodic/{user_id}` - All experiences
- `memory://semantic/{user_id}` - All concepts
- `memory://working/{user_id}` - Active work contexts
- `memory://session/{{"session_id"}}` - Specific session memory
- `memory://sessions/{user_id}` - All user sessions
- `memory://statistics/{user_id}` - Memory usage statistics

Use the search_memories tool for semantic similarity search across all memory types.
"""