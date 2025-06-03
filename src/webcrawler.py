from urllib.parse import urlparse
from typing import Callable, List, Optional, Set, Dict, Any
import time
import re
import click
import dill
from requests import session


from robotsparser import RobotsTxtParser
from webpage import Session, WebPage


class WebCrawler:
    """Main web crawler that orchestrates the crawling process with depth-first traversal."""

    def __init__(
        self,
        start_url: str,
        max_depth: int = 2,
        max_time: int = 300,
        verbose: bool = True,
        only_sub_links: bool = True,
        custom_depth_func: Optional[Callable] = None,
        **soup_find_kwargs,
    ):
        """_summary_

        Args:
            start_url (str): _description_
            max_depth (int, optional): _description_. Defaults to 2.
            max_time (int, optional): _description_. Defaults to 300.
            verbose (bool, optional): _description_. Defaults to True.
            only_sub_links (bool, optional): For true no links are crawled that are above the starter url in hierachy, e.g.
            https://test_url/ is ignored if the start_url is https://test_url/1, whereas https://test_url/1/2 is included. Defaults to True.
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_time = max_time
        self.verbose = verbose
        self.base_domain = urlparse(start_url).netloc
        self.soup_find_kwargs = soup_find_kwargs
        self.only_sub_links = only_sub_links
        self.custom_depth_func = custom_depth_func

        # Initialize components
        base_url = f"{urlparse(start_url).scheme}://{self.base_domain}"
        self.robots_parser = RobotsTxtParser(base_url)

        # Crawling state
        self.visited_urls: Set[str] = set()
        self.crawled_pages: Dict[str, WebPage] = {}
        self.crawl_stack: List[tuple] = []
        self.start_time = None
        self.is_time_exceeded = False
        self.blocked_urls: List[str] = []
        self.failed_urls: List[str] = []

    def crawl(self) -> Dict[str, Any]:
        """
        Start the crawling process using depth-first traversal.

        Returns:
            Dictionary containing crawling results and metadata
        """
        if self.verbose:
            click.echo(f"🚀 Starting crawler for: {self.start_url}")
            click.echo(f"📊 Max depth: {self.max_depth}, Max time: {self.max_time}s")
            click.echo("=" * 60)

        # Initialize
        self.start_time = time.time()
        self.robots_parser.load_robots_txt()
        crawl_delay = self.robots_parser.get_crawl_delay() or 1.0

        if self.custom_depth_func is not None:
            depth_start = self.custom_depth_func(self.start_url)
        else:
            depth_start = 0

        # Add starting URL to stack
        self.crawl_stack.append((self.start_url, depth_start))

        # Depth-first crawling
        while self.crawl_stack and not self._is_time_exceeded():
            current_url, depth = self.crawl_stack.pop()

            if current_url in self.visited_urls or depth > self.max_depth:
                continue

            if self.only_sub_links:
                if self.start_url not in current_url:
                    continue

            # Check robots.txt permission
            if not self.robots_parser.can_fetch(current_url):
                if self.verbose:
                    click.echo(f"🚫 Blocked by robots.txt: {current_url}")
                self.blocked_urls.append(current_url)
                self.visited_urls.add(current_url)
                continue

            # Crawl the page
            success = self._crawl_page(current_url, depth)

            if success and depth < self.max_depth:
                page = self.crawled_pages[current_url]
                child_links = page.get_same_domain_links(page.parse_result.links)

                for link in reversed(child_links):
                    if link not in self.visited_urls:
                        if self.custom_depth_func is not None:
                            click.echo(f"    DEBUG: Adding link {link} to crawl stack")
                            depth_current = self.custom_depth_func(link)
                        else:
                            depth_current = depth + 1
                        self.crawl_stack.append((link, depth_current))

            # Respect crawl delay
            if crawl_delay and not self._is_time_exceeded():
                time.sleep(crawl_delay)

        return self._generate_results()

    def _crawl_page(self, url: str, depth: int) -> bool:
        if self.verbose:
            elapsed = time.time() - self.start_time
            click.echo(f"[{elapsed:.1f}s] Depth {depth}: Crawling {url}")

        self.visited_urls.add(url)
        s = Session()
        page = WebPage(url, s, content_format="html", **self.soup_find_kwargs)
        success = page.fetch_result.success

        if success:
            self.crawled_pages[url] = page
            if self.verbose:
                click.echo(f"    ✓ Title: {page.parse_result.title}")
                click.echo(
                    f"    ✓ Content: {len(page.parse_result.content)} chars, {len(page.get_same_domain_links(page.parse_result.links))} links"
                )
        else:
            self.failed_urls.append(url)
            if self.verbose:
                click.echo(f"    ✗ Failed: {page.fetch_result.error_msg}")

        return success

    def _is_time_exceeded(self) -> bool:
        if self.start_time is None:
            return False

        elapsed = time.time() - self.start_time
        if elapsed >= self.max_time:
            if not self.is_time_exceeded:
                if self.verbose:
                    click.echo(
                        f"\n⏰ Time limit exceeded ({elapsed:.1f}s >= {self.max_time}s)"
                    )
                self.is_time_exceeded = True
            return True
        return False

    def _generate_results(self) -> Dict[str, Any]:
        """Generate final results dictionary for JSON output."""
        elapsed = time.time() - self.start_time

        results = {
            "crawl_metadata": {
                "start_url": self.start_url,
                "max_depth": self.max_depth,
                "max_time": self.max_time,
                "total_time": round(elapsed, 2),
                "pages_crawled": len(self.crawled_pages),
                "urls_visited": len(self.visited_urls),
                "urls_blocked": len(self.blocked_urls),
                "urls_failed": len(self.failed_urls),
                "time_exceeded": self.is_time_exceeded,
                "crawl_delay_used": self.robots_parser.get_crawl_delay(),
            },
            "pages": {},
            "blocked_urls": self.blocked_urls,
            "failed_urls": self.failed_urls,
        }

        # Add page data
        for url, page in self.crawled_pages.items():
            results["pages"][url] = page.to_dict()

        if self.verbose:
            self._print_summary(results["crawl_metadata"])

        return results

    def _print_summary(self, metadata: dict) -> None:
        click.echo("\n" + "=" * 60)
        click.echo("📈 CRAWLING SUMMARY")
        click.echo("=" * 60)
        click.echo(f"⏱️  Total time: {metadata['total_time']} seconds")
        click.echo(f"📄 Pages crawled: {metadata['pages_crawled']}")
        click.echo(f"🔗 URLs visited: {metadata['urls_visited']}")
        click.echo(f"🚫 URLs blocked: {metadata['urls_blocked']}")
        click.echo(f"❌ URLs failed: {metadata['urls_failed']}")

        if metadata["urls_visited"] > 0:
            success_rate = (metadata["pages_crawled"] / metadata["urls_visited"]) * 100
            click.echo(f"🎯 Success rate: {success_rate:.1f}%")

        if metadata["time_exceeded"]:
            click.echo(f"⏰ Stopped due to time limit ({metadata['max_time']}s)")

    def filter_content(self, results: dict, keyword: str) -> dict:
        """Filter results by keyword."""
        filtered_results = {
            "crawl_metadata": results["crawl_metadata"].copy(),
            "pages": {},
            "blocked_urls": results["blocked_urls"],
            "failed_urls": results["failed_urls"],
        }

        keyword_lower = keyword.lower()
        matched_pages = 0

        for url, page_data in results["pages"].items():
            content_match = keyword_lower in page_data["content"].lower()
            title_match = keyword_lower in page_data["title"].lower()

            if content_match or title_match:
                filtered_results["pages"][url] = page_data
                matched_pages += 1

        # Update metadata
        filtered_results["crawl_metadata"]["filter_keyword"] = keyword
        filtered_results["crawl_metadata"]["filtered_pages"] = matched_pages

        return filtered_results


def depth_by_hs_code(url: str) -> int:
    hscode = url.split("/")[-1]
    click.echo(f"    DEBUG: Hscode {hscode} with len {len(hscode)}")
    if hscode in ("2025", "2024", "2023", "2022", "2021", "2020"):
        return 0
    elif len(hscode) <= 2:
        return 1
    elif len(hscode) <= 4:
        return 2
    elif len(hscode) <= 6:
        return 3
    else:
        return 4


def main(db_year: int):
    """Test the WebCrawler with depth-first traversal."""
    # Test crawling
    
    start_url = f"https://www.tariffnumber.com/{db_year}"

    # start_url = "https://www.tariffnumber.com/2025/020760"
    max_time = 6000  # 30 seconds limit for testing

    print(f"Testing WebCrawler with {start_url}")
    print(f"Time limit: {max_time} seconds")

    # Create and run crawler
    soup_find_kwargs = {"name": "main", "attrs": {"id": "main"}}
    crawler = WebCrawler(
        start_url,
        max_depth=2,
        max_time=max_time,
        custom_depth_func=depth_by_hs_code,
        **soup_find_kwargs,
    )
    crawled_pages = crawler.crawl()

    # Show results
    if crawled_pages:
        print("\n📝 Content preview from first page:")
        first_page = list(crawled_pages.values())[0]
        # print(first_page.content[:300] + "..." if lenfirst_page.content) > 300 else first_page.content)
        print(list(crawled_pages["pages"].values())[-1]["content"])

    with open(f"./tmp/result_crawling_{max_time}_seconds_{db_year}.pickle", "wb") as f:
        dill.dump(crawled_pages, f)


if __name__ == "__main__":
    year = int(input("Enter year of codes to crawl (From 2025-2020):"))
    if year < 2020:
        raise ValueError("Only years > 2019 are supported for crawling")
    main(year)
