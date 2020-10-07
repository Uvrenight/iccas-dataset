import abc
import math
import re
from datetime import datetime
from typing import Tuple

import pandas as pd
from PyPDF3 import PdfFileReader
from reagex import reagex

from common import (
    cartesian_join,
    get_italian_date_pattern,
    process_datetime_tokens
)


def to_int(s):
    if not s:
        return math.nan
    return int(s.replace('.', '').replace(' ', ''))


def to_float(s):
    if not s:
        return math.nan
    return float(s.replace(',', '.'))


COLUMN_PREFIXES = ('male_', 'female_', '')
COLUMN_FIELDS = ('cases', 'cases_percentage', 'deaths', 'deaths_percentage', 'fatality_rate')
COLUMNS = ('age_group', *cartesian_join(COLUMN_PREFIXES, COLUMN_FIELDS))
COLUMN_CONVERTERS = [str] + [to_int, to_float, to_int, to_float, to_float] * 3  # noqa
CONVERTER_BY_COLUMN = dict(zip(COLUMNS, COLUMN_CONVERTERS))

# Useful to find the page containing the table
TABLE_CAPTION_PATTERN = re.compile(
    'tabella [0-9- ]+ distribuzione dei casi .+ per fascia di et. ',
    re.IGNORECASE
)

DATETIME_PATTERN = re.compile(
    get_italian_date_pattern(sep='[ ]?') + reagex(
        '[- ]* ore {hour}:{minute}',
        hour='[o0-2]?[o0-9]|3[o0-1]',  # yes, in some reports they wrote 'o' instead of zero
        minute='[o0-5][o0-9]'),
    re.IGNORECASE
)


class TableExtractionError(Exception):
    pass


class TableExtractor(abc.ABC):
    @abc.abstractmethod
    def extract(self, report_path) -> pd.DataFrame:
        pass

    def __call__(self, report_path):
        return self.extract(report_path)


class PyPDFTableExtractor(TableExtractor):
    unknown_age_matcher = re.compile('(età non nota|non not[ao])', flags=re.IGNORECASE)

    def extract(self, report_path) -> pd.DataFrame:
        pdf = PdfFileReader(str(report_path))
        date = extract_datetime(extract_text(pdf, page=0))
        page, _ = find_table_page(pdf)
        page = self.unknown_age_matcher.sub('unknown', page)
        data_start = page.find('0-9')
        raw_data = page[data_start:]
        raw_data = raw_data.replace(', ', ',')  # from 28/09, they write "1,5" as "1, 5"
        tokens = raw_data.split(' ')
        num_rows = 11
        num_columns = len(COLUMNS)
        rows = []
        for i in range(num_rows):
            data_start = i * num_columns
            end = data_start + num_columns
            values = convert_values(tokens[data_start:end], COLUMN_CONVERTERS)
            row = [date, *values]
            rows.append(row)
        df = pd.DataFrame(rows, columns=['date', *COLUMNS])
        return normalize_table(df)


def extract_text(pdf: PdfFileReader, page: int) -> str:
    # For some reason, the extracted text contains a lot of superfluous newlines
    return pdf.getPage(page).extractText().replace('\n', '')


def extract_datetime(text: str) -> datetime:
    match = DATETIME_PATTERN.search(text)
    if match is None:
        raise TableExtractionError('extraction of report datetime failed')
    datetime_dict = process_datetime_tokens(match.groupdict())
    return datetime(**datetime_dict)


def find_table_page(pdf: PdfFileReader) -> Tuple[str, int]:
    """ Finds the page containing the data table, then returns a tuple with:
    - the text extracted from the page, pre-processed
    - the page number (0-based)
    """
    num_pages = pdf.getNumPages()

    for i in range(1, num_pages):  # skip the first page, the table is certainly not there
        text = extract_text(pdf, page=i)
        if TABLE_CAPTION_PATTERN.search(text):
            return text, i
    else:
        raise TableExtractionError('could not find the table in the pdf')


def normalize_table(table: pd.DataFrame) -> pd.DataFrame:
    # Replace '≥90' with ascii equivalent '>=90'
    table.at[9, 'age_group'] = '>=90'
    # Replace 'Età non nota' with english translation
    table.at[10, 'age_group'] = 'unknown'
    return table


def sanity_check_with_totals(table: pd.DataFrame, totals):
    columns = cartesian_join(COLUMN_PREFIXES, ['cases', 'deaths'])
    for col in columns:
        actual_sum = table[col].sum()
        if actual_sum != totals[col]:
            raise TableExtractionError(
                f'column "{col}" sum() is inconsistent with the value reported '
                f'in the last row of the table: {actual_sum} != {totals[col]}')


def convert_values(values, converters):
    if len(values) != len(converters):
        raise ValueError
    return [converter(value) for value, converter in zip(values, converters)]
