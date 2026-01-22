import json
import os
import io
import sys
import re
import shlex
import ctypes
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

import requests
import typer
from rich.console import Console
from rich.table import Table

# Autocompletion
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style

# --- Configuration & Globals ---

if sys.platform == "darwin":
    cairo_lib = None
    lib_paths = [
        "/opt/homebrew/lib/libcairo.2.dylib", 
        "/usr/local/lib/libcairo.2.dylib",
        "/opt/homebrew/lib/libcairo.dylib"
    ]
    for lib_path in lib_paths:
        if os.path.exists(lib_path):
            try:
                cairo_lib = ctypes.CDLL(lib_path)
                break
            except OSError:
                pass

try:
    import cairosvg
except (ImportError, OSError):
    cairosvg = None

try:
    from PIL import Image
except ImportError:
    Image = None

app = typer.Typer(name="simple-icons", help="CLI for Simple Icons", add_completion=False)
console = Console()
err_console = Console(stderr=True)

DATA_URL = "https://unpkg.com/simple-icons/data/simple-icons.json"
CDN_URL = "https://cdn.simpleicons.org"
CACHE_PATH = Path.home() / ".cache" / "simple-icons-cli"
CACHE_FILE = CACHE_PATH / "data.json"

state = {"streamline": False}

# --- Helpers ---

@contextmanager
def task_status(message: str):
    if state["streamline"]:
        yield
    else:
        with console.status(message):
            yield

def get_data():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except:
            pass
            
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    with task_status("[bold green]Fetching icon data..."):
        try:
            response = requests.get(DATA_URL)
            response.raise_for_status()
            data = response.json()
            CACHE_FILE.write_text(json.dumps(data))
            return data
        except Exception as e:
            err_console.print(f"[red]Error fetching data: {e}[/red]")
            sys.exit(1)

def resolve_icon(query: str, icons: list) -> Optional[dict]:
    """Finds an icon by slug, allowing for fuzzy matching."""
    # 1. Exact match
    for icon in icons:
        if icon["slug"] == query:
            return icon
            
    # 2. Fuzzy match
    slugs = [i["slug"] for i in icons]
    match = process.extractOne(query, slugs, scorer=fuzz.ratio)
    
    if match:
        best_slug, score, index = match
        if score >= 60: # Threshold
            # Notify user of the correction
            if not state["streamline"]:
                console.print(f"[yellow]'{query}' not found. Did you mean [bold]{best_slug}[/bold]? (Score: {score:.1f})[/yellow]")
            
            # Find the full icon object for this slug
            return next((i for i in icons if i["slug"] == best_slug), None)
            
    return None

# --- Commands ---

@app.command()
def search(query: str = typer.Argument(..., help="Search query (title or slug)")):
    """Search for icons."""
    icons = get_data()
    results = []
    query = query.lower()
    
    for icon in icons:
        if query in icon["title"].lower() or query in icon["slug"].lower():
            results.append(icon)

    if not results:
        if not state["streamline"]:
            console.print(f"[red]No icons found for '{query}'[/red]")
        return

    if state["streamline"]:
        for icon in results:
            print(icon["slug"])
    else:
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Title", style="cyan")
        table.add_column("Slug", style="magenta")
        table.add_column("Hex", style="green")
        for item in results[:25]:
            table.add_row(item["title"], item["slug"], f"#{item['hex']}")
        console.print(table)
        if len(results) > 25:
            console.print(f"[dim]...and {len(results) - 25} more.[/dim]")

@app.command()
def info(slug: str = typer.Argument(..., help="Icon slug")):
    """Show detailed information about an icon."""
    icons = get_data()
    icon = resolve_icon(slug, icons)
    
    if not icon:
        err_console.print(f"[red]Icon '{slug}' not found (even with fuzzy search).[/red]")
        sys.exit(1)
    
    if state["streamline"]:
        print(f"title: {icon['title']}")
        print(f"slug: {icon['slug']}")
        print(f"hex: {icon['hex']}")
    else:
        console.print(f"[bold cyan]{icon['title']}[/bold cyan]")
        console.print(f"Slug: [magenta]{icon['slug']}[/magenta]")
        console.print(f"Hex: [green]#{icon['hex']}[/green]")
        console.print(f"Source: [blue]{icon['source']}[/blue]")

