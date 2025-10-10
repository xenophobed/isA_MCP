#!/usr/bin/env python3
"""
BS4 Service - Enhanced BeautifulSoup extraction with comprehensive features

Features:
- Basic text extraction (title, headings, paragraphs, links)
- Tables extraction with data preservation
- Images and media extraction
- Code blocks and pre-formatted text
- Lists (ordered and unordered)
- Metadata extraction (OpenGraph, Twitter Cards, JSON-LD)
- Forms and input fields
- SEO analysis
- Content readability scoring
"""

import requests
import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BS4ExtractionResult:
    """Result from BS4 text extraction"""
    success: bool
    url: str = ""
    title: str = ""
    content: str = ""
    headings: list = field(default_factory=list)
    links: list = field(default_factory=list)
    paragraphs: list = field(default_factory=list)
    # Enhanced fields
    tables: list = field(default_factory=list)
    images: list = field(default_factory=list)
    videos: list = field(default_factory=list)
    code_blocks: list = field(default_factory=list)
    lists: Dict[str, list] = field(default_factory=dict)
    forms: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    seo_analysis: Dict[str, Any] = field(default_factory=dict)
    readability_score: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    processing_time: float = 0.0
    error: Optional[str] = None
    extraction_stats: Dict[str, int] = field(default_factory=dict)


