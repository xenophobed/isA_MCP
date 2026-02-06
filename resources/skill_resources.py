"""
Skill Resources - MCP Resource Registration for All Skills

Manages two types of skills:
1. Vibe Skills (internal): AI-SDLC workflows like TDD, CDD, init, deployment
2. External Skills: Installed from npm, GitHub, or other registries

Directory Structure:
    resources/skills/
    ├── vibe/           # Internal vibe coding skills
    │   ├── tdd/
    │   ├── cdd/
    │   └── ...
    └── external/       # External skills installed by users
        ├── some-skill/
        └── ...

Resource URIs:
    skill://list                              - List all skills (vibe + external)
    skill://vibe/list                         - List vibe skills only
    skill://vibe/{name}                       - Get vibe skill content
    skill://vibe/{name}/guides                - List vibe skill guides
    skill://vibe/{name}/guides/{path}         - Get specific guide
    skill://vibe/{name}/templates             - List vibe skill templates
    skill://vibe/{name}/templates/{path}      - Get specific template
    skill://external/list                     - List external skills only
    skill://external/{name}                   - Get external skill content
    skill://external/{name}/guides/{path}     - Get external skill guide
    skill://search/{query}                    - Search all skills

Backward Compatibility:
    vibe://skill/{name} -> skill://vibe/{name}

Database Integration:
    Skills are registered as resources in PostgreSQL with resource_type="skill".
    This enables vector search via the unified search infrastructure.
"""

import json
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Skills directories
SKILLS_DIR = Path(__file__).parent / "skills"
VIBE_SKILLS_DIR = SKILLS_DIR / "vibe"
EXTERNAL_SKILLS_DIR = SKILLS_DIR / "external"


