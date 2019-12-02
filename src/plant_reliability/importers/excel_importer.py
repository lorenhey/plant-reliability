import pandas as pd
from typing import List, Tuple
from plant_reliability.core.domain.models import Event
from plant_reliability.importers.mapping import ImportMapping
from plant_reliability.importers.csv_importer import CsvImporter


class ExcelImporter(CsvImporter):
    def read_file(self, filepath: str) -> Tuple[List[Event], int]:
        df = pd.read_excel(filepath)
        return self._process_dataframe(df)
