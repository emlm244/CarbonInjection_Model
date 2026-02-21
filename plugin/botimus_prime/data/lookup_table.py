import csv
from bisect import bisect_left
from pathlib import Path
from typing import List


class LookupTable:

    def __init__(self, file_name: str):
        self.file_name = file_name

    def get_rows(self) -> List[dict[str, str]]:
        data_folder = Path(__file__).absolute().parent
        with (data_folder / self.file_name).open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def get_column(self, name: str) -> List[float]:
        """
        Get all data in a column
        :param name: Name of the column
        :return: List of float values in the column
        """
        return [float(row[name]) for row in self.get_rows()]

    @staticmethod
    def find_index(column: List[float], value: float) -> int:
        if not column:
            return 0
        index = bisect_left(column, value, hi=len(column))
        return min(index, len(column) - 1)