@app.command()
def download(
    slug: str = typer.Argument(..., help="Icon slug"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file or directory"),
    color: Optional[str] = typer.Option(None, "--color", "-c", help="Hex color (without #)"),
    invert: bool = typer.Option(False, "--invert", "-i", help="Invert the color (e.g. Black -> White)."),
    opacity: float = typer.Option(1.0, "--opacity", help="Opacity (0.0 to 1.0)."),
    background: Optional[str] = typer.Option(None, "--background", "-bg", help="Background color (removes transparency)."),
    format: str = typer.Option("svg", "--format", "-f", help="Output format"),
    size: int = typer.Option(256, "--size", "-s", help="Size in pixels"),
):
    """Download and optionally convert an icon."""
    
    icons = get_data()
    icon_data = resolve_icon(slug, icons)
    
    if not icon_data:
        err_console.print(f"[red]Icon '{slug}' not found.[/red]")
        sys.exit(1)
        
    # Update slug to the real one found via fuzzy match
    slug = icon_data["slug"]
    
    # 1. Resolve Color
    target_hex = None
    
    # If explicit color or invert is requested, we need to calculate the hex
    if color or invert:
        if color:
            hex_str = color.lstrip('#')
        else:
            hex_str = icon_data["hex"]

        if invert:
            # Invert hex
            val = int(hex_str, 16)
            inverted_val = 0xFFFFFF ^ val
            target_hex = f"{inverted_val:06X}"
        else:
            target_hex = hex_str

    # 2. Construct URL
    url = f"{CDN_URL}/{slug}"
    if target_hex:
        url += f"/{target_hex}"
    
    # 3. Resolve Format
    format = format.lower()
    if output and not output.is_dir() and output.suffix:
        format = output.suffix.lower().lstrip(".")

    if format != "svg" and (cairosvg is None or Image is None):
        err_console.print("[red]Error: cairo and pillow required for conversion.[/red]")
        sys.exit(1)

    filename = f"{slug}.{format}"
    target = output / filename if output and output.is_dir() else (output or Path(filename))

    with task_status(f"Downloading {slug}..."):
        response = requests.get(url)
        if response.status_code == 404:
            err_console.print(f"[red]Icon '{slug}' not found.[/red]")
            sys.exit(1)
        response.raise_for_status()
        svg_content = response.content

    # 4. Apply Opacity (SVG manipulation)
    if opacity < 1.0:
        svg_text = svg_content.decode("utf-8")
        # Inject opacity into the root svg tag
        # Simple regex to add opacity attribute. 
        # Note: If viewBox exists, we append after it, otherwise after <svg
        if "opacity=" in svg_text:
             svg_text = re.sub(r'opacity="[\d\.]+"', f'opacity="{opacity}"', svg_text)
        else:
             svg_text = re.sub(r'<svg', f'<svg opacity="{opacity}"', svg_text)
        svg_content = svg_text.encode("utf-8")

    try:
        if format == "svg":
            # If background is requested for SVG, we wrap in a group and add a rect
            # This is complex XML manipulation, simplified here:
            if background:
                # Basic SVG background injection could go here, but it's often cleaner in design tools.
                # For CLI, we'll warn or skip. Let's skip for SVG to keep it simple or implement if critical.
                pass 
            target.write_bytes(svg_content)
        else:
            with task_status(f"Converting to {format}..."):
                convert_image(svg_content, target, format, size, background)
        
        print(f"exported {target.name}")
        
    except Exception as e:
        err_console.print(f"[red]Failed: {e}[/red]")
        sys.exit(1)

def convert_image(svg_content, target, format, size, background=None):
    # If background provided, clean hex
    bg_color = None
    if background:
        h = background.lstrip('#')
        # Convert hex to RGB tuple for Pillow
        bg_color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    if format == "png":
        png_data = cairosvg.svg2png(bytestring=svg_content, output_width=size, output_height=size)
        if bg_color:
            image = Image.open(io.BytesIO(png_data))
            # Create solid background
            bg = Image.new("RGBA", image.size, bg_color + (255,))
            # Paste icon using itself as mask
            bg.alpha_composite(image)
            bg.save(target, "PNG")
        else:
            with open(target, "wb") as f:
                f.write(png_data)

    elif format == "ico":
        png_data = cairosvg.svg2png(bytestring=svg_content, output_width=size, output_height=size)
        image = Image.open(io.BytesIO(png_data))
        if bg_color:
            bg = Image.new("RGBA", image.size, bg_color + (255,))
            bg.alpha_composite(image)
            image = bg
        image.save(target, format="ICO")

    elif format == "jpg":
        # JPG does not support transparency, so we MUST have a background.
        # Default to White if not provided.
        if not bg_color:
            bg_color = (255, 255, 255)
            
        png_data = cairosvg.svg2png(bytestring=svg_content, output_width=size, output_height=size)
        image = Image.open(io.BytesIO(png_data))
        bg = Image.new("RGB", image.size, bg_color)
        if image.mode == 'RGBA':
            bg.paste(image, mask=image.split()[3])
        else:
            bg.paste(image)
        bg.save(target, "JPEG")

    elif format == "icns":
        with tempfile.TemporaryDirectory() as temp_dir:
            iconset = Path(temp_dir) / "icon.iconset"
            iconset.mkdir()
            for s in [16, 32, 128, 256, 512]:
                png_data = cairosvg.svg2png(bytestring=svg_content, output_width=s, output_height=s)
                
                # Apply background if needed
                if bg_color:
                    img = Image.open(io.BytesIO(png_data))
                    bg = Image.new("RGBA", img.size, bg_color + (255,))
                    bg.alpha_composite(img)
                    # Save back to bytes for write
                    buf = io.BytesIO()
                    bg.save(buf, format="PNG")
                    png_data = buf.getvalue()
                
                (iconset/f"icon_{s}x{s}.png").write_bytes(png_data)
                
                # For @2x (simulated upscale if source is vector, simply render larger)
                png_data_2x = cairosvg.svg2png(bytestring=svg_content, output_width=s*2, output_height=s*2)
                if bg_color:
                    img = Image.open(io.BytesIO(png_data_2x))
                    bg = Image.new("RGBA", img.size, bg_color + (255,))
                    bg.alpha_composite(img)
                    buf = io.BytesIO()
                    bg.save(buf, format="PNG")
                    png_data_2x = buf.getvalue()

                (iconset/f"icon_{s}x{s}@2x.png").write_bytes(png_data_2x)

            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(target)], check=True)
    else:
        # Fallback basic
        cairosvg.svg2png(bytestring=svg_content, write_to=str(target), output_width=size, output_height=size)