class SkillManager:
    """
    Unified manager for all skills (vibe and external).

    Provides:
    - Loading skills from vibe/ and external/ directories
    - Level 3 resource access (guides, templates, scripts)
    - Search across all skills
    - Installation tracking for external skills
    """

    def __init__(
        self,
        vibe_dir: Path = VIBE_SKILLS_DIR,
        external_dir: Path = EXTERNAL_SKILLS_DIR,
    ):
        self.vibe_dir = vibe_dir
        self.external_dir = external_dir
        self._vibe_cache: Dict[str, Dict[str, Any]] = {}
        self._external_cache: Dict[str, Dict[str, Any]] = {}
        self._load_all_skills()

    def _load_all_skills(self) -> None:
        """Load all skills from both directories."""
        self._load_skills_from_dir(self.vibe_dir, self._vibe_cache, "vibe")
        self._load_skills_from_dir(self.external_dir, self._external_cache, "external")
        logger.debug(
            f"Loaded {len(self._vibe_cache)} vibe skills, "
            f"{len(self._external_cache)} external skills"
        )

    def _load_skills_from_dir(
        self,
        skills_dir: Path,
        cache: Dict[str, Dict[str, Any]],
        skill_type: str,
    ) -> None:
        """Load skills from a directory into cache."""
        if not skills_dir.exists():
            logger.debug(f"Skills directory not found: {skills_dir}")
            return

        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith(("_", ".")):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    self._load_skill(skill_dir.name, skill_file, skill_dir, cache, skill_type)

    def _load_skill(
        self,
        skill_name: str,
        skill_file: Path,
        skill_dir: Path,
        cache: Dict[str, Dict[str, Any]],
        skill_type: str,
    ) -> None:
        """Load a single skill into cache."""
        try:
            content = skill_file.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(content)

            guides_dir = skill_dir / "guides"
            templates_dir = skill_dir / "templates"
            scripts_dir = skill_dir / "scripts"

            has_level3 = guides_dir.exists() or templates_dir.exists() or scripts_dir.exists()

            cache[skill_name] = {
                "name": skill_name,
                "type": skill_type,
                "description": metadata.get("description", ""),
                "version": metadata.get("version", "1.0.0"),
                "author": metadata.get("author"),
                "content": content,
                "path": str(skill_file),
                "skill_dir": str(skill_dir),
                "has_level3": has_level3,
                "guides_dir": str(guides_dir) if guides_dir.exists() else None,
                "templates_dir": str(templates_dir) if templates_dir.exists() else None,
                "scripts_dir": str(scripts_dir) if scripts_dir.exists() else None,
                "loaded_at": datetime.now().isoformat(),
            }
            logger.debug(f"Loaded {skill_type} skill: {skill_name}")

        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")

    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML frontmatter from markdown content."""
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

    # =========================================================================
    # List Methods
    # =========================================================================

    def list_all_skills(self) -> List[Dict[str, str]]:
        """List all skills (vibe + external)."""
        skills = []
        for name, data in self._vibe_cache.items():
            skills.append({
                "name": name,
                "type": "vibe",
                "description": data.get("description", ""),
                "uri": f"skill://vibe/{name}",
            })
        for name, data in self._external_cache.items():
            skills.append({
                "name": name,
                "type": "external",
                "description": data.get("description", ""),
                "uri": f"skill://external/{name}",
            })
        return skills

    def list_vibe_skills(self) -> List[Dict[str, str]]:
        """List vibe skills only."""
        return [
            {
                "name": name,
                "type": "vibe",
                "description": data.get("description", ""),
                "uri": f"skill://vibe/{name}",
            }
            for name, data in self._vibe_cache.items()
        ]

    def list_external_skills(self) -> List[Dict[str, str]]:
        """List external skills only."""
        return [
            {
                "name": name,
                "type": "external",
                "description": data.get("description", ""),
                "version": data.get("version", "1.0.0"),
                "author": data.get("author"),
                "uri": f"skill://external/{name}",
            }
            for name, data in self._external_cache.items()
        ]

    # =========================================================================
    # Get Methods
    # =========================================================================

    def get_skill(self, skill_type: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific skill by type and name."""
        if skill_type == "vibe":
            return self._vibe_cache.get(skill_name)
        elif skill_type == "external":
            return self._external_cache.get(skill_name)
        return None

    def get_vibe_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get a vibe skill by name."""
        return self._vibe_cache.get(skill_name)

    def get_external_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get an external skill by name."""
        return self._external_cache.get(skill_name)

    # =========================================================================
    # Level 3 Resources (Guides, Templates, Scripts)
    # =========================================================================

    def list_guides(self, skill_type: str, skill_name: str) -> List[Dict[str, str]]:
        """List guides for a skill."""
        skill = self.get_skill(skill_type, skill_name)
        if not skill or not skill.get("guides_dir"):
            return []

        guides_dir = Path(skill["guides_dir"])
        guides = []

        for guide_file in guides_dir.rglob("*.md"):
            rel_path = guide_file.relative_to(guides_dir)
            guides.append({
                "name": guide_file.stem,
                "path": str(rel_path),
                "uri": f"skill://{skill_type}/{skill_name}/guides/{rel_path}",
            })

        return sorted(guides, key=lambda x: x["path"])

    def get_guide(self, skill_type: str, skill_name: str, guide_path: str) -> Optional[str]:
        """Get guide content."""
        skill = self.get_skill(skill_type, skill_name)
        if not skill or not skill.get("guides_dir"):
            return None

        guide_file = Path(skill["guides_dir"]) / guide_path
        if guide_file.exists() and guide_file.suffix == ".md":
            return guide_file.read_text(encoding="utf-8")
        return None

    def list_templates(self, skill_type: str, skill_name: str) -> List[Dict[str, str]]:
        """List templates for a skill."""
        skill = self.get_skill(skill_type, skill_name)
        if not skill or not skill.get("templates_dir"):
            return []

        templates_dir = Path(skill["templates_dir"])
        templates = []

        for template_file in templates_dir.rglob("*"):
            if template_file.is_file():
                rel_path = template_file.relative_to(templates_dir)
                templates.append({
                    "name": template_file.name,
                    "path": str(rel_path),
                    "uri": f"skill://{skill_type}/{skill_name}/templates/{rel_path}",
                })

        return sorted(templates, key=lambda x: x["path"])

    def get_template(self, skill_type: str, skill_name: str, template_path: str) -> Optional[str]:
        """Get template content."""
        skill = self.get_skill(skill_type, skill_name)
        if not skill or not skill.get("templates_dir"):
            return None

        template_file = Path(skill["templates_dir"]) / template_path
        if template_file.exists() and template_file.is_file():
            return template_file.read_text(encoding="utf-8")
        return None

    def list_scripts(self, skill_type: str, skill_name: str) -> List[Dict[str, str]]:
        """List scripts for a skill."""
        skill = self.get_skill(skill_type, skill_name)
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
                    "uri": f"skill://{skill_type}/{skill_name}/scripts/{rel_path}",
                })

        return sorted(scripts, key=lambda x: x["path"])

    # =========================================================================
    # Search
    # =========================================================================

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Search all skills by keyword."""
        query_lower = query.lower()
        results = []

        # Search vibe skills
        for name, data in self._vibe_cache.items():
            score = self._calculate_match_score(query_lower, name, data)
            if score > 0:
                results.append({
                    "name": name,
                    "type": "vibe",
                    "description": data.get("description", ""),
                    "uri": f"skill://vibe/{name}",
                    "match_score": score,
                })

        # Search external skills
        for name, data in self._external_cache.items():
            score = self._calculate_match_score(query_lower, name, data)
            if score > 0:
                results.append({
                    "name": name,
                    "type": "external",
                    "description": data.get("description", ""),
                    "uri": f"skill://external/{name}",
                    "match_score": score,
                })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def _calculate_match_score(self, query: str, name: str, data: Dict) -> float:
        """Calculate relevance score for search."""
        score = 0.0

        if query == name.lower():
            score += 1.0
        elif query in name.lower():
            score += 0.7

        if query in data.get("description", "").lower():
            score += 0.5

        if query in data.get("content", "").lower():
            score += 0.2

        return score

    # =========================================================================
    # Reload & Management
    # =========================================================================

    def reload_skills(self) -> Dict[str, int]:
        """Reload all skills from disk."""
        self._vibe_cache.clear()
        self._external_cache.clear()
        self._load_all_skills()
        return {
            "vibe": len(self._vibe_cache),
            "external": len(self._external_cache),
        }

    def get_external_skills_dir(self) -> Path:
        """Get the external skills directory for installation."""
        return self.external_dir

    # =========================================================================
    # Database Sync - Register skills as resources for vector search
    # =========================================================================

    async def sync_to_database(self) -> Dict[str, Any]:
        """
        Sync all skills to the resources database.

        Skills are registered as resources with resource_type="skill".
        This enables them to flow through the same sync pipeline as
        other resources (embedding → classification → Qdrant).

        Returns:
            Dict with sync statistics
        """
        from services.resource_service.resource_repository import ResourceRepository

        repo = ResourceRepository()
        synced = 0
        failed = 0
        errors = []

        # Sync vibe skills
        for name, data in self._vibe_cache.items():
            try:
                await self._sync_skill_to_db(repo, "vibe", name, data)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync vibe skill {name}: {e}")
                errors.append(f"vibe/{name}: {str(e)}")
                failed += 1

        # Sync external skills
        for name, data in self._external_cache.items():
            try:
                await self._sync_skill_to_db(repo, "external", name, data)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync external skill {name}: {e}")
                errors.append(f"external/{name}: {str(e)}")
                failed += 1

        logger.info(f"Skill sync complete: {synced} synced, {failed} failed")

        return {
            "synced": synced,
            "failed": failed,
            "errors": errors,
            "total": len(self._vibe_cache) + len(self._external_cache),
        }

    async def _sync_skill_to_db(
        self,
        repo,
        skill_type: str,
        skill_name: str,
        skill_data: Dict[str, Any],
    ) -> None:
        """
        Sync a single skill to the resources database.

        Args:
            repo: ResourceRepository instance
            skill_type: "vibe" or "external"
            skill_name: Name of the skill
            skill_data: Skill data from cache
        """
        uri = f"skill://{skill_type}/{skill_name}"

        # Build metadata
        metadata = {
            "skill_type": skill_type,
            "version": skill_data.get("version", "1.0.0"),
            "author": skill_data.get("author"),
            "has_guides": skill_data.get("guides_dir") is not None,
            "has_templates": skill_data.get("templates_dir") is not None,
            "has_scripts": skill_data.get("scripts_dir") is not None,
            "skill_path": skill_data.get("path"),
        }

        # Calculate content size
        content = skill_data.get("content", "")
        size_bytes = len(content.encode("utf-8")) if content else 0

        resource_data = {
            "uri": uri,
            "name": skill_name,
            "description": skill_data.get("description", f"{skill_type.title()} skill: {skill_name}"),
            "resource_type": "skill",
            "mime_type": "text/markdown",
            "size_bytes": size_bytes,
            "metadata": metadata,
            "tags": [skill_type, "skill", "workflow"],
            "is_public": True,
            "is_active": True,
            "is_external": skill_type == "external",
        }

        # Upsert the resource
        await repo.upsert_resource(resource_data)
        logger.debug(f"Synced skill to database: {uri}")

    async def sync_skill_to_database(self, skill_type: str, skill_name: str) -> bool:
        """
        Sync a single skill to the database.

        Useful after installing a new external skill.

        Args:
            skill_type: "vibe" or "external"
            skill_name: Name of the skill

        Returns:
            True if successful
        """
        from services.resource_service.resource_repository import ResourceRepository

        skill_data = self.get_skill(skill_type, skill_name)
        if not skill_data:
            raise ValueError(f"Skill not found: {skill_type}/{skill_name}")

        repo = ResourceRepository()
        await self._sync_skill_to_db(repo, skill_type, skill_name, skill_data)
        return True

    async def remove_skill_from_database(self, skill_type: str, skill_name: str) -> bool:
        """
        Remove a skill from the database.

        Useful after uninstalling an external skill.

        Args:
            skill_type: "vibe" or "external"
            skill_name: Name of the skill

        Returns:
            True if successful
        """
        from services.resource_service.resource_repository import ResourceRepository

        uri = f"skill://{skill_type}/{skill_name}"
        repo = ResourceRepository()

        existing = await repo.get_resource_by_uri(uri)
        if existing:
            await repo.delete_resource(existing["id"])
            logger.info(f"Removed skill from database: {uri}")
            return True

        return False


# Global skill manager instance
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get or create the global skill manager."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager


def register_skill_resources(mcp: FastMCP):
    """Register skill resources with MCP server."""

    logger.debug("Registering skill resources...")
    skill_manager = get_skill_manager()

    # =========================================================================
    # List Resources
    # =========================================================================

    @mcp.resource("skill://list")
    def list_all_skills() -> str:
        """
        List all available skills (vibe + external).

        Returns catalog of all skills with their types and URIs.
        """
        skills = skill_manager.list_all_skills()
        vibe_skills = [s for s in skills if s["type"] == "vibe"]
        external_skills = [s for s in skills if s["type"] == "external"]

        return json.dumps({
            "total_skills": len(skills),
            "vibe_count": len(vibe_skills),
            "external_count": len(external_skills),
            "skills": skills,
            "usage": {
                "get_vibe_skill": "skill://vibe/{name}",
                "get_external_skill": "skill://external/{name}",
                "list_guides": "skill://{type}/{name}/guides",
                "search": "skill://search/{query}",
            }
        }, indent=2)

    @mcp.resource("skill://vibe/list")
    def list_vibe_skills() -> str:
        """
        List vibe coding skills only (TDD, CDD, init, etc.).

        These are internal AI-SDLC workflow skills.
        """
        skills = skill_manager.list_vibe_skills()

        return json.dumps({
            "total": len(skills),
            "type": "vibe",
            "description": "Vibe coding skills for AI-SDLC workflows",
            "skills": skills,
        }, indent=2)

    @mcp.resource("skill://external/list")
    def list_external_skills() -> str:
        """
        List external skills installed from registries.

        These are skills installed via npm, GitHub, etc.
        """
        skills = skill_manager.list_external_skills()

        return json.dumps({
            "total": len(skills),
            "type": "external",
            "description": "External skills installed from registries",
            "skills": skills,
            "install_dir": str(skill_manager.get_external_skills_dir()),
        }, indent=2)

    # =========================================================================
    # Get Skill Content
    # =========================================================================

    @mcp.resource("skill://vibe/{skill_name}")
    def get_vibe_skill(skill_name: str) -> str:
        """
        Get vibe skill content (SKILL.md).

        Args:
            skill_name: Name of the vibe skill (e.g., 'tdd', 'cdd')

        Returns:
            Complete skill markdown with instructions.
        """
        skill = skill_manager.get_vibe_skill(skill_name)

        if skill is None:
            available = [s["name"] for s in skill_manager.list_vibe_skills()]
            return json.dumps({
                "error": f"Vibe skill not found: {skill_name}",
                "available_skills": available,
            }, indent=2)

        return skill["content"]

    @mcp.resource("skill://external/{skill_name}")
    def get_external_skill(skill_name: str) -> str:
        """
        Get external skill content (SKILL.md).

        Args:
            skill_name: Name of the external skill

        Returns:
            Complete skill markdown with instructions.
        """
        skill = skill_manager.get_external_skill(skill_name)

        if skill is None:
            available = [s["name"] for s in skill_manager.list_external_skills()]
            return json.dumps({
                "error": f"External skill not found: {skill_name}",
                "available_skills": available,
                "hint": "Install external skills using: npx @isa-mcp/skills install <name>",
            }, indent=2)

        return skill["content"]

    # =========================================================================
    # Level 3 Resources - Guides
    # =========================================================================

    @mcp.resource("skill://vibe/{skill_name}/guides")
    def list_vibe_skill_guides(skill_name: str) -> str:
        """List guides for a vibe skill."""
        skill = skill_manager.get_vibe_skill(skill_name)
        if skill is None:
            return json.dumps({"error": f"Skill not found: {skill_name}"}, indent=2)

        guides = skill_manager.list_guides("vibe", skill_name)
        return json.dumps({
            "skill": skill_name,
            "type": "vibe",
            "total_guides": len(guides),
            "guides": guides,
        }, indent=2)

    @mcp.resource("skill://vibe/{skill_name}/guides/{path}")
    def get_vibe_skill_guide(skill_name: str, path: str) -> str:
        """Get a specific guide from a vibe skill."""
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_guide("vibe", skill_name, decoded_path)

        if content is None:
            guides = skill_manager.list_guides("vibe", skill_name)
            return json.dumps({
                "error": f"Guide not found: {path}",
                "available_guides": [g["path"] for g in guides],
            }, indent=2)

        return content

    @mcp.resource("skill://external/{skill_name}/guides")
    def list_external_skill_guides(skill_name: str) -> str:
        """List guides for an external skill."""
        skill = skill_manager.get_external_skill(skill_name)
        if skill is None:
            return json.dumps({"error": f"Skill not found: {skill_name}"}, indent=2)

        guides = skill_manager.list_guides("external", skill_name)
        return json.dumps({
            "skill": skill_name,
            "type": "external",
            "total_guides": len(guides),
            "guides": guides,
        }, indent=2)

    @mcp.resource("skill://external/{skill_name}/guides/{path}")
    def get_external_skill_guide(skill_name: str, path: str) -> str:
        """Get a specific guide from an external skill."""
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_guide("external", skill_name, decoded_path)

        if content is None:
            guides = skill_manager.list_guides("external", skill_name)
            return json.dumps({
                "error": f"Guide not found: {path}",
                "available_guides": [g["path"] for g in guides],
            }, indent=2)

        return content

    # =========================================================================
    # Level 3 Resources - Templates
    # =========================================================================

    @mcp.resource("skill://vibe/{skill_name}/templates")
    def list_vibe_skill_templates(skill_name: str) -> str:
        """List templates for a vibe skill."""
        skill = skill_manager.get_vibe_skill(skill_name)
        if skill is None:
            return json.dumps({"error": f"Skill not found: {skill_name}"}, indent=2)

        templates = skill_manager.list_templates("vibe", skill_name)
        return json.dumps({
            "skill": skill_name,
            "type": "vibe",
            "total_templates": len(templates),
            "templates": templates,
        }, indent=2)

    @mcp.resource("skill://vibe/{skill_name}/templates/{path}")
    def get_vibe_skill_template(skill_name: str, path: str) -> str:
        """Get a specific template from a vibe skill."""
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_template("vibe", skill_name, decoded_path)

        if content is None:
            templates = skill_manager.list_templates("vibe", skill_name)
            return json.dumps({
                "error": f"Template not found: {path}",
                "available_templates": [t["path"] for t in templates][:20],
            }, indent=2)

        return content

    @mcp.resource("skill://external/{skill_name}/templates")
    def list_external_skill_templates(skill_name: str) -> str:
        """List templates for an external skill."""
        skill = skill_manager.get_external_skill(skill_name)
        if skill is None:
            return json.dumps({"error": f"Skill not found: {skill_name}"}, indent=2)

        templates = skill_manager.list_templates("external", skill_name)
        return json.dumps({
            "skill": skill_name,
            "type": "external",
            "total_templates": len(templates),
            "templates": templates,
        }, indent=2)

    @mcp.resource("skill://external/{skill_name}/templates/{path}")
    def get_external_skill_template(skill_name: str, path: str) -> str:
        """Get a specific template from an external skill."""
        decoded_path = urllib.parse.unquote(path)
        content = skill_manager.get_template("external", skill_name, decoded_path)

        if content is None:
            templates = skill_manager.list_templates("external", skill_name)
            return json.dumps({
                "error": f"Template not found: {path}",
                "available_templates": [t["path"] for t in templates][:20],
            }, indent=2)

        return content

    # =========================================================================
    # Search & Reload
    # =========================================================================

    @mcp.resource("skill://search/{query}")
    def search_skills(query: str) -> str:
        """
        Search all skills by keyword.

        Searches across both vibe and external skills.
        """
        results = skill_manager.search_skills(query)

        return json.dumps({
            "query": query,
            "total_matches": len(results),
            "results": results,
        }, indent=2)

    @mcp.resource("skill://reload")
    def reload_skills() -> str:
        """Reload all skills from disk."""
        counts = skill_manager.reload_skills()

        return json.dumps({
            "status": "success",
            "vibe_skills_loaded": counts["vibe"],
            "external_skills_loaded": counts["external"],
        }, indent=2)

    # =========================================================================
    # Backward Compatibility - vibe://skill/ URIs
    # =========================================================================

    @mcp.resource("vibe://skill/list")
    def compat_list_vibe_skills() -> str:
        """[Backward Compat] List vibe skills."""
        return list_vibe_skills()

    @mcp.resource("vibe://skill/{skill_name}")
    def compat_get_vibe_skill(skill_name: str) -> str:
        """[Backward Compat] Get vibe skill content."""
        return get_vibe_skill(skill_name)

    @mcp.resource("vibe://skill/{skill_name}/guides")
    def compat_list_guides(skill_name: str) -> str:
        """[Backward Compat] List vibe skill guides."""
        return list_vibe_skill_guides(skill_name)

    @mcp.resource("vibe://skill/{skill_name}/guides/{path}")
    def compat_get_guide(skill_name: str, path: str) -> str:
        """[Backward Compat] Get vibe skill guide."""
        return get_vibe_skill_guide(skill_name, path)

    @mcp.resource("vibe://skill/{skill_name}/templates")
    def compat_list_templates(skill_name: str) -> str:
        """[Backward Compat] List vibe skill templates."""
        return list_vibe_skill_templates(skill_name)

    @mcp.resource("vibe://skill/{skill_name}/templates/{path}")
    def compat_get_template(skill_name: str, path: str) -> str:
        """[Backward Compat] Get vibe skill template."""
        return get_vibe_skill_template(skill_name, path)

    @mcp.resource("vibe://skill/search/{query}")
    def compat_search_skills(query: str) -> str:
        """[Backward Compat] Search skills."""
        return search_skills(query)

    @mcp.resource("vibe://skill/reload")
    def compat_reload_skills() -> str:
        """[Backward Compat] Reload skills."""
        return reload_skills()

    # =========================================================================
    # Dynamic Registration - Individual Skill Resources
    # Register each skill with its specific URI so they appear in list_resources()
    # This enables sync_resources() to index them for semantic search
    # =========================================================================

    def _create_skill_getter(skill_type: str, skill_name: str):
        """Create a getter function for a specific skill (closure)."""
        def getter() -> str:
            skill = skill_manager.get_skill(skill_type, skill_name)
            if skill is None:
                return json.dumps({"error": f"Skill not found: {skill_type}/{skill_name}"})
            return skill.get("content", "")
        # Set function name and doc for proper resource registration
        getter.__name__ = skill_name
        getter.__doc__ = f"Get {skill_type} skill: {skill_name}"
        return getter

    # Register all skills as individual resources
    all_skills = skill_manager.list_all_skills()
    for skill in all_skills:
        skill_type = skill.get("type", "vibe")
        skill_name = skill.get("name")
        skill_desc = skill.get("description", f"{skill_type} skill: {skill_name}")

        if skill_name:
            uri = f"skill://{skill_type}/{skill_name}"
            getter_func = _create_skill_getter(skill_type, skill_name)
            # Register with description for better sync/search
            mcp.resource(uri, description=skill_desc)(getter_func)
            logger.debug(f"  Registered individual skill resource: {uri}")

    # Log registration summary
    skills = skill_manager.list_all_skills()
    vibe_count = len([s for s in skills if s["type"] == "vibe"])
    external_count = len([s for s in skills if s["type"] == "external"])
    logger.debug(f"Registered {vibe_count} vibe skills, {external_count} external skills")
