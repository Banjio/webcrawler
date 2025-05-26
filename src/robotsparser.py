import urllib.robotparser
import urllib.parse
from typing import Optional


class RobotsTxtParser:
    """Handles fetching and parsing robots.txt files to check crawling permissions."""
    
    def __init__(self, base_url: str, user_agent: str = "*"):
        """
        Initialize the robots.txt parser for a given website.
        
        Args:
            base_url: The base URL of the website (e.g., "https://example.com")
            user_agent: User-agent string to use for robots.txt checks
        """
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent
        self.robots_parser = urllib.robotparser.RobotFileParser()
        self.crawl_delay = None
        self.is_loaded = False
    
    def load_robots_txt(self) -> bool:
        """
        Fetch and parse the robots.txt file from the target website.
        
        Returns:
            True if robots.txt was successfully loaded, False otherwise
        """
        try:
            robots_url = f"{self.base_url}/robots.txt"
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            
            # Extract crawl delay if specified
            self.crawl_delay = self.robots_parser.crawl_delay(self.user_agent)
            self.is_loaded = True
            
            print(f"✓ Loaded robots.txt from {robots_url}")
            if self.crawl_delay:
                print(f"✓ Crawl delay: {self.crawl_delay} seconds")
            
            return True
            
        except Exception as e:
            print(f"⚠ Could not load robots.txt: {e}")
            print("⚠ Proceeding with caution (assuming no restrictions)")
            self.is_loaded = False
            return False
    
    def can_fetch(self, url: str) -> bool:
        """
        Check if the given URL can be fetched according to robots.txt rules.
        
        Args:
            url: The URL to check
            
        Returns:
            True if URL can be fetched, False otherwise
        """
        if not self.is_loaded:
            # If robots.txt couldn't be loaded, be conservative but allow crawling
            return True
        
        return self.robots_parser.can_fetch(self.user_agent, url)
    
    def get_crawl_delay(self) -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt.
        
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        return self.crawl_delay


def main():
    """Test the RobotsTxtParser component."""
    # Test with a real website
    base_url = "https://httpbin.org"
    parser = RobotsTxtParser(base_url)
    
    # Load robots.txt
    parser.load_robots_txt()
    
    # Test some URLs
    test_urls = [
        f"{base_url}/get",
        f"{base_url}/post",
        f"{base_url}/status/200"
    ]
    
    print("\n--- Testing URL permissions ---")
    for url in test_urls:
        can_fetch = parser.can_fetch(url)
        status = "✓ Allowed" if can_fetch else "✗ Blocked"
        print(f"{status}: {url}")
    
    # Show crawl delay
    delay = parser.get_crawl_delay()
    if delay:
        print(f"\nCrawl delay: {delay} seconds")
    else:
        print("\nNo crawl delay specified")


if __name__ == "__main__":
    main()