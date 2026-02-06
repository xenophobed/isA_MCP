"""
External Skill Installer - Downloads and installs skills from external registries.

Supports installing Claude Skills from:
- npm registry (packages with 'claude-skill' keyword)
- GitHub repositories (skill bundles)
- isA Cloud registry (future)

Installation locations:
- Project scope: ./.claude/skills/{name}/
- User scope: ~/.claude/skills/{name}/

A skill bundle contains:
- SKILL.md (required) - Skill manifest with YAML frontmatter
- guides/ (optional) - Detailed workflow documentation
- templates/ (optional) - File templates
- scripts/ (optional) - Automation scripts
"""
import aiohttp
import asyncio
import json
import logging
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

logger = logging.getLogger(__name__)


class SkillSource(str, Enum):
    """Source registry for skills."""
    NPM = "npm"
    GITHUB = "github"
    ISA_CLOUD = "isa_cloud"
    LOCAL = "local"


@dataclass
class SkillManifest:
    """Parsed skill manifest from SKILL.md frontmatter."""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class InstallResult:
    """Result of skill installation."""
    success: bool
    skill_name: str
    version: str
    install_path: Optional[Path] = None
    source: Optional[SkillSource] = None
    error: Optional[str] = None
    guides_count: int = 0
    templates_count: int = 0


