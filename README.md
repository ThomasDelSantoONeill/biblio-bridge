<font size='30'>`biblio-bridge`</font>: a context-based literature
linker with emergent knowledge identification.
================
**T. J. Del Santo O’Neill**

*2025-06-20*

# <img src="www/biblio-bridge.svg" style='width: 50%; object-fit: contain; vertical-align:top'>

<!-- README.md is generated from README.Rmd. Please edit that file -->

# Disclaimer

This project represents the final beta version of the postgraduate
course “**Programación Informática Orientada a la Gestión y el
Mantenimiento del Sector Transporte, la Logística y sus Infraestructuras
Vinculadas**” offered by *Universidad Politécnica de Madrid*. The course
is part of the “*NextGenerationEU*” funding initiative aimed at
supporting research and innovation in various sectors.

This repository contains all relevant code and documentation. It is
intended for academic and research purposes only, and any use or
modification of the project should give appropriate credit.

<!-- badges: start -->

[![License: CC BY
4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
<!-- badges: end -->

# In a nutshell

The goal of `biblio-bridge` is to **identify** potential **research
avenues** that **emerge** from analysing the **context** of a focal
academic work, as well as, recursively, the context of its cited
references depending on a user-predefined depth level.

# Under the hood

`biblio-bridge` is an interactive **web application** build under the
**[Shiny](https://en.wikipedia.org/wiki/Shiny_(web_framework))
framework**. It leverages the **[OpenAlex
API](https://docs.openalex.org/how-to-use-the-api/api-overview)** to
fetch metadata, processes it using `Python` and `R`, and showcases
results through key term summaries, frequency plots, and network
visualisations.

# Prerequisites

`biblio-bridge` can be run locally if downloaded following

``` bash
git clone https://github.com/ThomasDelSantoONeill/biblio-bridge.git
#> Cloning into 'biblio-bridge'...
```

or run via **(shinyapps.io)\[<https://www.shinyapps.io/>\] web service**
at <https://thomasdelsantooneill.shinyapps.io/biblio-bridge/>.

These are the requirements if used locally:

- `R`: Version 4.0 or higher with packages: `shiny`, `reticulate`,
  `jsonlite`, `dplyr`, `purrr`, `ggplot2`, `visNetwork`.
- `Python`: Version 3.8 or higher with packages: `requests`, `numpy`,
  `scikit-learn`, `spacy`, `aiohttp`.
- `spaCy` Model: English model (`en_core_web_lg`) installed in
  “./models/”.

# Directory structure

``` plaintext
biblio-bridge/
├── app.R
├── openalex.py
├── context_extract.py
├── www/
│   ├── biblio-bridge.svg
│   ├── inst.svg
│   ├── caminos.svg
├── metadata/
│   ├── initial_data_<DOI>.json
│   ├── dl0/, dl1/, ...
├── results/
│   ├── network_results_depth_<N>.json
├── models/
│   ├── en_core_web_lg/
```

# Contact

Should any issue araise, please open it on the GitHub repository or
email me at \[<delsantooneillthomas@gmail.com>\].