# --- REPL ---

from prompt_toolkit.formatted_text import HTML

from rapidfuzz import process, fuzz

def interactive_shell():
    console.print("[bold yellow]Simple Icons Shell[/bold yellow]")
    console.print("[dim]Type [bold]help[/bold] to see available commands or [bold]exit[/bold] to quit.[/dim]")
    
    slugs = []
    try:
        if CACHE_FILE.exists():
             data = json.loads(CACHE_FILE.read_text())
             slugs = [icon["slug"] for icon in data]
    except:
        pass

    slug_commands = {s: None for s in slugs}
    
    completer_dict = {
        "search": None,
        "info": slug_commands,
        "download": slug_commands,
        "help": None,
        "exit": None,
        "quit": None,
        "clear": None,
        "cls": None
    }
    
    completer = NestedCompleter.from_nested_dict(completer_dict)
    
    # Enhanced Styling
    style = Style.from_dict({
        # Prompt
        'p-icon': '#00ff00 bold',   # Green icon
        'p-name': '#00ffff bold',   # Cyan name
        'p-arrow': '#888888',       # Gray arrow
        
        # Completion Menu
        'completion-menu': 'bg:#222222 #eeeeee', 
        'completion-menu.completion': 'bg:#222222 #eeeeee',
        'completion-menu.completion.current': 'bg:#00aaaa #000000 bold', # Cyan bg, black text for selected
        'scrollbar.background': 'bg:#222222',
        'scrollbar.button': 'bg:#444444',
        
        # Toolbar
        'bottom-toolbar': 'bg:#333333 #ffffff',
        'bottom-toolbar.key': '#ff00ff bold', # Magenta keys
    })

    def get_toolbar():
        return HTML(' <b>TAB</b> Autocomplete  |  <b>UP/DOWN</b> History  |  <b>CTRL+D</b> Exit ')

    session = PromptSession(completer=completer, style=style)

    while True:
        try:
            # Rich, multicolored prompt
            prompt_fragments = [
                ('class:p-icon', '🚀 '),
                ('class:p-name', 'simple-icons'),
                ('class:p-arrow', ' > '),
            ]
            
            cmd = session.prompt(
                prompt_fragments, 
                bottom_toolbar=get_toolbar
            )
            cmd = cmd.strip()
            
            if not cmd: continue
            if cmd.lower() in ["exit", "quit", "q"]: break
            
            if cmd.lower() in ["clear", "cls"]:
                os.system('clear' if os.name != 'nt' else 'cls')
                continue
            
            if cmd.lower() in ["/help", "?", "h"]:
                cmd = "--help"
            
            args = shlex.split(cmd)
            if args and args[0].lower() == "help":
                args = ["--help"]
                
            app(args, standalone_mode=False)
            
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

@app.callback(invoke_without_command=True)
def cli_root(
    ctx: typer.Context,
    streamline: bool = typer.Option(False, "--streamline", "-s", help="Clean output for scripting."),
):
    state["streamline"] = streamline
    if ctx.invoked_subcommand is None:
        interactive_shell()

def main():
    app()

if __name__ == "__main__":
    main()