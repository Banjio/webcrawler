import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Any, List, Optional
import httpx
from dataclasses import dataclass, field
import logging
from functools import wraps

logger = logging.getLogger(__name__)


#TODO: This doesnot work find out why
@wraps
def check_empty_soup(fun):
    def inner(*args, **kwargs):
        if args[1] is None:
            return None
        else:
            return fun(*args, **kwargs)
    return inner
@dataclass
class FetchResult:
    content: str
    status_code: int
    error_msg: Optional[str] = None
    success: bool = True

@dataclass
class ParseResult:
    content: str = ""
    links: Optional[List[str]] = field(default_factory=lambda: [])
    title: Optional[str] = None

class Session():

    def __init__(self, user_agent: str = "*", timeout: int = 10, raise_on_error: bool = False):
        self.session = httpx.Client()
        self.session.headers.update(
            {'User-Agent': user_agent}
            )
        self.timeout = timeout
        self.raise_on_error = raise_on_error #QA: Is this really neccesary decide later

    def fetch(self, url) -> FetchResult:
        """
        Fetch the web page content from the URL.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            True if page was successfully fetched, False otherwise
        """
        try:
            resp = self.session.get(url, timeout=self.timeout)
            self.status_code = resp.status_code
            
            match resp.status_code:
                case 200:
                    result = FetchResult(resp.text, resp.status_code)
                case 401:
                    result = FetchResult(resp.text, resp.status_code, error_msg="401: Site not Found", success=False)
                case _:
                    result = FetchResult(resp.text, resp.status_code, error_msg=resp.text, success=False)
                
            logger.debug(f"Receiving result from url {url} is sucessful {result.success}. With status code: {result.status_code} and message {result.error_msg}")
                
            return result
                
        except Exception as e:
            result = FetchResult("", 500, str(e), success=False)
            logger.warning(f"✗ Error fetching {url}: {e}")
            return result
    
    def close(self):
        self.session.close()


