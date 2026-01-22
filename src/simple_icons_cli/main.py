import json
import os
import io
import sys
from pathlib import Path
from typing import Optional
import requests
import typer
from rich.console import Console
from rich.table import Table

# Try to import cairosvg safely
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg = None

# Try to import PIL safely
try:
    from PIL import Image
except ImportError:
    Image = None

app = typer.Typer(name="simple-icons", help="CLI for Simple Icons")
console = Console()

DATA_URL = "https://unpkg.com/simple-icons/data/simple-icons.json"
CDN_URL = "https://cdn.simpleicons.org"
CACHE_PATH = Path.home() / ".cache" / "simple-icons-cli"
CACHE_FILE = CACHE_PATH / "data.json"

def get_data():
    """Fetch icon data with local caching."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except:
            pass
            
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    with console.status("[bold green]Fetching icon data..."):
        response = requests.get(DATA_URL)
        response.raise_for_status()
        data = response.json()
        CACHE_FILE.write_text(json.dumps(data))
        return data

@app.command()
def search(query: str = typer.Argument(..., help="Search query (title or slug)")):
    """Search for icons."""
    icons = get_data()
    results = []
    query = query.lower()
    
    for icon in icons:
        title = icon["title"]
        slug = icon["slug"]
        hex_code = icon["hex"]
        
        if query in title.lower() or query in slug.lower():
            results.append((title, slug, hex_code))

    if not results:
        console.print(f"[red]No icons found for '{query}'[/red]")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Title", style="cyan")
    table.add_column("Slug", style="magenta")
    table.add_column("Hex", style="green")

    for title, slug, hex_code in results[:25]:
        table.add_row(title, slug, f"#{hex_code}")

    console.print(table)
    if len(results) > 25:
        console.print(f"[dim]...and {len(results) - 25} more. Try a more specific query.[/dim]")

@app.command()
def download(
    slug: str = typer.Argument(..., help="Icon slug"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file or directory"),
    color: Optional[str] = typer.Option(None, "--color", "-c", help="Hex color (without #)"),
    format: str = typer.Option("svg", "--format", "-f", help="Output format (svg, png, jpg, pdf)"),
    size: int = typer.Option(256, "--size", "-s", help="Size in pixels (for raster formats)"),
):
    """Download an icon (and optionally convert it)."""
    url = f"{CDN_URL}/{slug}"
    if color:
        url += f"/{color.lstrip('#')}"
    
    format = format.lower()
    
    # Infer format from output extension
    if output and not output.is_dir() and output.suffix:
        ext = output.suffix.lower().lstrip(".")
        if ext in ["svg", "png", "jpg", "jpeg", "pdf"]:
            format = ext.replace("jpeg", "jpg")

    if format != "svg" and (cairosvg is None or Image is None):
        console.print("[red]Error: 'cairosvg' could not be loaded.[/red]")
        if sys.platform == "darwin":
             console.print("[yellow]Tip: If you installed cairo via Homebrew, try running:[/yellow]")
             console.print("[bold]export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH[/bold]")
        raise typer.Exit(code=1)

    filename = f"{slug}.{format}"
    
    if output is None:
        target = Path(filename)
    elif output.is_dir():
        target = output / filename
    else:
        target = output

    with console.status(f"[bold green]Downloading {slug}..."):
        response = requests.get(url)
        if response.status_code == 404:
            console.print(f"[red]Icon '{slug}' not found.[/red]")
            return
        response.raise_for_status()
        svg_content = response.content

    if format == "svg":
        target.write_bytes(svg_content)
        console.print(f"[green]Successfully downloaded {slug} to [bold]{target}[/bold][/green]")
        return

    # Conversion logic
    with console.status(f"[bold blue]Converting to {format}..."):
        try:
            if format == "png":
                cairosvg.svg2png(bytestring=svg_content, write_to=str(target), output_width=size, output_height=size)
            elif format == "pdf":
                cairosvg.svg2pdf(bytestring=svg_content, write_to=str(target), output_width=size, output_height=size)
            elif format == "jpg":
                png_data = cairosvg.svg2png(bytestring=svg_content, output_width=size, output_height=size)
                image = Image.open(io.BytesIO(png_data))
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    bg.paste(image, mask=image.split()[3])
                else:
                    bg.paste(image)
                bg.save(target, "JPEG")
            else:
                console.print(f"[red]Unsupported format: {format}[/red]")
                return
                
        except Exception as e:
            console.print(f"[red]Conversion failed: {e}[/red]")
            if "cairo" in str(e).lower() or "dlopen" in str(e).lower():
                 console.print("[yellow]Tip: Install libcairo: `brew install cairo`[/yellow]")
            raise typer.Exit(code=1)

    console.print(f"[green]Successfully saved to [bold]{target}[/bold][/green]")

@app.command()
def info(slug: str = typer.Argument(..., help="Icon slug")):
    """Show detailed information about an icon."""
    icons = get_data()
    icon = next((i for i in icons if i["slug"] == slug), None)
    
    if not icon:
        console.print(f"[red]Icon '{slug}' not found.[/red]")
        return
        
    console.print(f"[bold cyan]{icon['title']}[/bold cyan]")
    console.print(f"Slug: [magenta]{icon['slug']}[/magenta]")
    console.print(f"Hex: [green]#{icon['hex']}[/green]")
    console.print(f"Source: [blue]{icon['source']}[/blue]")
    if "guidelines" in icon:
        console.print(f"Guidelines: [blue]{icon['guidelines']}[/blue]")
    if "license" in icon:
        license_data = icon['license']
        l_type = license_data.get('type') if isinstance(license_data, dict) else license_data
        l_url = license_data.get('url') if isinstance(license_data, dict) else "N/A"
        console.print(f"License: {l_type} ({l_url})")

def main():
    app()

if __name__ == "__main__":
    main()
