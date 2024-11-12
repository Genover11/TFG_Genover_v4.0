"""Console script for ArnauGenover_TFG."""
import ArnauGenover_TFG

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for ArnauGenover_TFG."""
    console.print("Replace this message by putting your code into "
               "ArnauGenover_TFG.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    


if __name__ == "__main__":
    app()