class BS4Service:
    """Enhanced BS4 text extraction service"""
    
    def __init__(self):
        logger.info("✨ BS4Service initialized with enhanced extraction capabilities")
    
    async def extract_text(self, url: str, enhanced: bool = False, options: Dict[str, bool] = None) -> BS4ExtractionResult:
        """
        Extract content from a web page using BeautifulSoup
        
        Args:
            url: Target web page URL
            enhanced: Enable enhanced extraction (tables, images, metadata, etc.)
            options: Specific extraction options when enhanced=True
            
        Returns:
            BS4ExtractionResult with extracted content
        """
        if enhanced:
            return await self.extract_enhanced(url, options)
        
        # Original simple extraction
        try:
            start_time = asyncio.get_event_loop().time()
            logger.info(f"📄 Starting BS4 text extraction for: {url}")
            
            # Fetch the webpage
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Remove script, style, nav, header, footer tags
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'meta', 'link']):
                tag.decompose()
            
            # Extract headings
            headings = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        'level': heading.name,
                        'text': text
                    })
            
            # Extract paragraphs
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Only meaningful paragraphs
                    paragraphs.append(text)
            
            # Extract links
            links = self._extract_simple_links(soup)
            
            # Get main text content
            main_content = soup.get_text(separator=' ', strip=True)
            
            # Clean up the text
            content = self._clean_text(main_content)
            word_count = len(content.split())
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"✅ BS4 extraction completed in {processing_time:.2f}s - {word_count} words")
            
            return BS4ExtractionResult(
                success=True,
                url=url,
                title=title,
                content=content,
                headings=headings,
                links=links,
                paragraphs=paragraphs,
                word_count=word_count,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ BS4 extraction failed: {e}")
            return BS4ExtractionResult(
                success=False,
                url=url,
                processing_time=processing_time,
                error=str(e)
            )
    
    async def extract_enhanced(self, url: str, options: Dict[str, bool] = None) -> BS4ExtractionResult:
        """
        Extract comprehensive content from a web page
        
        Args:
            url: Target web page URL
            options: Extraction options (tables, images, metadata, seo, etc.)
            
        Returns:
            BS4ExtractionResult with comprehensive extracted content
        """
        if options is None:
            options = {
                'tables': True,
                'images': True,
                'metadata': True,
                'forms': True,
                'code_blocks': True,
                'lists': True,
                'seo_analysis': True,
                'readability': True
            }
        
        try:
            start_time = asyncio.get_event_loop().time()
            logger.info(f"🚀 Starting enhanced BS4 extraction for: {url}")
            
            # Fetch the webpage
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Initialize result
            result = BS4ExtractionResult(success=True, url=url)
            
            # Basic extraction
            result.title = self._extract_title(soup)
            
            # Clone soup for text extraction
            text_soup = BeautifulSoup(str(soup), 'html.parser')
            
            # Extract enhanced features before removing tags
            if options.get('tables', True):
                result.tables = self._extract_tables(soup, url)
            
            if options.get('images', True):
                result.images = self._extract_images(soup, url)
                result.videos = self._extract_videos(soup, url)
            
            if options.get('code_blocks', True):
                result.code_blocks = self._extract_code_blocks(soup)
            
            if options.get('lists', True):
                result.lists = self._extract_lists(soup)
            
            if options.get('forms', True):
                result.forms = self._extract_forms(soup)
            
            if options.get('metadata', True):
                result.metadata = self._extract_metadata(soup, url)
            
            # Remove scripts and styles for text extraction
            for tag in text_soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Extract text content
            result.headings = self._extract_headings(text_soup)
            result.paragraphs = self._extract_paragraphs(text_soup)
            result.links = self._extract_links(text_soup, url)
            
            # Get main text content
            result.content = text_soup.get_text(separator=' ', strip=True)
            result.content = self._clean_text(result.content)
            result.word_count = len(result.content.split())
            
            # Advanced analysis
            if options.get('seo_analysis', True):
                result.seo_analysis = self._analyze_seo(soup, result)
            
            if options.get('readability', True):
                result.readability_score = self._calculate_readability(result.content)
            
            # Calculate extraction statistics
            result.extraction_stats = {
                'headings': len(result.headings),
                'paragraphs': len(result.paragraphs),
                'links': len(result.links),
                'tables': len(result.tables),
                'images': len(result.images),
                'videos': len(result.videos),
                'code_blocks': len(result.code_blocks),
                'forms': len(result.forms),
                'ordered_lists': len(result.lists.get('ordered', [])),
                'unordered_lists': len(result.lists.get('unordered', [])),
                'words': result.word_count
            }
            
            result.processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"✅ Enhanced extraction completed in {result.processing_time:.2f}s")
            logger.info(f"📊 Extracted: {result.extraction_stats}")
            
            return result
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ Enhanced BS4 extraction failed: {e}")
            return BS4ExtractionResult(
                success=False,
                url=url,
                processing_time=processing_time,
                error=str(e)
            )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try og:title as fallback
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '')
        
        # Try h1 as last resort
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return ""
    
    def _extract_simple_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract simple links for basic mode"""
        links = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']
            if text and href:
                links.append({
                    'text': text,
                    'url': href
                })
        return links
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all headings with hierarchy"""
        headings = []
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(level):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        'level': level,
                        'text': text,
                        'id': heading.get('id', ''),
                        'class': ' '.join(heading.get('class', []))
                    })
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extract meaningful paragraphs"""
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                paragraphs.append(text)
        return paragraphs
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract links with absolute URLs"""
        links = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']
            
            # Make URL absolute
            absolute_url = urljoin(base_url, href)
            
            if text or href:
                links.append({
                    'text': text,
                    'url': absolute_url,
                    'rel': link.get('rel', []),
                    'target': link.get('target', ''),
                    'title': link.get('title', '')
                })
        return links
    
    def _extract_tables(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract tables with data preservation"""
        tables = []
        for table in soup.find_all('table'):
            headers = []
            for th in table.find_all('th'):
                headers.append(th.get_text(strip=True))
            
            rows = []
            for tr in table.find_all('tr'):
                row_data = []
                for td in tr.find_all('td'):
                    link = td.find('a', href=True)
                    if link:
                        cell_data = {
                            'text': td.get_text(strip=True),
                            'link': urljoin(base_url, link['href'])
                        }
                    else:
                        cell_data = td.get_text(strip=True)
                    row_data.append(cell_data)
                if row_data:
                    rows.append(row_data)
            
            if headers or rows:
                tables.append({
                    'headers': headers,
                    'rows': rows,
                    'caption': table.find('caption').get_text(strip=True) if table.find('caption') else '',
                    'class': ' '.join(table.get('class', [])),
                    'id': table.get('id', '')
                })
        return tables
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images with metadata"""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                images.append({
                    'src': urljoin(base_url, src),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', ''),
                    'loading': img.get('loading', ''),
                    'srcset': img.get('srcset', ''),
                    'class': ' '.join(img.get('class', []))
                })
        return images
    
    def _extract_videos(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract video elements"""
        videos = []
        
        for video in soup.find_all('video'):
            video_data = {
                'src': urljoin(base_url, video.get('src', '')),
                'poster': urljoin(base_url, video.get('poster', '')),
                'width': video.get('width', ''),
                'height': video.get('height', ''),
                'controls': video.has_attr('controls'),
                'autoplay': video.has_attr('autoplay'),
                'sources': []
            }
            
            for source in video.find_all('source'):
                video_data['sources'].append({
                    'src': urljoin(base_url, source.get('src', '')),
                    'type': source.get('type', '')
                })
            
            videos.append(video_data)
        
        # YouTube/Vimeo iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'vimeo.com' in src or 'video' in src.lower():
                videos.append({
                    'type': 'iframe',
                    'src': src,
                    'width': iframe.get('width', ''),
                    'height': iframe.get('height', ''),
                    'title': iframe.get('title', '')
                })
        
        return videos
    
    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract code blocks and pre-formatted text"""
        code_blocks = []
        
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                code_blocks.append({
                    'type': 'pre-code',
                    'language': ' '.join(code.get('class', [])),
                    'content': code.get_text(strip=False)
                })
            else:
                code_blocks.append({
                    'type': 'pre',
                    'content': pre.get_text(strip=False)
                })
        
        for code in soup.find_all('code'):
            if not code.find_parent('pre'):
                code_blocks.append({
                    'type': 'inline-code',
                    'content': code.get_text(strip=False)
                })
        
        return code_blocks
    
    def _extract_lists(self, soup: BeautifulSoup) -> Dict[str, List[Any]]:
        """Extract ordered and unordered lists"""
        lists = {'ordered': [], 'unordered': [], 'definition': []}
        
        for ul in soup.find_all('ul'):
            items = []
            for li in ul.find_all('li', recursive=False):
                item = {
                    'text': li.get_text(strip=True),
                    'nested': []
                }
                
                nested_ul = li.find('ul')
                nested_ol = li.find('ol')
                if nested_ul or nested_ol:
                    for nested_li in li.find_all('li'):
                        item['nested'].append(nested_li.get_text(strip=True))
                
                items.append(item)
            
            if items:
                lists['unordered'].append(items)
        
        for ol in soup.find_all('ol'):
            items = []
            for li in ol.find_all('li', recursive=False):
                items.append(li.get_text(strip=True))
            
            if items:
                lists['ordered'].append(items)
        
        for dl in soup.find_all('dl'):
            definitions = []
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                definitions.append({
                    'term': dt.get_text(strip=True),
                    'definition': dd.get_text(strip=True)
                })
            
            if definitions:
                lists['definition'].append(definitions)
        
        return lists
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract form elements and their fields"""
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'name': form.get('name', ''),
                'id': form.get('id', ''),
                'fields': []
            }
            
            for input_field in form.find_all('input'):
                field = {
                    'type': input_field.get('type', 'text'),
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'placeholder': input_field.get('placeholder', ''),
                    'required': input_field.has_attr('required'),
                    'value': input_field.get('value', '')
                }
                form_data['fields'].append(field)
            
            for select in form.find_all('select'):
                options = []
                for option in select.find_all('option'):
                    options.append({
                        'value': option.get('value', ''),
                        'text': option.get_text(strip=True),
                        'selected': option.has_attr('selected')
                    })
                
                form_data['fields'].append({
                    'type': 'select',
                    'name': select.get('name', ''),
                    'id': select.get('id', ''),
                    'options': options
                })
            
            for textarea in form.find_all('textarea'):
                form_data['fields'].append({
                    'type': 'textarea',
                    'name': textarea.get('name', ''),
                    'id': textarea.get('id', ''),
                    'placeholder': textarea.get('placeholder', ''),
                    'rows': textarea.get('rows', ''),
                    'cols': textarea.get('cols', '')
                })
            
            for button in form.find_all('button'):
                form_data['fields'].append({
                    'type': 'button',
                    'text': button.get_text(strip=True),
                    'button_type': button.get('type', 'submit')
                })
            
            forms.append(form_data)
        
        return forms
    
    def _extract_metadata(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract metadata including OpenGraph, Twitter Cards, and JSON-LD"""
        metadata = {
            'meta_tags': {},
            'opengraph': {},
            'twitter': {},
            'json_ld': [],
            'canonical': '',
            'favicon': ''
        }
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '')
            property = meta.get('property', '')
            content = meta.get('content', '')
            
            if name:
                metadata['meta_tags'][name] = content
            
            if property and property.startswith('og:'):
                metadata['opengraph'][property] = content
            
            if name and name.startswith('twitter:'):
                metadata['twitter'][name] = content
        
        canonical = soup.find('link', rel='canonical')
        if canonical:
            metadata['canonical'] = canonical.get('href', '')
        
        favicon = soup.find('link', rel=lambda x: x and 'icon' in x)
        if favicon:
            metadata['favicon'] = urljoin(base_url, favicon.get('href', ''))
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                json_data = json.loads(script.string)
                metadata['json_ld'].append(json_data)
            except json.JSONDecodeError:
                pass
        
        return metadata
    
    def _analyze_seo(self, soup: BeautifulSoup, result: BS4ExtractionResult) -> Dict[str, Any]:
        """Analyze SEO aspects of the page"""
        seo = {
            'title_length': len(result.title),
            'title_ok': 30 <= len(result.title) <= 60,
            'meta_description': '',
            'meta_description_length': 0,
            'meta_description_ok': False,
            'h1_count': 0,
            'h2_count': 0,
            'image_alt_missing': 0,
            'internal_links': 0,
            'external_links': 0,
            'canonical_url': result.metadata.get('canonical', ''),
            'robots': '',
            'sitemap': False,
            'schema_org': len(result.metadata.get('json_ld', [])) > 0
        }
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            seo['meta_description'] = meta_desc.get('content', '')
            seo['meta_description_length'] = len(seo['meta_description'])
            seo['meta_description_ok'] = 120 <= seo['meta_description_length'] <= 160
        
        seo['h1_count'] = len(soup.find_all('h1'))
        seo['h2_count'] = len(soup.find_all('h2'))
        
        for img in result.images:
            if not img.get('alt'):
                seo['image_alt_missing'] += 1
        
        parsed_base = urlparse(result.url)
        for link in result.links:
            parsed_link = urlparse(link['url'])
            if parsed_link.netloc == parsed_base.netloc:
                seo['internal_links'] += 1
            elif parsed_link.scheme in ['http', 'https']:
                seo['external_links'] += 1
        
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta:
            seo['robots'] = robots_meta.get('content', '')
        
        sitemap_link = soup.find('link', rel='sitemap')
        seo['sitemap'] = sitemap_link is not None
        
        return seo
    
    def _calculate_readability(self, text: str) -> Dict[str, Any]:
        """Calculate readability scores"""
        if not text:
            return {'error': 'No text to analyze'}
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        if sentence_count == 0:
            return {'error': 'No sentences found'}
        
        avg_words_per_sentence = word_count / sentence_count
        
        syllable_count = 0
        for word in words:
            word = word.lower()
            vowels = 'aeiouy'
            syllables = 0
            previous_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not previous_was_vowel:
                    syllables += 1
                previous_was_vowel = is_vowel
            
            if syllables == 0:
                syllables = 1
            
            syllable_count += syllables
        
        avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0
        
        flesch_score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
        
        if flesch_score >= 90:
            difficulty = "Very Easy"
            grade_level = "5th grade"
        elif flesch_score >= 80:
            difficulty = "Easy"
            grade_level = "6th grade"
        elif flesch_score >= 70:
            difficulty = "Fairly Easy"
            grade_level = "7th grade"
        elif flesch_score >= 60:
            difficulty = "Standard"
            grade_level = "8th-9th grade"
        elif flesch_score >= 50:
            difficulty = "Fairly Difficult"
            grade_level = "10th-12th grade"
        elif flesch_score >= 30:
            difficulty = "Difficult"
            grade_level = "College"
        else:
            difficulty = "Very Difficult"
            grade_level = "College graduate"
        
        return {
            'flesch_reading_ease': round(flesch_score, 2),
            'difficulty': difficulty,
            'grade_level': grade_level,
            'avg_words_per_sentence': round(avg_words_per_sentence, 2),
            'avg_syllables_per_word': round(avg_syllables_per_word, 2),
            'word_count': word_count,
            'sentence_count': sentence_count
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


# Global instance for easy import
bs4_service = BS4Service()


# Convenience function
async def extract_text(url: str, enhanced: bool = False, options: Dict[str, bool] = None) -> BS4ExtractionResult:
    """Extract text from URL using BS4"""
    return await bs4_service.extract_text(url, enhanced, options)