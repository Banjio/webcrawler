from urllib.parse import urlparse
import json
import click
import sys

from webcrawler import WebCrawler

@click.command()
@click.argument('url')
@click.option('--max-time', '-t', default=60, help='Maximum crawling time in seconds (default: 60)')
@click.option('--max-depth', '-d', default=2, help='Maximum crawling depth (default: 2)')
@click.option('--filter', '-f', 'filter_keyword', help='Filter results by keyword')
@click.option('--output', '-o', help='Output file path (default: stdout)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
def crawl(url, max_time, max_depth, filter_keyword, output, quiet):
    """
    Web crawler CLI tool that respects robots.txt and outputs JSON results.
    
    URL: The starting URL to crawl from
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            click.echo("❌ Invalid URL. Please include http:// or https://", err=True)
            sys.exit(1)
        
        if not quiet:
            click.echo("🔍 Web Crawler v1.0")
            click.echo(f"🌐 Target: {url}")
            click.echo(f"⏰ Max time: {max_time}s")
            click.echo(f"📏 Max depth: {max_depth}")
            if filter_keyword:
                click.echo(f"🔎 Filter: '{filter_keyword}'")
            click.echo()
        
        # Create and run crawler
        crawler = WebCrawler(url, max_depth=max_depth, max_time=max_time, verbose=not quiet)
        results = crawler.crawl()
        
        # Apply filtering if requested
        if filter_keyword:
            results = crawler.filter_content(results, filter_keyword)
            if not quiet:
                click.echo(f"\n🔎 Filtered results for keyword: '{filter_keyword}'")
                click.echo(f"📄 Matching pages: {results['crawl_metadata'].get('filtered_pages', 0)}")
        
        # Output results
        json_output = json.dumps(results, indent=2, ensure_ascii=False)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            if not quiet:
                click.echo(f"\n💾 Results saved to: {output}")
        else:
            click.echo("\n" + "=" * 60)
            click.echo("📋 JSON RESULTS")
            click.echo("=" * 60)
            click.echo(json_output)
    
    except KeyboardInterrupt:
        click.echo("\n\n⚠️ Crawling interrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    crawl()


    