class WebPageParser:

    def __init__(self, result: FetchResult, orig_url: str, return_format: str = "text"):
        self.result = result
        self.return_format = return_format
        self.orig_url = orig_url
        

    
    def parse(self, soup_ext: Optional[BeautifulSoup] = None, **find_kwargs) -> ParseResult:
        if soup_ext is None:
            soup = BeautifulSoup(self.result.content, "html.parser")
        else:
            soup = soup_ext
        # Remove script and style elements mainly that we do not follow that links
        for script in soup(["script", "style"]):
            script.decompose()
        sub_soup = soup.find(**find_kwargs)
        
        title_tag = self._parse_title_(sub_soup)
        content = self._parse_content(sub_soup)
        links = self._parse_links(sub_soup, self.orig_url)
        return ParseResult(content=content, links=links, title=title_tag)

    #@check_empty_soup
    def _parse_content(self, soup: Any | None) -> str:
        if soup is None:
            return ""
        if self.return_format == "text":
            content = soup.get_text() # type: ignore
        else:
            content = soup.prettify()
        
        lines = (line.strip() for line in content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return ' '.join(chunk for chunk in chunks if chunk)        
        
    
    #@check_empty_soup
    def _parse_title_(self, soup: Any | None):
        if soup is None:
            return None
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else "No title"
    

    #@check_empty_soup
    def _parse_links(self, soup: Any | None, orig_url: str):
        if soup is None:
            return None
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(orig_url, href)
            
            # Only include HTTP/HTTPS links
            if absolute_url.startswith(('http://', 'https://')):
                links.append(absolute_url)
        return links

    



class WebPage:
    
    def __init__(self, url: str, session: Session, content_format="text", **soup_find_kwargs) -> None:
        self.url = url
        self.session = session
        self.soup_find_kwargs = soup_find_kwargs
        self.content_format = content_format
        self.fetch_result: FetchResult = self.session.fetch(self.url)
        self.parser: WebPageParser = WebPageParser(self.fetch_result, self.url, self.content_format)
        self.parse_result: ParseResult =  self.parser.parse(**self.soup_find_kwargs)

    
    def to_dict(self) -> dict:
        """Convert WebPage to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.parse_result.title,
            'content': self.parse_result.content,
            'status_code': self.fetch_result.status_code,
            'links': self.parse_result.links,
            'same_domain_links': self.get_same_domain_links(self.parse_result.links),
            'is_fetched': self.fetch_result.success,
            'error_message': self.fetch_result.error_msg,
            #'content_length': len(self.parse_result.content)
        }
    
    def get_same_domain_links(self, links: List[str] | None) -> List[str]:
        """
        Filter links to only include those from the same domain.
        
        Returns:
            List of URLs from the same domain
        """
        if links is None:
            links = []
        base_domain = urlparse(self.url).netloc
        same_domain_links = []
        
        for link in links:
            if urlparse(link).netloc == base_domain:
                same_domain_links.append(link)
        
        return same_domain_links

    def get_content_preview(self, max_length: int = 200) -> str:
        """
        Get a preview of the page content.
        
        Args:
            max_length: Maximum length of preview text
            
        Returns:
            Truncated content preview
        """
        content = self.parse_result.content
        if content is None:
            content = ""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."





        


# class WebPage:
#     """Represents a single web page with content extraction and link parsing capabilities."""
    
#     def __init__(self, url: str, session: Session, content_format="text", **soup_find_kwargs):
#         """
#         Initialize a WebPage object.
        
#         Args:
#             url: The URL of the web page
#         """
#         self.url = url
#         self.session = session
#         self.content = ""
#         self.title = ""
#         self.links = []
#         self.status_code = None
#         self.is_fetched = False
#         self.error_message = None
#         self.soup_find_kwargs = soup_find_kwargs
#         self.content_format = content_format
    
    
    
#     def _parse_content(self, html: str) -> None:
#         """
#         Parse HTML content and extract text, title, and links.
        
#         Args:
#             html: Raw HTML content
#         """
#         soup = BeautifulSoup(html, 'html.parser')
#         soup = soup.find(**self.soup_find_kwargs)
#         if soup is None:
#             raise ValueError(f"Your soup is empty. Please use another url than {self.url} or refine your soup_find_kwargs {self.soup_find_kwargs}")
#         # Extract title
#         title_tag = soup.find('title')
#         self.title = title_tag.get_text().strip() if title_tag else "No title"
        
#         # Extract clean text content
#         # Remove script and style elements
#         for script in soup(["script", "style"]):
#             script.decompose()
        
#         if self.content_format == "text":
#             self.content = soup.get_text()
#         else:
#             self.content = soup.prettify()
#         # Clean up whitespace
#         lines = (line.strip() for line in self.content.splitlines())
#         chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
#         self.content = ' '.join(chunk for chunk in chunks if chunk)
        
#         # Extract all links
#         self.links = []
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             # Convert relative URLs to absolute URLs
#             absolute_url = urljoin(self.url, href)
            
#             # Only include HTTP/HTTPS links
#             if absolute_url.startswith(('http://', 'https://')):
#                 self.links.append(absolute_url)
    
#     def get_same_domain_links(self) -> List[str]:
#         """
#         Filter links to only include those from the same domain.
        
#         Returns:
#             List of URLs from the same domain
#         """
#         base_domain = urlparse(self.url).netloc
#         same_domain_links = []
        
#         for link in self.links:
#             if urlparse(link).netloc == base_domain:
#                 same_domain_links.append(link)
        
#         return same_domain_links
    
#     def get_summary(self) -> dict:
#         """
#         Get a summary of the web page information.
        
#         Returns:
#             Dictionary containing page summary
#         """
#         return {
#             'url': self.url,
#             'title': self.title,
#             'status_code': self.status_code,
#             'content_length': len(self.content),
#             'links_found': len(self.links),
#             'same_domain_links': len(self.get_same_domain_links()),
#             'is_fetched': self.is_fetched,
#             'error': self.error_message
#         }
    
#     def get_content_preview(self, max_length: int = 200) -> str:
#         """
#         Get a preview of the page content.
        
#         Args:
#             max_length: Maximum length of preview text
            
#         Returns:
#             Truncated content preview
#         """
#         if len(self.content) <= max_length:
#             return self.content
#         return self.content[:max_length] + "..."
    
#     def to_dict(self) -> dict:
#         """Convert WebPage to dictionary for JSON serialization."""
#         return {
#             'url': self.url,
#             'title': self.title,
#             'content': self.content,
#             'status_code': self.status_code,
#             'links': self.links,
#             'same_domain_links': self.get_same_domain_links(),
#             'is_fetched': self.is_fetched,
#             'error_message': self.error_message,
#             'content_length': len(self.content)
#         }
        



def main():
    """Test the WebPage component."""
    # Test with a real website
    test_url = "https://httpbin.org"
    
    print(f"Testing WebPage component with: {test_url}")
    print("-" * 50)
    
    # Create and fetch page
    s = Session()
    page = WebPage(test_url, s)
    success = page.fetch_result.success
    
    if success:
        # Display page information
        summary = page.to_dict()
        print("\nPage Summary:")
        print(f"Title: {summary['title']}")
        print(f"Status: {summary['status_code']}")
        #print(f"Content length: {summary['content_length']} characters")
        print(f"Total links found: {summary['links']}")
        print(f"Same-domain links: {summary['same_domain_links']}")
        
        # Show content preview
        print("\nContent Preview:")
        print(page.get_content_preview())
        
        # Show some links
        print("\nSample Links Found:")
        for i, link in enumerate(page.get_same_domain_links(page.parse_result.links)[:5]):
            print(f"  {i+1}. {link}")
    
    else:
        print(f"Failed to fetch page: {page.fetch_result.error_msg}")


if __name__ == "__main__":
    main()