class ExternalSkillInstaller:
    """
    Downloads and installs skills from external registries.

    Example:
        >>> installer = ExternalSkillInstaller()
        >>> result = await installer.install("tdd-advanced", scope=SkillScope.USER)
        >>> print(f"Installed to {result.install_path}")
    """

    # Registry endpoints
    NPM_REGISTRY_URL = "https://registry.npmjs.org"
    GITHUB_API_URL = "https://api.github.com"
    ISA_CLOUD_REGISTRY_URL = "https://registry.isa.cloud/skills"  # Future

    # Skill keywords for npm search
    SKILL_KEYWORDS = {"claude-skill", "mcp-skill", "vibe-skill", "isa-skill"}

    # Default external skills directory (relative to package)
    DEFAULT_EXTERNAL_DIR = Path(__file__).parent.parent.parent / "resources" / "skills" / "external"

    def __init__(
        self,
        external_skills_dir: Optional[Path] = None,
        http_timeout: int = 30,
    ):
        """
        Initialize ExternalSkillInstaller.

        Args:
            external_skills_dir: Directory for external skills
                                 (default: resources/skills/external/)
            http_timeout: HTTP request timeout in seconds
        """
        self._external_dir = external_skills_dir or self.DEFAULT_EXTERNAL_DIR
        self._timeout = aiohttp.ClientTimeout(total=http_timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # =========================================================================
    # Main Installation Methods
    # =========================================================================

    async def install(
        self,
        name: str,
        version: Optional[str] = None,
        source: Optional[SkillSource] = None,
    ) -> InstallResult:
        """
        Install a skill from an external registry.

        Args:
            name: Skill name (e.g., "tdd-advanced", "@org/my-skill")
            version: Specific version (default: latest)
            source: Force specific source (auto-detect if None)

        Returns:
            InstallResult with success status and install path
        """
        logger.info(f"Installing skill: {name}@{version or 'latest'}")

        try:
            # Determine source if not specified
            if source is None:
                source = self._detect_source(name)

            # Fetch skill data from registry
            if source == SkillSource.NPM:
                skill_data = await self._fetch_from_npm(name, version)
            elif source == SkillSource.GITHUB:
                skill_data = await self._fetch_from_github(name, version)
            elif source == SkillSource.ISA_CLOUD:
                skill_data = await self._fetch_from_isa_cloud(name, version)
            else:
                return InstallResult(
                    success=False,
                    skill_name=name,
                    version=version or "unknown",
                    error=f"Unsupported source: {source}",
                )

            if not skill_data:
                return InstallResult(
                    success=False,
                    skill_name=name,
                    version=version or "unknown",
                    error=f"Skill not found: {name}",
                )

            # Determine install path
            skill_path = self._external_dir / self._sanitize_name(name)

            # Write skill files
            await self._write_skill_files(skill_path, skill_data)

            # Parse manifest for metadata
            manifest = self._parse_manifest(skill_data.get("skill_md", ""))

            # Count resources
            guides_count = len(skill_data.get("guides", {}))
            templates_count = len(skill_data.get("templates", {}))

            logger.info(
                f"Installed {name}@{skill_data.get('version', '1.0.0')} to {skill_path} "
                f"({guides_count} guides, {templates_count} templates)"
            )

            return InstallResult(
                success=True,
                skill_name=name,
                version=skill_data.get("version", "1.0.0"),
                install_path=skill_path,
                source=source,
                guides_count=guides_count,
                templates_count=templates_count,
            )

        except Exception as e:
            logger.error(f"Installation failed for {name}: {e}")
            return InstallResult(
                success=False,
                skill_name=name,
                version=version or "unknown",
                error=str(e),
            )

    async def uninstall(self, name: str) -> bool:
        """
        Uninstall a skill.

        Args:
            name: Skill name

        Returns:
            True if uninstalled successfully
        """
        skill_path = self._external_dir / self._sanitize_name(name)

        if not skill_path.exists():
            logger.warning(f"Skill not found: {name}")
            return False

        try:
            shutil.rmtree(skill_path)
            logger.info(f"Uninstalled skill: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall {name}: {e}")
            return False

    def list_installed(self) -> List[Dict[str, Any]]:
        """
        List installed external skills.

        Returns:
            List of installed skills with metadata
        """
        skills = []

        if not self._external_dir.exists():
            return skills

        for skill_dir in self._external_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith((".", "_")):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    manifest = self._parse_manifest(skill_file.read_text())
                    skills.append({
                        "name": skill_dir.name,
                        "description": manifest.description,
                        "version": manifest.version,
                        "path": str(skill_dir),
                        "has_guides": (skill_dir / "guides").exists(),
                        "has_templates": (skill_dir / "templates").exists(),
                    })

        return skills

    # =========================================================================
    # Registry Fetch Methods
    # =========================================================================

    async def _fetch_from_npm(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch skill from npm registry.

        npm packages with claude-skill keyword should have:
        - SKILL.md in package root
        - guides/ directory (optional)
        - templates/ directory (optional)
        """
        session = await self._get_session()

        # Fetch package metadata
        url = f"{self.NPM_REGISTRY_URL}/{name}"

        try:
            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    logger.warning(f"npm fetch failed for {name}: {resp.status}")
                    return None

                pkg_data = await resp.json()
        except Exception as e:
            logger.error(f"npm fetch error for {name}: {e}")
            return None

        # Get target version
        target_version = version or pkg_data.get("dist-tags", {}).get("latest")
        if not target_version:
            return None

        version_data = pkg_data.get("versions", {}).get(target_version, {})

        # Verify it's a skill package
        keywords = version_data.get("keywords", [])
        if not any(kw.lower() in self.SKILL_KEYWORDS for kw in keywords):
            logger.warning(f"Package {name} doesn't have claude-skill keyword")
            # Continue anyway - user explicitly requested it

        # Download tarball and extract skill files
        tarball_url = version_data.get("dist", {}).get("tarball")
        if not tarball_url:
            return None

        return await self._extract_npm_tarball(tarball_url, target_version)

    async def _extract_npm_tarball(
        self,
        tarball_url: str,
        version: str,
    ) -> Optional[Dict[str, Any]]:
        """Extract skill files from npm tarball."""
        session = await self._get_session()

        try:
            async with session.get(tarball_url) as resp:
                if resp.status != 200:
                    return None

                tarball_data = await resp.read()
        except Exception as e:
            logger.error(f"Failed to download tarball: {e}")
            return None

        # Extract to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / "package.tgz"
            tarball_path.write_bytes(tarball_data)

            # Extract tarball
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(tmpdir)

            # npm packages extract to 'package/' subdirectory
            package_dir = Path(tmpdir) / "package"
            if not package_dir.exists():
                # Try finding extracted directory
                for item in Path(tmpdir).iterdir():
                    if item.is_dir() and item.name != "__MACOSX":
                        package_dir = item
                        break

            if not package_dir.exists():
                return None

            return self._read_skill_bundle(package_dir, version)

    async def _fetch_from_github(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch skill from GitHub repository.

        Name format: "owner/repo" or "owner/repo/path/to/skill"
        """
        session = await self._get_session()

        # Parse name
        parts = name.split("/")
        if len(parts) < 2:
            logger.error(f"Invalid GitHub skill name: {name}")
            return None

        owner = parts[0]
        repo = parts[1]
        skill_path = "/".join(parts[2:]) if len(parts) > 2 else ""

        # Determine ref (version or default branch)
        ref = version or "main"

        # Use GitHub API to get contents
        headers = {"Accept": "application/vnd.github.v3+json"}

        # Get repository info for default branch
        if not version:
            repo_url = f"{self.GITHUB_API_URL}/repos/{owner}/{repo}"
            try:
                async with session.get(repo_url, headers=headers) as resp:
                    if resp.status == 200:
                        repo_data = await resp.json()
                        ref = repo_data.get("default_branch", "main")
            except Exception:
                pass

        # Download as tarball
        tarball_url = f"https://github.com/{owner}/{repo}/archive/{ref}.tar.gz"

        try:
            async with session.get(tarball_url) as resp:
                if resp.status != 200:
                    logger.warning(f"GitHub tarball fetch failed: {resp.status}")
                    return None

                tarball_data = await resp.read()
        except Exception as e:
            logger.error(f"GitHub fetch error: {e}")
            return None

        # Extract and find skill bundle
        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / "repo.tgz"
            tarball_path.write_bytes(tarball_data)

            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(tmpdir)

            # Find extracted directory
            extracted_dir = None
            for item in Path(tmpdir).iterdir():
                if item.is_dir() and item.name.startswith(f"{repo}-"):
                    extracted_dir = item
                    break

            if not extracted_dir:
                return None

            # Navigate to skill path if specified
            skill_dir = extracted_dir / skill_path if skill_path else extracted_dir

            if not skill_dir.exists():
                return None

            return self._read_skill_bundle(skill_dir, version or ref)

    async def _fetch_from_isa_cloud(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch skill from isA Cloud registry.

        Future implementation - returns None for now.
        """
        # TODO: Implement when isA Cloud registry is available
        logger.warning("isA Cloud registry not yet implemented")
        return None

    # =========================================================================
    # File Operations
    # =========================================================================

    def _read_skill_bundle(
        self,
        skill_dir: Path,
        version: str,
    ) -> Optional[Dict[str, Any]]:
        """Read skill bundle from directory.

        Searches for SKILL.md in:
        1. Root directory
        2. skill/ subdirectory
        3. Any subdirectory (recursive search)
        """
        skill_file = skill_dir / "SKILL.md"

        # If not at root, search subdirectories
        if not skill_file.exists():
            # Check skill/ subdirectory (common pattern)
            for subdir in skill_dir.iterdir():
                if subdir.is_dir():
                    candidate = subdir / "SKILL.md"
                    if candidate.exists():
                        skill_dir = subdir
                        skill_file = candidate
                        break
                    # Check one level deeper (skill/name/SKILL.md)
                    for nested in subdir.iterdir():
                        if nested.is_dir():
                            candidate = nested / "SKILL.md"
                            if candidate.exists():
                                skill_dir = nested
                                skill_file = candidate
                                break

        if not skill_file.exists():
            logger.warning(f"No SKILL.md found in {skill_dir}")
            return None

        skill_data = {
            "version": version,
            "skill_md": skill_file.read_text(encoding="utf-8"),
            "guides": {},
            "templates": {},
            "scripts": {},
        }

        # Read guides
        guides_dir = skill_dir / "guides"
        if guides_dir.exists():
            for guide_file in guides_dir.rglob("*.md"):
                rel_path = guide_file.relative_to(guides_dir)
                skill_data["guides"][str(rel_path)] = guide_file.read_text(encoding="utf-8")

        # Read templates
        templates_dir = skill_dir / "templates"
        if templates_dir.exists():
            for template_file in templates_dir.rglob("*"):
                if template_file.is_file():
                    rel_path = template_file.relative_to(templates_dir)
                    try:
                        skill_data["templates"][str(rel_path)] = template_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        # Skip binary files
                        pass

        # Read scripts
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.rglob("*"):
                if script_file.is_file():
                    rel_path = script_file.relative_to(scripts_dir)
                    try:
                        skill_data["scripts"][str(rel_path)] = script_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        pass

        return skill_data

    async def _write_skill_files(
        self,
        skill_path: Path,
        skill_data: Dict[str, Any],
    ) -> None:
        """Write skill files to installation directory."""
        # Create skill directory
        skill_path.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text(skill_data["skill_md"], encoding="utf-8")

        # Write guides
        for rel_path, content in skill_data.get("guides", {}).items():
            guide_file = skill_path / "guides" / rel_path
            guide_file.parent.mkdir(parents=True, exist_ok=True)
            guide_file.write_text(content, encoding="utf-8")

        # Write templates
        for rel_path, content in skill_data.get("templates", {}).items():
            template_file = skill_path / "templates" / rel_path
            template_file.parent.mkdir(parents=True, exist_ok=True)
            template_file.write_text(content, encoding="utf-8")

        # Write scripts
        for rel_path, content in skill_data.get("scripts", {}).items():
            script_file = skill_path / "scripts" / rel_path
            script_file.parent.mkdir(parents=True, exist_ok=True)
            script_file.write_text(content, encoding="utf-8")
            # Make scripts executable
            script_file.chmod(0o755)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _detect_source(self, name: str) -> SkillSource:
        """Detect source registry from skill name."""
        if "/" in name and not name.startswith("@"):
            # owner/repo format = GitHub
            return SkillSource.GITHUB
        elif name.startswith("isa://") or name.startswith("isA://"):
            return SkillSource.ISA_CLOUD
        else:
            # Default to npm
            return SkillSource.NPM

    def _sanitize_name(self, name: str) -> str:
        """Sanitize skill name for filesystem."""
        # Remove @ prefix and replace / with -
        sanitized = name.lstrip("@").replace("/", "-")
        # Remove any other invalid characters
        sanitized = re.sub(r'[^\w\-\.]', '-', sanitized)
        return sanitized.lower()

    def _parse_manifest(self, skill_md: str) -> SkillManifest:
        """Parse SKILL.md frontmatter into manifest."""
        metadata = {}

        if skill_md.startswith("---"):
            parts = skill_md.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

        return SkillManifest(
            name=metadata.get("name", "unknown"),
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0.0"),
            author=metadata.get("author"),
            homepage=metadata.get("homepage"),
            repository=metadata.get("repository"),
            license=metadata.get("license"),
            tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
        )


# =========================================================================
# Search Functions
# =========================================================================

async def search_npm_skills(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search npm for Claude skills.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching skill packages
    """
    async with aiohttp.ClientSession() as session:
        search_url = f"https://registry.npmjs.org/-/v1/search"
        params = {
            "text": f"{query} keywords:claude-skill",
            "size": limit,
        }

        try:
            async with session.get(search_url, params=params) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()

                skills = []
                for obj in data.get("objects", []):
                    pkg = obj["package"]
                    skills.append({
                        "name": pkg["name"],
                        "description": pkg.get("description", ""),
                        "version": pkg.get("version"),
                        "author": pkg.get("author", {}).get("name") if isinstance(pkg.get("author"), dict) else pkg.get("author"),
                        "source": "npm",
                        "install_cmd": f"npx @isa-mcp/skills install {pkg['name']}",
                    })

                return skills

        except Exception as e:
            logger.error(f"npm search error: {e}")
            return []


async def search_github_skills(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search GitHub for Claude skill repositories.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching skill repositories
    """
    async with aiohttp.ClientSession() as session:
        search_url = "https://api.github.com/search/repositories"
        headers = {"Accept": "application/vnd.github.v3+json"}
        params = {
            "q": f"{query} topic:claude-skill OR topic:mcp-skill",
            "sort": "stars",
            "per_page": limit,
        }

        try:
            async with session.get(search_url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()

                skills = []
                for repo in data.get("items", []):
                    skills.append({
                        "name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "stars": repo["stargazers_count"],
                        "author": repo["owner"]["login"],
                        "source": "github",
                        "install_cmd": f"npx @isa-mcp/skills install {repo['full_name']}",
                    })

                return skills

        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []
