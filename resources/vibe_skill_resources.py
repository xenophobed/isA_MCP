#!/usr/bin/env python3
"""
Vibe Skill Resources - MCP Resource Registration for AI-SDLC Skills

Provides MCP resources for accessing isA_Vibe skills (CDD, TDD, Deployment, Operations).
Skills are markdown files that provide instructions for Claude agents.

Supports Level 3 resources (progressive disclosure):
- Level 1: Metadata (always loaded) - name, description from frontmatter
- Level 2: Instructions (when triggered) - SKILL.md content
- Level 3: Resources (as needed) - guides, templates, scripts

Usage:
    # In MCP client
    resources/list  -> lists vibe://skill/cdd, vibe://skill/tdd, etc.
    resources/read("vibe://skill/cdd")  -> returns SKILL.md content

Resource URIs:
    vibe://skill/list                           - List all available skills
    vibe://skill/{skill_name}                   - Get specific skill content (Level 2)
    vibe://skill/{skill_name}/guides            - List available guides (Level 3)
    vibe://skill/{skill_name}/guides/{path}     - Get specific guide content
    vibe://skill/{skill_name}/templates         - List available templates (Level 3)
    vibe://skill/{skill_name}/templates/{path}  - Get specific template content
    vibe://skill/search/{query}                 - Search skills by keyword
"""

import json
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Skills directory relative to this file
# Skills are in resources/skills/vibe/ (not resources/vibe_skills/)
VIBE_SKILLS_DIR = Path(__file__).parent / "skills" / "vibe"


