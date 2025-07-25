"""Manim's init subcommand.

Manim's init subcommand is accessed in the command-line interface via ``manim
init``. Here you can specify options, subcommands, and subgroups for the init
group.

"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import click
import cloup

from manim._config import console
from manim.constants import CONTEXT_SETTINGS, EPILOG, QUALITIES
from manim.utils.file_ops import (
    add_import_statement,
    copy_template_files,
    get_template_names,
    get_template_path,
)

CFG_DEFAULTS = {
    "frame_rate": 30,
    "background_color": "BLACK",
    "background_opacity": 1,
    "scene_names": "Default",
    "resolution": (854, 480),
}

__all__ = ["select_resolution", "update_cfg", "project", "scene"]


def select_resolution() -> tuple[int, int]:
    """Prompts input of type click.Choice from user. Presents options from QUALITIES constant.

    Returns
    -------
    tuple[int, int]
        Tuple containing height and width.
    """
    resolution_options: list[tuple[int, int]] = []
    for quality in QUALITIES.items():
        resolution_options.append(
            (quality[1]["pixel_height"], quality[1]["pixel_width"]),
        )
    resolution_options.pop()
    choice = click.prompt(
        "\nSelect resolution:\n",
        type=cloup.Choice([f"{i[0]}p" for i in resolution_options]),
        show_default=False,
        default="480p",
    )
    matches = [res for res in resolution_options if f"{res[0]}p" == choice]
    return matches[0]


def update_cfg(cfg_dict: dict[str, Any], project_cfg_path: Path) -> None:
    """Update the ``manim.cfg`` file after reading it from the specified
    ``project_cfg_path``.

    Parameters
    ----------
    cfg_dict
        Values used to update ``manim.cfg`` which is found in
        ``project_cfg_path``.
    project_cfg_path
        Path of the ``manim.cfg`` file.
    """
    config = configparser.ConfigParser()
    config.read(project_cfg_path)
    cli_config = config["CLI"]
    for key, value in cfg_dict.items():
        if key == "resolution":
            cli_config["pixel_width"] = str(value[0])
            cli_config["pixel_height"] = str(value[1])
        else:
            cli_config[key] = str(value)

    with project_cfg_path.open("w") as conf:
        config.write(conf)


@cloup.command(
    context_settings=CONTEXT_SETTINGS,
    epilog=EPILOG,
)
@cloup.argument("project_name", type=cloup.Path(path_type=Path), required=False)
@cloup.option(
    "-d",
    "--default",
    "default_settings",
    is_flag=True,
    help="Default settings for project creation.",
    nargs=1,
)
def project(default_settings: bool, **kwargs: Any) -> None:
    """Creates a new project.

    PROJECT_NAME is the name of the folder in which the new project will be initialized.
    """
    project_name: Path
    if kwargs["project_name"]:
        project_name = kwargs["project_name"]
    else:
        project_name = click.prompt("Project Name", type=Path)

    # in the future when implementing a full template system. Choices are going to be saved in some sort of config file for templates
    template_name = click.prompt(
        "Template",
        type=click.Choice(get_template_names(), False),
        default="Default",
    )

    if project_name.is_dir():
        console.print(
            f"\nFolder [red]{project_name}[/red] exists. Please type another name\n",
        )
    else:
        project_name.mkdir()
        new_cfg: dict[str, Any] = {}
        new_cfg_path = Path.resolve(project_name / "manim.cfg")

        if not default_settings:
            for key, value in CFG_DEFAULTS.items():
                if key == "scene_names":
                    new_cfg[key] = template_name + "Template"
                elif key == "resolution":
                    new_cfg[key] = select_resolution()
                else:
                    new_cfg[key] = click.prompt(f"\n{key}", default=value)

            console.print("\n", new_cfg)
            if click.confirm("Do you want to continue?", default=True, abort=True):
                copy_template_files(project_name, template_name)
                update_cfg(new_cfg, new_cfg_path)
        else:
            copy_template_files(project_name, template_name)
            update_cfg(CFG_DEFAULTS, new_cfg_path)


@cloup.command(
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=True,
    epilog=EPILOG,
)
@cloup.argument("scene_name", type=str, required=True)
@cloup.argument("file_name", type=str, required=False)
def scene(**kwargs: Any) -> None:
    """Inserts a SCENE to an existing FILE or creates a new FILE.

    SCENE is the name of the scene that will be inserted.

    FILE is the name of file in which the SCENE will be inserted.
    """
    template_name: str = click.prompt(
        "template",
        type=click.Choice(get_template_names(), False),
        default="Default",
    )
    scene = (get_template_path() / f"{template_name}.mtp").resolve().read_text()
    scene = scene.replace(template_name + "Template", kwargs["scene_name"], 1)

    if kwargs["file_name"]:
        file_name = Path(kwargs["file_name"])

        if file_name.suffix != ".py":
            file_name = file_name.with_suffix(file_name.suffix + ".py")

        if file_name.is_file():
            # file exists so we are going to append new scene to that file
            with file_name.open("a") as f:
                f.write("\n\n\n" + scene)
        else:
            # file does not exist so we create a new file, append the scene and prepend the import statement
            file_name.write_text("\n\n\n" + scene)

            add_import_statement(file_name)
    else:
        # file name is not provided so we assume it is main.py
        # if main.py does not exist we do not continue
        with Path("main.py").open("a") as f:
            f.write("\n\n\n" + scene)


@cloup.group(
    context_settings=CONTEXT_SETTINGS,
    invoke_without_command=True,
    no_args_is_help=True,
    epilog=EPILOG,
    help="Create a new project or insert a new scene.",
)
@cloup.pass_context
def init(ctx: cloup.Context) -> None:
    pass


init.add_command(project)
init.add_command(scene)
