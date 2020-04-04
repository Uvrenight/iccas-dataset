# Italy Coronavirus Cases by Age group and Sex (ICCAS)

_[Leggilo in italiano](README.it.md)._

This repository contains datasets about the number of Italian Sars-CoV-2 
confirmed cases and deaths disaggregated by age group and sex. 
The data is (automatically) extracted from pdf reports 
(like [this](https://www.epicentro.iss.it/coronavirus/bollettino/Bollettino-sorveglianza-integrata-COVID-19_30-marzo-2020.pdf)) 
published by _Istituto Superiore di Sanità_ (ISS) two times a week.
A link to the most recent report can be found in [this page](https://www.epicentro.iss.it/coronavirus/sars-cov-2-sorveglianza-dati)
under section "Documento esteso".

The code for downloading ISS reports and for generating all datasets is also 
included (but maybe I'll move it into a separate repository).

Hopefully, ISS or other institutions will release more detailed 
machine-readable data making this repository useless. 

## Data folder structure
The `data` folder is structured as follows:
```
data
├── by-date                    
│   └── iccas_{date}.csv   Dataset with cases/deaths updated to 4 p.m. of {date}
└── iccas_full.csv      Dataset with data from all reports (by date)
```
The full dataset is obtained by concatenating all datasets in `by-date` and has
an additional `date` column.

## Dataset details
Each dataset in the `by-date` folder contains the same data you can find in 
"Table 1" of the corresponding ISS report.
This table contains the number of confirmed cases, deaths and other derived
information disaggregated by age group (0-9, 10-19, ..., 80-89, >=90) and sex.

**WARNING**: the sum of male and female cases is **not** equal to the total 
number of cases, since the sex of some cases is unknown. The same applies to deaths.

Below, `{sex}` can be `male` or `female`.

| Column                    | Description                                                                                  |
|---------------------------|----------------------------------------------------------------------------------------------|
| `date`                    | **(Only in `iccas_full.csv`)** Date the format `YYYY-MM-DD`; numbers are updated to 4 p.m of this date |
| `age_group`               | Values: `"0-9", "10-19", ..., "80-89", ">=90"`                                               |
| `cases`                   | Number of confirmed cases (both sexes + unknown-sex; active + closed)                        |
| `deaths`                  | Number of deaths (both sexes + unknown-sex)                                                  |
| `{sex}_cases`             | Number of cases of sex {sex}                                                                 |
| `{sex}_deaths`            | Number of cases of sex {sex} ended up in death                                               |
| `cases_percentage`        | `100 * cases / cases_of_all_ages`                                                            |
| `deaths_percentage`       | `100 * deaths / deaths_of_all_ages`                                                          |
| `fatality_rate`           | `100 * deaths / cases`                                                                       |
| `{sex}_cases_percentage`  | `100 * {sex}_cases / (male_cases + female_cases)` (cases of unknown sex excluded)            |
| `{sex}_deaths_percentage` | `100 * {sex}_deaths / (male_deaths + female_deaths)` (cases of unknown sex excluded)         | 
| `{sex}_fatality_rate`     | `100 * {sex}_deaths / {sex}_cases`                                                           |

All columns that can be computed from absolute counts of cases and deaths (bottom 
half of the table above) were all re-computed to increase precision.

## How the code works

I tried to automate as much as possible, more for the sake of "exercising" than for convenience
(I took this as a kind of didactical project); but of course, if ISS don't make crazy changes, the
automation should work fine for a while.

Here is how it works.

### ISS reports retrieval
The [ISS news page](https://www.epicentro.iss.it/coronavirus/aggiornamenti) 
is parsed to obtain the links to all PDF reports (see `download_reports.py`) 
and if new reports are found they are downloaded into the `reports` folder 
(reports are not included in the git repository because they take MBs).

### Data extraction
For each report, the page containing the table is found by extracting the text from 
each page (using [PyPDF3](https://github.com/mstamy2/PyPDF3)) and using a regular 
expression to match the table caption.

Then, the table is extracted from the page using [tabula-py](https://github.com/chezou/tabula-py)* 
with "tabula templates", i.e. JSON files describing where the table is located (page and selection area).
Since the page containing the table is automatically detected, only the "selection area" is actually used.

Templates are stored in the `tabula-templates` folder as `{date of first validity}.tabula-template.json`
and are created using the [Tabula app](https://tabula.technology/) by loading a document 
and manually selecting the area of interest. Fortunately, the table area location has been stable so I had
to repeat this manual step only two times.

(*) I quickly tried to extract the table by parsing the text extracted by `PyPDF3` but
the solution required some "hacks", so in the end I preferred using `tabula-py`.

### Post-processing and file generation
At this point we have a dataframe for each report. All columns that can be computed from absolute 
case/death counts are recomputed to increase precision (do I really need to do that? Probably not). 

A `pandas.DataFrame` for the full dataset is created by concatenating all dataframes extracted
and defining a multi-index `(date, age_group)`.

All dataset files are generated using `pandas`.

