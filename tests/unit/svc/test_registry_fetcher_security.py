"""
Unit tests for SSRF protection in RegistryFetcher.

Tests the _validate_url function that protects against:
- Private/internal IP addresses
- Localhost and loopback addresses
- Cloud metadata endpoints
- Non-allowlisted hosts
- Invalid URL schemes

Issue #14: SSRF protection validation tests
"""

import pytest
from services.marketplace_service.registry_fetcher import _validate_url, _ALLOWED_REGISTRY_HOSTS


class TestSSRFProtection:
    """Tests for SSRF protection in _validate_url."""

    # =========================================================================
    # Valid URLs (should pass validation)
    # =========================================================================

    def test_valid_npm_registry_url(self):
        """Test that npm registry URL is allowed."""
        url = "https://registry.npmjs.org/-/v1/search"
        # Should not raise
        _validate_url(url)

    def test_valid_github_api_url(self):
        """Test that GitHub API URL is allowed."""
        url = "https://api.github.com/search/repositories"
        # Should not raise
        _validate_url(url)

    def test_valid_http_scheme(self):
        """Test that http scheme is allowed for allowlisted hosts."""
        url = "http://registry.npmjs.org/package"
        # Should not raise
        _validate_url(url)

    def test_valid_https_scheme(self):
        """Test that https scheme is allowed."""
        url = "https://registry.npmjs.org/package"
        # Should not raise
        _validate_url(url)

    def test_all_allowlisted_hosts(self):
        """Test all hosts in the allowlist are accepted."""
        for host in _ALLOWED_REGISTRY_HOSTS:
            url = f"https://{host}/some/path"
            # Should not raise for any allowlisted host
            _validate_url(url)

    # =========================================================================
    # Invalid Schemes (should be blocked)
    # =========================================================================

    def test_block_file_scheme(self):
        """Test that file:// scheme is blocked."""
        url = "file:///etc/passwd"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        # file:// URLs have no network hostname, so they're caught by hostname check
        assert "invalid" in str(exc_info.value).lower()

    def test_block_ftp_scheme(self):
        """Test that ftp:// scheme is blocked."""
        url = "ftp://registry.npmjs.org/package"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "scheme" in str(exc_info.value).lower()

    def test_block_javascript_scheme(self):
        """Test that javascript: scheme is blocked."""
        url = "javascript:alert(1)"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        # Either no hostname or invalid scheme
        assert "invalid" in str(exc_info.value).lower()

    def test_block_data_scheme(self):
        """Test that data: scheme is blocked."""
        url = "data:text/plain,hello"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "invalid" in str(exc_info.value).lower()

    # =========================================================================
    # Private IP Addresses (should be blocked)
    # =========================================================================

    def test_block_localhost(self):
        """Test that localhost is blocked."""
        url = "http://localhost:8080/internal"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "allowlist" in str(exc_info.value).lower()

    def test_block_127_0_0_1(self):
        """Test that 127.0.0.1 (loopback) is blocked."""
        url = "http://127.0.0.1:8080/internal"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "private" in str(exc_info.value).lower() or "loopback" in str(exc_info.value).lower()

    def test_block_loopback_variations(self):
        """Test that all loopback address variations are blocked."""
        loopback_urls = [
            "http://127.0.0.1/",
            "http://127.0.0.2/",
            "http://127.255.255.255/",
        ]
        for url in loopback_urls:
            with pytest.raises(ValueError):
                _validate_url(url)

    def test_block_10_x_x_x_private_range(self):
        """Test that 10.x.x.x private range is blocked."""
        urls = [
            "http://10.0.0.1/internal",
            "http://10.255.255.255/internal",
            "http://10.100.50.25/internal",
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            assert "private" in str(exc_info.value).lower()

    def test_block_172_16_x_x_private_range(self):
        """Test that 172.16.x.x - 172.31.x.x private range is blocked."""
        urls = [
            "http://172.16.0.1/internal",
            "http://172.20.10.5/internal",
            "http://172.31.255.255/internal",
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            assert "private" in str(exc_info.value).lower()

    def test_block_192_168_x_x_private_range(self):
        """Test that 192.168.x.x private range is blocked."""
        urls = [
            "http://192.168.0.1/internal",
            "http://192.168.1.1/internal",
            "http://192.168.255.255/internal",
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            assert "private" in str(exc_info.value).lower()

    # =========================================================================
    # Cloud Metadata Endpoints (should be blocked)
    # =========================================================================

    def test_block_aws_metadata_endpoint(self):
        """Test that AWS metadata endpoint (169.254.169.254) is blocked."""
        url = "http://169.254.169.254/latest/meta-data/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        error_msg = str(exc_info.value).lower()
        assert "metadata" in error_msg or "cidr" in error_msg

    def test_block_link_local_range(self):
        """Test that 169.254.x.x link-local range is blocked."""
        urls = [
            "http://169.254.0.1/",
            "http://169.254.100.100/",
            "http://169.254.255.254/",
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            error_msg = str(exc_info.value).lower()
            assert "metadata" in error_msg or "cidr" in error_msg or "link" in error_msg

    def test_block_gcp_metadata_hostname(self):
        """Test that GCP metadata hostname is blocked."""
        url = "http://metadata.google.internal/computeMetadata/v1/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "metadata" in str(exc_info.value).lower()

    def test_block_internal_domain_suffix(self):
        """Test that .internal domain suffix is blocked."""
        urls = [
            "http://anything.internal/",
            "http://service.kubernetes.internal/",
            "http://db.corp.internal/",
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            assert "metadata" in str(exc_info.value).lower() or "internal" in str(exc_info.value).lower()

    # =========================================================================
    # Non-Allowlisted Hosts (should be blocked)
    # =========================================================================

    def test_block_arbitrary_external_host(self):
        """Test that arbitrary external hosts are blocked."""
        url = "https://evil-attacker.com/malicious"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "allowlist" in str(exc_info.value).lower()

    def test_block_similar_looking_hosts(self):
        """Test that hosts similar to allowlisted ones are blocked."""
        urls = [
            "https://registry.npmjs.org.evil.com/",  # subdomain of evil.com
            "https://api.github.com.attacker.io/",
            "https://fake-registry.npmjs.org/",
            "https://npmjs.org/",  # missing registry. prefix
        ]
        for url in urls:
            with pytest.raises(ValueError) as exc_info:
                _validate_url(url)
            assert "allowlist" in str(exc_info.value).lower()

    # =========================================================================
    # IPv6 Addresses (should be blocked if private/loopback)
    # =========================================================================

    def test_block_ipv6_loopback(self):
        """Test that IPv6 loopback (::1) is blocked."""
        url = "http://[::1]:8080/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        error_msg = str(exc_info.value).lower()
        assert "loopback" in error_msg or "private" in error_msg

    def test_block_ipv6_private(self):
        """Test that IPv6 private addresses are blocked."""
        # fc00::/7 is the unique local address range
        url = "http://[fd00::1]:8080/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        error_msg = str(exc_info.value).lower()
        assert "private" in error_msg or "internal" in error_msg

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_block_empty_hostname(self):
        """Test that URLs without hostname are blocked."""
        url = "http:///path"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "hostname" in str(exc_info.value).lower()

    def test_block_url_with_credentials(self):
        """Test URL with embedded credentials (should still validate host)."""
        # The credentials don't bypass the allowlist check
        url = "https://user:pass@evil.com/path"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "allowlist" in str(exc_info.value).lower()

    def test_block_url_with_port_bypass_attempt(self):
        """Test that port numbers don't bypass security checks."""
        # Trying to use different port on private IP
        url = "http://192.168.1.1:443/internal"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        assert "private" in str(exc_info.value).lower()

    def test_block_metadata_hostname_literal(self):
        """Test that 'metadata' hostname alone is blocked."""
        url = "http://metadata/computeMetadata/v1/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        error_msg = str(exc_info.value).lower()
        assert "metadata" in error_msg or "allowlist" in error_msg

    def test_block_instance_data_hostname(self):
        """Test that 'instance-data' hostname is blocked."""
        url = "http://instance-data/latest/"
        with pytest.raises(ValueError) as exc_info:
            _validate_url(url)
        error_msg = str(exc_info.value).lower()
        assert "metadata" in error_msg or "allowlist" in error_msg
