import shutil
from pathlib import Path
from typing import Any

import openpyxl
import yaml
from pydantic import BaseModel


class Config(BaseModel):
    institute_name: str
    enrollment: int
    monthly_payment: int
    template_directory: Path
    output_directory: Path


def load_config(filename: str) -> Any:
    with open(filename) as file:
        return yaml.safe_load(file)


def validate_config(filename: str) -> Config | None:
    data = load_config(filename)
    try:
        return Config(**data)
    except Exception as e:
        print(e)
        return


def copy_template(
    in_directory: Path,
    out_directory: Path,
    config: Config,
    delete_if_exist: bool = True,
) -> None:
    if delete_if_exist:
        shutil.rmtree(out_directory)
    shutil.copytree(in_directory, out_directory, dirs_exist_ok=True)
    institute_file = out_directory / "INSTITUTO"
    institute_file.rename(out_directory / config.institute_name)
    print(institute_file)
