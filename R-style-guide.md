# PIH R Style Guide

## Code Style and Language Features

Follow the
[Google Style Guide](https://google.github.io/styleguide/Rguide.xml).
This document should be read as an extension of that, with the following
exception:

Curly braces are obligatory for all blocks, even single-line blocks.
Inline blocks are acceptable, but use them sparingly. A good use is an
inline `if/else` statement in the style of other languages' ternary 
operator. You may omit curly braces for inline blocks.

GOOD:
```
if (is.null(ylim)) {
  ylim <- c(0, 0.06)
}
```

```
if (x > 5) "yes" else "no"
```

BAD: 
```
if (is.null(ylim))
  ylim <- c(0, 0.06) 
```

Use the [Tidyverse](https://www.tidyverse.org/).
[Learn](https://r4ds.had.co.nz/) the Tidyverse. Most of your files
should have `library(tidyverse)` as one of the first lines of code.
Prefer Tidyverse functions to their
base R equivalents. They are better designed; their behavior makes more
sense.

Avoid using pipes (`%>%`) or other magrittr( !!!!!!!!!!!!!!!!! )
features. They make code marginally easier to read, but extremely
difficult to debug.


## Structuring Projects

Structure your projects according to
[this guide](https://chrisvoncsefalvay.com/structuring-r-projects/).
That is,

```
.
└── my_awesome_project/
    ├── src/            # files with functions and their tests
    ├── data/
    │   ├── raw         # the input data, which should not be modified
    │   ├── tmp         # intermediate artifacts
    │   └── output
    ├── README.md
    ├── run_analyses.R 
    └── .gitignore
```

The test file for `src/data_prep.R` should be called `src/test-data_prep.R`.

Use the `source` function to include files in `src/`. Do not use either
of the modules libraries (
[1](https://cran.r-project.org/web/packages/modules/vignettes/modulesInR.html),
[2](https://github.com/klmr/modules)).
They are very immature and do not yet work well.

Functions in the files in `src/` should be given a short (1-4 letter) prefix
starting with a capital letter, separated from the function name by a dot.
This prefix indicates which file the function is in. For example, all
the functions in the file `indicators.R` might be prefixed with `In.`,
yielding e.g. `In.NumEnrolledPatients`, `In.PercentageInControl`, etc. Thus,
when you source `src/indicators.R` in a script or in another function file,
you will immediately know what file the PercentageInControl function is
in. Further, this effectively namespaces functions, so that you can have
`Pt.GetData()` get patient data and `Con.GetData()` get consult data.


## Packrat

Use [prackrat](https://rstudio.github.io/packrat/)
for dependency management. Be sure to execute
`packrat::set_opts(vcs.ignore.src = TRUE)`
so that it adds `packrat/src` to your `.gitignore`, so that you aren't
committing your depedencies themselves to VCS.


## Developing

There are two ways of writing R code, which I'll call "scripting"
and "programming." A
project may swich from one to the other, or make use of both.


### Scripting

R is, at heart, a scripting language. A script is a single file which,
when executed, does something. Scripts are often developed by running
commands in the interactive console, adding those lines to a script
file as you go, and then cleaning up (choosing better variable names,
fixing formatting, etc).

As your script grows, you should refactor logical pieces of it into
functions. Document those functions with comments, per the 
[Google Style Guide](https://google.github.io/styleguide/Rguide.xml).

If at some point you want to use those functions in another script,
you should refactor them into their own file. You will then be in
the domain of Programming.

### Programming

R Shiny applications, projects consisting of multiple scripts with
shared logic, and other larger applications should be developed in the
Programming style. For this kind of project, all of the logic will take
place in functions in files under `src/` (see above project structure).

The purpose of this is to allow us to develop functions by writing
tests for them. This process produces tests as a byproduct of development.
Tests are essential to making sure your project continues
to work as expected as it grows and evolves. This is the basic idea
of Test Driven Development, or TDD. Use `testthat` for testing.

In general, the script's job is to coordinate inputs and outputs with
your functions.

> Example
>
> I want to find all the patients with high blood pressure.
> I begin by creating a script, which outlines the
> process in the most general possible terms. Again, the job of this
> script is to coordinate inputs and outputs with functions from `src/`.
>
> `findHTN.R`
> ```
> #' findHTN.R
> #' Given clinical data, outputs the names of patients with high blood
> #' pressure readings.
> 
> source("src/data_prep.R")
> source("src/htn_identification.R")
>
> OUTPUT_FILENAME <- "data/output/htn.csv"
>
> print("Getting patient data")
> ptData <- Data.GetPtData()
> print("Finding patients with high BP readings")
> htnResults <- HTN.FindPtsWithHighValues(ptData)
> print(paste("Writing results to ", OUTPUT_FILENAME))
> Data.WriteResults(htnResults, OUTPUT_FILENAME)
> ```
>
> Let's assume that we already have a file `src/data_prep.R`, containing
> the functions `GetPtData` and `WriteResults`. They should in any case
> just be one-line wrappers for read_csv and write_csv.
>
> Let's start on our logic function.
>
> `src/htn_identification.R`
> ```
> #' htn_identification.R
> #' Provides a function for finding patients with high blood pressure.
> 
> library(tidyverse)
>
> HTN.FindPtsWithHighValues <- function(pt_data) {
>   # this is where we'll write a function
> }
> ```
>
> Before we do anything with this function, let's write a test that
> encodes our expectations for this function.
>
> `src/test-htn_identification.R`
> ```
> library("testthat")
> library("tidyverse")
> source("src/htn_identification.R")
>
> test_that("FindPtsWithHighValues returns a vector of names of patients with systolic BP above 140", {
>   test_data <- tribble(
>     ~"name",  ~"bp-systolic", ~"bp-diastolic",
>     "Normal", 120,            80,
>     "High",   141,            90,
>     "Spread", 140,            50
>   )
>   results <- HTN.FindPtsWithHighValues(test_data)
>   expect_equal(1, length(results))
>   expect_equal("High", results[[1]])
> })
> ```
>
> Run the test file as a script and watch it fail. Then write go back
> to `src/htn_identification.R` and write the function so that it
> passes!

If developing an R Shiny application, `server.R` should be centrally
concerned with expressing the relationships between input, output,
and functions in `src/`. It should also contain display logic, unless
display logic has been refactored out into its own file in `src/`,
perhaps called something like `charts.R`, if what it contains are
functions that produce charts. `charts.R` should contain no application
logic. You probably don't need to write tests for `charts.R`.
The files in `src/` that contain application logic should
contain no display logic. They should have tests.

