"""
Command Line Interface for Ethopy Analysis package.
"""

import click
import sys
import os
from datetime import datetime

from .plots.animal import (
    plot_session_date,
    plot_performance_liquid,
    plot_session_performance,
    plot_trial_per_session,
)
from .db.schemas import get_schema
from .data.analysis import get_performance
from .data.loaders import get_sessions
from .config.settings import get_config_summary, DEFAULT_CONFIG, save_config


@click.group()
@click.version_option()
def main():
    """Ethopy Analysis CLI - Analyze behavioral data from Ethopy experiments."""
    pass


@main.command()
@click.option(
    "--animal-id",
    type=int,
    required=True,
    help="Animal ID to analyze",
)
@click.option(
    "--save-plots",
    is_flag=True,
    help="Save plots to specified directory",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default="./plots",
    help="Output directory for saved plots (default: ./plots)",
)
@click.option(
    "--min-trials",
    type=int,
    default=2,
    help="Minimum number of trials per session (default: 2)",
)
def analyze_animal(animal_id: int, save_plots: bool, output_dir: str, min_trials: int):
    """Generate comprehensive analysis plots for an animal."""
    try:
        # Create output directory if saving plots
        if save_plots:
            os.makedirs(output_dir, exist_ok=True)
            click.echo(f"Saving plots to: {output_dir}")

        # Get sessions for the animal
        sessions = get_sessions(animal_id, min_trials=min_trials)
        if sessions.empty:
            click.echo(
                f"No sessions found for animal {animal_id} with min_trials={min_trials}"
            )
            return

        click.echo(f"Analyzing animal {animal_id} with {len(sessions)} sessions...")

        # Generate plots
        plot_funcs = [
            ("session_dates", lambda: plot_session_date(animal_id, min_trials)),
            (
                "performance_liquid",
                lambda: plot_performance_liquid(animal_id, sessions),
            ),
            (
                "session_performance",
                lambda: plot_session_performance(
                    animal_id, sessions["session"].values, get_performance
                ),
            ),
            (
                "trials_per_session",
                lambda: plot_trial_per_session(animal_id, min_trials),
            ),
        ]

        for plot_name, plot_func in plot_funcs:
            try:
                click.echo(f"Generating {plot_name} plot...")
                plot_func()

                if save_plots:
                    # Save using matplotlib's savefig since we need to handle the current figure
                    import matplotlib.pyplot as plt

                    save_path = os.path.join(
                        output_dir, f"animal_{animal_id}_{plot_name}.png"
                    )
                    plt.savefig(save_path, dpi=300, bbox_inches="tight")
                    click.echo(f"  Saved: {save_path}")
                else:
                    import matplotlib.pyplot as plt

                    plt.show()

            except Exception as e:
                click.echo(f"Error generating {plot_name}: {str(e)}", err=True)

        click.echo(f"Analysis complete for animal {animal_id}")

    except Exception as e:
        click.echo(f"Error analyzing animal {animal_id}: {str(e)}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--animal-id",
    type=int,
    required=True,
    help="Animal ID to generate report for",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default="./reports",
    help="Output directory for report (default: ./reports)",
)
def generate_report(animal_id: int, output_dir: str):
    """Generate a comprehensive analysis report for an animal."""
    try:
        os.makedirs(output_dir, exist_ok=True)

        click.echo(f"Generating comprehensive report for animal {animal_id}...")

        # Get basic info
        sessions = get_sessions(animal_id, min_trials=2)
        if sessions.empty:
            click.echo(f"No sessions found for animal {animal_id}")
            return

        report_file = os.path.join(output_dir, f"animal_{animal_id}_report.txt")

        with open(report_file, "w") as f:
            f.write("ETHOPY ANALYSIS REPORT\n")
            f.write(f"Animal ID: {animal_id}\n")
            f.write("Generated: {}\n".format(datetime.now())) 
            f.write("=" * 50 + "\n\n")

            f.write("SESSION SUMMARY\n")
            f.write(f"Total sessions: {len(sessions)}\n")
            f.write(
                f"Session range: {sessions['session'].min()} - {sessions['session'].max()}\n\n"
            )

            # Add session details
            for _, session_row in sessions.iterrows():
                f.write(f"Session {session_row['session']}:\n")
                f.write(f"  Trials: {session_row['trials_count']}\n")
                performance = get_performance(animal_id, session_row["session"])
                if performance is None:
                    f.write("  Performance: no behavior in this session\n")
                else:
                    f.write(f"  Performance: {performance:.3f}\n")
                f.write(f"  Date: {session_row['session_tmst']}\n\n")

        # Generate and save all plots
        plot_dir = os.path.join(output_dir, f"animal_{animal_id}_plots")
        os.makedirs(plot_dir, exist_ok=True)

        # Use the analyze_animal functionality to generate plots
        from click.testing import CliRunner

        runner = CliRunner()
        runner.invoke(
            analyze_animal,
            ["--animal-id", str(animal_id), "--save-plots", "--output-dir", plot_dir],
        )

        click.echo(f"Report generated: {report_file}")
        click.echo(f"Plots saved to: {plot_dir}")

    except Exception as e:
        click.echo(f"Error generating report: {str(e)}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--animal-id",
    "-a",
    type=int,
    required=True,
    help="Animal ID",
)
@click.option(
    "--session",
    "-s",
    type=int,
    required=True,
    help="Session number",
)
def session_summary(animal_id: int, session: int):
    """Print comprehensive session summary."""
    try:
        from .data.analysis import session_summary as print_session_summary

        print_session_summary(animal_id, session)
    except Exception as e:
        click.echo(f"Error getting session summary: {str(e)}", err=True)
        sys.exit(1)


