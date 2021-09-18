import pandas as pd

from plant_reliability.core.domain.models import Event
from plant_reliability.importers.csv_importer import CsvImporter


class ExcelImporter(CsvImporter):
    def read_file(self, filepath: str) -> tuple[list[Event], int]:
        df = pd.read_excel(filepath)
        return self._process_dataframe(df)
