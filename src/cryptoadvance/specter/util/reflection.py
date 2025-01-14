import logging
from importlib import import_module
from inspect import isclass
import os
from pathlib import Path
import pkgutil
from pkgutil import iter_modules
import sys

logger = logging.getLogger(__name__)


def _get_module_from_class(clazz):
    return import_module(clazz.__module__)


def get_template_static_folder(foldername):
    """convenience-method to return static/template methods taking pyinstaller into account
    foldername can be anything but probably most reasonable template or static
    """
    if getattr(sys, "frozen", False):
        # Best understood with the snippet below this section:
        # https://pyinstaller.readthedocs.io/en/v3.3.1/runtime-information.html#using-sys-executable-and-sys-argv-0
        x_folder = os.path.join(sys._MEIPASS, foldername)
    else:
        x_folder = foldername
    return x_folder


def get_package_dir_for_subclasses_of(clazz):
    """There are two occasions where this is used: migrations and service-classes. Depending on the clazz
    this function is returning package_directories where subclasses from clazz are supposed to be located
    * subclasses of SpecterMigration are located in a subpackage called migrations
    * subclasses of Servuce are located in subpackages of package cryptoadvance.specter.services
    I have to admit that this is not a pure util class as it's containing business-logic
    """
    if clazz.__name__ == "SpecterMigration":
        return str(
            Path(
                Path(_get_module_from_class(clazz).__file__).resolve().parent,
                "migrations",
            ).resolve()
        )
    elif clazz.__name__ == "Service":
        return str(
            Path(
                import_module("cryptoadvance.specter.services").__file__
            ).parent.resolve()
        )


def get_subclasses_for_class(clazz, services_load_from_cwd=False):
    """Returns all subclasses of class clazz located in the specific package for that class"""
    class_list = []
    loopdir = Path(__file__).resolve()
    package_dir = get_package_dir_for_subclasses_of(clazz)
    logger.info(f"Collecting subclasses of {clazz.__name__} in {package_dir}...")
    package_dirs = [package_dir]
    if services_load_from_cwd:
        if not Path("./src/cryptoadvance").is_dir():
            package_dirs.append(".")
            logger.debug(
                "Running in non-specter-src-folder. Added CWD to Service-Discovery"
            )
    for (_, module_name, _) in iter_modules(
        package_dirs
    ):  # import the module and iterate through its attributes
        logger.debug(f"Iterating on {module_name} ")
        if clazz.__name__ == "Service":
            try:

                module = import_module(
                    f"cryptoadvance.specter.services.{module_name}.service"
                )
                logger.debug(
                    f"Imported cryptoadvance.specter.services.{module_name}.service"
                )
            except ModuleNotFoundError:
                logger.debug(
                    f"No Service Impl found in cryptoadvance.specter.services.{module_name}."
                )
                try:
                    module = import_module(f"{module_name}.service")
                    logger.debug(f"Imported {module_name}.service")
                except ModuleNotFoundError as e:
                    logger.debug(
                        f"No Service Impl found in {module_name}.service. Skipping!"
                    )
                    continue
        elif clazz.__name__ == "SpecterMigration":
            module = import_module(
                f"cryptoadvance.specter.util.migrations.{module_name}"
            )
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isclass(attribute):
                if (
                    issubclass(attribute, clazz)
                    and not attribute.__name__ == clazz.__name__
                ):
                    class_list.append(attribute)
                    logger.info(f"  Found class {attribute.__name__}")
    return class_list