@main.command("config-summary")
def config_summary():
    """Display current configuration summary and source file path."""
    try:
        summary = get_config_summary()
        click.echo(summary)
        
    except Exception as e:
        click.echo(f"Error getting configuration summary: {str(e)}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--output-path",
    type=click.Path(dir_okay=False, file_okay=True),
    default="config.json",
    help="Output path for configuration file (default: config.json)",
)
@click.option(
    "--template-only",
    is_flag=True,
    help="Create template config without prompting for values",
)
def create_config(output_path: str, template_only: bool):
    """Create a new configuration file."""
    try:
        config = DEFAULT_CONFIG.copy()
        
        if not template_only:
            click.echo("Creating new configuration file...")
            click.echo("Enter database connection details (leave blank for defaults):")
            
            # Get database configuration
            host = click.prompt("Database host", default="", show_default=False)
            if host:
                config["database"]["host"] = host
            
            user = click.prompt("Database user", default="", show_default=False)
            if user:
                config["database"]["user"] = user
            
            password = click.prompt("Database password", default="", hide_input=True, show_default=False)
            if password:
                config["database"]["password"] = password
            
            # Schema mappings
            click.echo("\nSchema mappings (press Enter to use defaults):")
            for schema_type in ["experiment", "stimulus", "behavior"]:
                current_default = config["database"]["schemas"][schema_type]
                schema_name = click.prompt(f"{schema_type} schema", default=current_default, show_default=True)
                config["database"]["schemas"][schema_type] = schema_name
        
        # Save configuration
        save_config(config, output_path)
        
        click.echo(f"Configuration file created: {output_path}")
        if not template_only:
            click.echo("You can now modify this file or use environment variables to override settings.")
        else:
            click.echo("Template configuration created. Edit the file to add your database credentials.")
            
    except Exception as e:
        click.echo(f"Error creating configuration: {str(e)}", err=True)
        sys.exit(1)


@main.command()
def test_db_connection():
    """Test database connection."""
    try:
        click.echo("Testing database connection...")

        # Try to get schemas
        experiment = get_schema("experiment")
        behavior = get_schema("behavior")
        stimulus = get_schema("stimulus")

        click.echo("Successfully connected to database")
        click.echo(f"✓ Experiment schema: {experiment}")
        click.echo(f"✓ Behavior schema: {behavior}")
        click.echo(f"✓ Stimulus schema: {stimulus}")

    except Exception as e:
        click.echo(f"✗ Database connection failed: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