class VibeSkillManager:
    """Manager for Vibe skills as MCP resources with Level 3 support"""

    def __init__(self, skills_dir: Path = VIBE_SKILLS_DIR):
        self.skills_dir = skills_dir
        self._skill_cache: Dict[str, Dict[str, Any]] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Load all skills from the skills directory"""
        if not self.skills_dir.exists():
            logger.debug(f"Skills directory not found: {self.skills_dir}")
            return

        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    self._load_skill(skill_dir.name, skill_file, skill_dir)

    def _load_skill(self, skill_name: str, skill_file: Path, skill_dir: Path) -> None:
        """Load a single skill from file with Level 3 resource discovery"""
        try:
            content = skill_file.read_text(encoding="utf-8")

            # Parse frontmatter (YAML between --- markers)
            metadata = self._parse_frontmatter(content)

            # Discover Level 3 resources (guides, templates, scripts)
            guides_dir = skill_dir / "guides"
            templates_dir = skill_dir / "templates"
            scripts_dir = skill_dir / "scripts"

            has_level3 = guides_dir.exists() or templates_dir.exists() or scripts_dir.exists()

            self._skill_cache[skill_name] = {
                "name": skill_name,
                "description": metadata.get("description", ""),
                "content": content,
                "path": str(skill_file),
                "skill_dir": str(skill_dir),
                "has_level3": has_level3,
                "guides_dir": str(guides_dir) if guides_dir.exists() else None,
                "templates_dir": str(templates_dir) if templates_dir.exists() else None,
                "scripts_dir": str(scripts_dir) if scripts_dir.exists() else None,
                "loaded_at": datetime.now().isoformat()
            }
            logger.info(f"  Loaded skill: {skill_name} (Level 3: {has_level3})")

        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")

    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML frontmatter from markdown content"""
        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
        return metadata

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills"""
        return [
            {
                "name": name,
                "description": data.get("description", ""),
                "uri": f"vibe://skill/{name}"
            }
            for name, data in self._skill_cache.items()
        ]

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific skill by name (case-insensitive)"""
        # Try exact match first
        if skill_name in self._skill_cache:
            return self._skill_cache[skill_name]
        # Try case-insensitive match
        skill_lower = skill_name.lower()
        for name, data in self._skill_cache.items():
            if name.lower() == skill_lower:
                return data
        return None

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Search skills by keyword"""
        query_lower = query.lower()
        results = []

        for name, data in self._skill_cache.items():
            # Search in name, description, and content
            if (query_lower in name.lower() or
                query_lower in data.get("description", "").lower() or
                query_lower in data.get("content", "").lower()):
                results.append({
                    "name": name,
                    "description": data.get("description", ""),
                    "uri": f"vibe://skill/{name}",
                    "match_score": self._calculate_match_score(query_lower, name, data)
                })

        # Sort by match score
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def _calculate_match_score(self, query: str, name: str, data: Dict) -> float:
        """Calculate relevance score for search results"""
        score = 0.0

        # Exact name match
        if query == name.lower():
            score += 1.0
        # Name contains query
        elif query in name.lower():
            score += 0.7

        # Description match
        if query in data.get("description", "").lower():
            score += 0.5

        # Content match (lower weight)
        if query in data.get("content", "").lower():
            score += 0.2

        return score

    def reload_skills(self) -> int:
        """Reload all skills from disk"""
        self._skill_cache.clear()
        self._load_skills()
        return len(self._skill_cache)

    def list_guides(self, skill_name: str) -> List[Dict[str, str]]:
        """List available guides for a skill (Level 3)"""
        skill = self._skill_cache.get(skill_name)
        if not skill or not skill.get("guides_dir"):
            return []

        guides_dir = Path(skill["guides_dir"])
        guides = []

        for guide_file in guides_dir.rglob("*.md"):
            rel_path = guide_file.relative_to(guides_dir)
            guides.append({
                "name": guide_file.stem,
                "path": str(rel_path),
                "uri": f"vibe://skill/{skill_name}/guides/{rel_path}"
            })

        return sorted(guides, key=lambda x: x["path"])

    def get_guide(self, skill_name: str, guide_path: str) -> Optional[str]:
        """Get a specific guide content (Level 3)"""
        skill = self._skill_cache.get(skill_name)
        if not skill or not skill.get("guides_dir"):
            return None

        guide_file = Path(skill["guides_dir"]) / guide_path
        if guide_file.exists() and guide_file.suffix == ".md":
            return guide_file.read_text(encoding="utf-8")
        return None

    def list_templates(self, skill_name: str) -> List[Dict[str, str]]:
        """List available templates for a skill (Level 3)"""
        skill = self._skill_cache.get(skill_name)
        if not skill or not skill.get("templates_dir"):
            return []

        templates_dir = Path(skill["templates_dir"])
        templates = []

        # Include all file types in templates
        for template_file in templates_dir.rglob("*"):
            if template_file.is_file():
                rel_path = template_file.relative_to(templates_dir)
                templates.append({
                    "name": template_file.name,
                    "path": str(rel_path),
                    "uri": f"vibe://skill/{skill_name}/templates/{rel_path}"
                })

        return sorted(templates, key=lambda x: x["path"])

    def get_template(self, skill_name: str, template_path: str) -> Optional[str]:
        """Get a specific template content (Level 3)"""
        skill = self._skill_cache.get(skill_name)
        if not skill or not skill.get("templates_dir"):
            return None

        template_file = Path(skill["templates_dir"]) / template_path
        if template_file.exists() and template_file.is_file():
            return template_file.read_text(encoding="utf-8")
        return None

    def list_scripts(self, skill_name: str) -> List[Dict[str, str]]:
        """List available scripts for a skill (Level 3)"""
        skill = self._skill_cache.get(skill_name)
        if not skill or not skill.get("scripts_dir"):
            return []

        scripts_dir = Path(skill["scripts_dir"])
        scripts = []

        for script_file in scripts_dir.rglob("*"):
            if script_file.is_file():
                rel_path = script_file.relative_to(scripts_dir)
                scripts.append({
                    "name": script_file.name,
                    "path": str(rel_path),
                    "uri": f"vibe://skill/{skill_name}/scripts/{rel_path}"
                })

        return sorted(scripts, key=lambda x: x["path"])


# Global skill manager instance
_skill_manager: Optional[VibeSkillManager] = None


def get_skill_manager() -> VibeSkillManager:
    """Get or create the global skill manager"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = VibeSkillManager()
    return _skill_manager


