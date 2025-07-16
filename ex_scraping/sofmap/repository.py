import os
import json
from abc import ABC, abstractmethod

from .model import CategoryResult

CATEGORY_DEFAULT_FILENAME = "sofmap_category.json"
AKIBA_CATEGORY_DEFAULT_FILENAME = "a_sofmap_category.json"


class ICategoryRepository(ABC):
    @abstractmethod
    def save(self, cate: CategoryResult):
        pass

    @abstractmethod
    def get_gid(self, name: str) -> str:
        pass

    @abstractmethod
    def has_data(self) -> bool:
        pass


class FileCategoryRepository(ICategoryRepository):
    dir_path: str
    fname: str

    def __init__(self, filename: str = CATEGORY_DEFAULT_FILENAME, dirpath: str = ""):
        self.dir_path = dirpath
        self.fname = filename

    def _create_output_filepath(self) -> str:
        return os.path.join(self.dir_path, self.fname)

    def save(self, cate: CategoryResult):
        with open(self._create_output_filepath(), "w") as f:
            f.write(json.dumps(cate.name_to_gid, ensure_ascii=False))

    def get_gid(self, name: str) -> str:
        if not name:
            return ""
        output_path = self._create_output_filepath()
        if not os.path.exists(output_path):
            return ""
        with open(output_path, "r") as f:
            jtext = f.read()
        name_to_gid: dict = json.loads(jtext)
        if type(name_to_gid) is not dict:
            return ""
        return name_to_gid.get(name, "")

    def has_data(self) -> bool:
        if not os.path.exists(self._create_output_filepath()):
            return False
        with open(self._create_output_filepath(), "r") as f:
            jtext = f.read()
        if not jtext:
            return False
        name_to_gid: dict = json.loads(jtext)
        if type(name_to_gid) is not dict:
            return False
        return len(name_to_gid) > 0


class FileAkibaCategoryRepository(FileCategoryRepository):
    def __init__(
        self, filename: str = AKIBA_CATEGORY_DEFAULT_FILENAME, dirpath: str = ""
    ):
        super().__init__(filename=filename, dirpath=dirpath)