def register_vibe_skill_resources(mcp: FastMCP):
    """Register Vibe skill resources with MCP server"""

    logger.debug("Registering Vibe skill resources...")
    skill_manager = get_skill_manager()

    @mcp.resource("vibe://skill/list")
    def list_all_skills() -> str:
        """
        List all available Vibe skills for AI-SDLC workflows.

        Returns catalog of consolidated skills (cdd, tdd, deployment, init, operations, agile).
        Each skill may have Level 3 resources (guides, templates, scripts).

        Keywords: skills, list, catalog, cdd, tdd, deployment, operations, init, agile
        """
        skills = skill_manager.list_skills()

        # Categorize by consolidated bundle names
        consolidated = ["cdd", "tdd", "deployment", "init", "operations", "agile"]

        return json.dumps({
            "total_skills": len(skills),
            "skills": skills,
            "consolidated_bundles": [s for s in skills if s["name"] in consolidated],
            "legacy_skills": [s for s in skills if s["name"] not in consolidated],
            "usage": {
                "get_skill": "vibe://skill/{skill_name} - Get SKILL.md content",
                "list_guides": "vibe://skill/{skill_name}/guides - List available guides",
                "get_guide": "vibe://skill/{skill_name}/guides/{path} - Get specific guide",
                "list_templates": "vibe://skill/{skill_name}/templates - List available templates",
                "get_template": "vibe://skill/{skill_name}/templates/{path} - Get specific template"
            }
        }, indent=2)

    @mcp.resource("vibe://skill/{skill_name}")
    def get_skill_content(skill_name: str) -> str:
        """
        Get the full content of a specific Vibe skill.

        Args:
            skill_name: Name of the skill (e.g., 'cdd-domain', 'tdd-python-test-pyramid')

        Returns:
            Complete skill markdown content with instructions for Claude agents.

        Keywords: skill, instructions, workflow, agent
        """
        skill = skill_manager.get_skill(skill_name)

        if skill is None:
            available = [s["name"] for s in skill_manager.list_skills()]
            return json.dumps({
                "error": f"Skill not found: {skill_name}",
                "available_skills": available,
                "suggestion": "Use vibe://skill/list to see all available skills"
            }, indent=2)

        # Return the raw markdown content - this is what agents need
        return skill["content"]

    @mcp.resource("vibe://skill/search/{query}")
    def search_skills(query: str) -> str:
        """
        Search for skills by keyword.

        Args:
            query: Search term to find relevant skills

        Returns:
            List of matching skills with relevance scores.

        Keywords: search, find, skills, query
        """
        results = skill_manager.search_skills(query)

        return json.dumps({
            "query": query,
            "total_matches": len(results),
            "results": results,
            "usage": "Use vibe://skill/{skill_name} to get the full content"
        }, indent=2)

    @mcp.resource("vibe://skill/reload")
    def reload_skills() -> str:
        """
        Reload all skills from disk.

        Use this after adding new skills to the vibe_skills directory.

        Keywords: reload, refresh, skills
        """
        count = skill_manager.reload_skills()

        return json.dumps({
            "status": "success",
            "skills_loaded": count,
            "message": f"Reloaded {count} skills from disk"
        }, indent=2)

    # ==================== Level 3 Resources ====================

    @mcp.resource("vibe://skill/{skill_name}/guides")
    def list_skill_guides(skill_name: str) -> str:
        """
        List available guides for a skill (Level 3 resources).

        Guides are specialized instruction files that provide detailed
        workflows for specific tasks within a skill bundle.

        Args:
            skill_name: Name of the skill (e.g., 'cdd', 'tdd')

        Returns:
            List of available guides with URIs.

        Keywords: guides, level3, resources, instructions
        """
        skill = skill_manager.get_skill(skill_name)

        if skill is None:
            return json.dumps({
                "error": f"Skill not found: {skill_name}",
                "suggestion": "Use vibe://skill/list to see all available skills"
            }, indent=2)

        guides = skill_manager.list_guides(skill_name)

        return json.dumps({
            "skill": skill_name,
            "total_guides": len(guides),
            "guides": guides,
            "usage": f"Use vibe://skill/{skill_name}/guides/{{path}} to get guide content"
        }, indent=2)

    @mcp.resource("vibe://skill/{skill_name}/guides/{path}")
    def get_skill_guide(skill_name: str, path: str) -> str:
        """
        Get a specific guide content (Level 3 resource).

        Args:
            skill_name: Name of the skill
            path: Relative path to the guide (e.g., 'prd/domain.md')
                  Note: Path should be URL-encoded if it contains slashes

        Returns:
            Guide markdown content.

        Keywords: guide, content, instructions, level3
        """
        # URL-decode the path (handles multi-segment paths like 'prd%2Fdomain.md')
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_guide(skill_name, decoded_path)

        if content is None:
            guides = skill_manager.list_guides(skill_name)
            return json.dumps({
                "error": f"Guide not found: {path}",
                "available_guides": [g["path"] for g in guides],
                "suggestion": f"Use vibe://skill/{skill_name}/guides to see all guides"
            }, indent=2)

        return content

    @mcp.resource("vibe://skill/{skill_name}/templates")
    def list_skill_templates(skill_name: str) -> str:
        """
        List available templates for a skill (Level 3 resources).

        Templates are code/document templates that Claude can use
        to generate consistent artifacts.

        Args:
            skill_name: Name of the skill (e.g., 'cdd', 'tdd')

        Returns:
            List of available templates with URIs.

        Keywords: templates, level3, resources, code
        """
        skill = skill_manager.get_skill(skill_name)

        if skill is None:
            return json.dumps({
                "error": f"Skill not found: {skill_name}",
                "suggestion": "Use vibe://skill/list to see all available skills"
            }, indent=2)

        templates = skill_manager.list_templates(skill_name)

        return json.dumps({
            "skill": skill_name,
            "total_templates": len(templates),
            "templates": templates,
            "usage": f"Use vibe://skill/{skill_name}/templates/{{path}} to get template content"
        }, indent=2)

    @mcp.resource("vibe://skill/{skill_name}/templates/{path}")
    def get_skill_template(skill_name: str, path: str) -> str:
        """
        Get a specific template content (Level 3 resource).

        Args:
            skill_name: Name of the skill
            path: Relative path to the template
                  Note: Path should be URL-encoded if it contains slashes

        Returns:
            Template file content.

        Keywords: template, content, code, level3
        """
        # URL-decode the path (handles multi-segment paths)
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_template(skill_name, decoded_path)

        if content is None:
            templates = skill_manager.list_templates(skill_name)
            return json.dumps({
                "error": f"Template not found: {path}",
                "available_templates": [t["path"] for t in templates][:20],  # Limit output
                "suggestion": f"Use vibe://skill/{skill_name}/templates to see all templates"
            }, indent=2)

        return content

    @mcp.resource("vibe://skill/{skill_name}/scripts")
    def list_skill_scripts(skill_name: str) -> str:
        """
        List available scripts for a skill (Level 3 resources).

        Scripts are executable files that Claude can run via bash
        for deterministic operations without consuming context.

        Args:
            skill_name: Name of the skill

        Returns:
            List of available scripts with URIs.

        Keywords: scripts, level3, resources, executable
        """
        skill = skill_manager.get_skill(skill_name)

        if skill is None:
            return json.dumps({
                "error": f"Skill not found: {skill_name}",
                "suggestion": "Use vibe://skill/list to see all available skills"
            }, indent=2)

        scripts = skill_manager.list_scripts(skill_name)

        return json.dumps({
            "skill": skill_name,
            "total_scripts": len(scripts),
            "scripts": scripts,
            "usage": "Run scripts via Bash tool instead of reading content"
        }, indent=2)

    # Log registration summary
    skills = skill_manager.list_skills()
    logger.debug(f"Registered {len(skills)} Vibe skills as MCP resources")
    for skill in skills:
        has_level3 = skill_manager.get_skill(skill["name"]).get("has_level3", False)
        level_info = "(Level 3)" if has_level3 else "(Level 2)"
        logger.debug(f"  - vibe://skill/{skill['name']} {level_info}")
