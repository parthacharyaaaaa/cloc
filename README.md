# locstat
## Get LoC statistics, fast.

* [Installation](#installation)
* [Usage](#usage)
    * [Primary Action](#primary-action)
    * [Parsing Filters](#parsing-filters)
    * [Finer Parsing Control](#finer-parsing-controls)
    * [Emitting Results](#emitting-results)

* [Examples](#examples)

* [Customizations](#customizations)
* [License](#license)
* [Comptatibility Notes](#compatibility-notes)
* [Acknowledgements](#acknowledgements)

## Installation

```bash
$ pip install locstat
```

## Usage
locstat is designed to be a CLI tool, invocable as the package name itself.

```bash
$ locstat [-h] (-v VERSION | -f FILE | -d DIR | -c CONFIG | -clm COPY_LANGUAGE_METADATA | -rc RESTORE_CONFIG) [options]
```

### Primary Action
---
A primary action must be specified when invoking the tool through the command line, namely:
* **-v/--version**: Display the installed version and exit
* **-h/--help**: Display the help message and exit

* **-c/--config**: Display and optionally edit the configuration settings and exit
* **-clm/--copy-language-metadata**: Copy language metadata file to given filepath
* **-rc/--restore-config**: Restore configuration settings

* **-f/--file**: Filepath to parse
* **-d/--dir**: Directory to parse

**Note**: These options are **mutually exclusive**

### Parsing Filters
---
#### Directories:
**-xd/--exclude-dir**: Directory paths following this flag will be ignored.

**-id/--include-dir**: Parse only the directories following this flag.

#### Files:
**-xf/--exclude-file**: Filepaths following this flag will be ignored.

**-if/--include-file**: Only filepaths following this flag will be parsed.

**-xt/--exclude-type**: File extensions following this flag will be ignored.

**-it/--include-type**: Only file extensions following this flag will be parsed.

#### Path Resolution
Assume a directory structure as follows:
```bash
├── locstat
│   ├── data_structures
│   ├── parsing
│   │   └── extensions
│   └── utilities
└── tests
    ├── integrity
    └── unit
```
Furthermore, lets assume that our CWD is `../locstat`, i.e. a level above the structure.

Here, suppose we wish to exclude the nested `extensions` directory from our scans (-xd flag). Locstat provides 3 ways of achieving this:

1. **Absolute**
```bash
$ locstat -d locstat -xd /home/foo/projects/locstat/tests
```

2. **Relative**
```bash
$ locstat -d locstat -xd locstat/tests
```

3. **Implicitly Relative**
```bash
$ locstat -d locstat -xd tests
```

### Finer Parsing Controls
---
**-pm/--parsing-mode**: Override default file parsing behaviour. Available options: MMAP, BUF, COMP.

1) **BUF**: Default parsing mode. Allocates a buffer of 4MB and reads files in chunks into this buffer.

2) **MMAP**: Map files to the virtual memory of the locstat process in an attempt to reduce the number of syscalls. May improve performance for hot page caches or for larger source files. Uses `mmap` and `madvice` on Linux and Mac systems, or `CreateFileMapping` and `MapViewOfFile` on Windows.

3) **COMP**: Read the entire file at once without any buffering.

---

**-vb/--verbosity**: Amount of statistics to include in the final report. Available modes:

1) **BARE**: Default mode, count only total lines and lines of code.

2) **REPORT**: Additionally include language metadata, i.e. number of files, total lines, and lines of code per file extension parsed.

3) **DETAILED**: Additionally include language metadata and per directory and per file line statistics.

---

**-md/--max-depth**: Recursively scan sub-directories upto the given level. Negative values are treated as infinite depth. Defaults to -1

**-mc/--min-chars**: Specify the minimum number of non-whitespace characters a line should have to be considered an LOC. Defaults to 1.

**-clm/--copy-language-metadata**: Copy language metadata to a specified file, used as a precursor to using custom language metadata.

**-lm/--language-metadata**: Specify JSON file to supply additional comment data for languages. This file is read and used instead of the default language metadata file.

**-rc/--restore-config**: Restore configuration file to default its state.

### Emitting Results
---
**-o/--output**: Specify output file to dump counts into. If not specified, output is dumped to `stdout`. If output file is in json then output is formatted differently.

## Examples
Let's run locstat against a cloned repository of `cpython-main`

```bash
$ locstat -d /home/tcn/targets/cpython-main/

General:
Total : 2155349
Loc : 1722995
Comments : 213946
Blank : 218408
Time : 0.911s
Scanned : 22/02/26, at 15:40:51
Platform : Linux
```

Additionally, we can fetch per-extension metadata using the `REPORT` verbosity mode.

```bash
$ locstat -d /home/tcn/targets/cpython-main/ -vb REPORT

General:
Total : 2155349
Loc : 1722995
Comments : 213946
Blank : 218408
Time : 0.196s
Scanned : 22/02/26, at 15:41:05
Platform : Linux

Languages
Extension  Files    Total     LOC  Comments   Blank
-----------------------------------------------------
py          2211  1088097  851618    109836  126643
bat           32     2327    1959         0     368
ps1            6      571     451        48      72
sh            14      918     582       237      99
css            6     3248    2570       202     476
c            485   652306  498587     95501   58218
h            637   356061  319201      7124   29736
js            10     2431    1775       281     375
html          18    10327    9132        51    1144
xml          119    31796   31615        25     156
m             10     1029     807        85     137
xsl            2       33      16        15       2
cpp            7     4989    3796       385     808
vbs            1        1       0         0       1
pyi            1        4       2         1       1
asm            1       46      18        26       2
lisp           1      692     502        81     109
ts             2       37      32         2       3
kts            3      307     236        31      40
kt             2      129      96        15      18
```
**Note**: The drop in scanning time in the second example is thanks to page caching following the first example.

## Customizations
locstat allows for default behaviour to be overridden per invocation, such as:

```bash
locstat -f foo.py --min-chars 2
```
This overrides the default minimum characters threshold of 1

Furthermore, changes to default values can be saved permanently using the `--config` (shorthand: `-c`) flag.

When invoked without any arguments, `--config` displays the current default configurations for locstat.

#### changelog v1.1.0
* Configuration settings can be restored to their default state using `--restore-config` (shorthand: `-rc`)

`locstat 1.2.0` introduces a new customization: language metadata

By default, locstat uses a flat `languages.json` file to infer data about comment symbols. This file is shipped as part of locstat releases and meant to be **read-only**.

However, to allow for customizations, locstat introduces 2 commands.

**Example**
```bash
$ locstat --copy-language-metadata foo.json
$ locstat --config language_metadata_path foo.json
$ locstat --config
language_metadata_path : foo.json
max_depth : -1
minimum_characters : 1
parsing_mode : BUF
verbosity : BARE
```
Now, changes can be made to `foo.json`, and locstat would always use this file as a symbol reference. Of course, these changes can be reverted through `--restore-config`

To update any value, append the flag with the option name and it's new value as a space-separated pair.

```bash
$ locstat --config max_depth 5 parsing_mode MMAP verbosity report
$ locstat --config
language_metadata_path :
max_depth : 5
minimum_characters : 1
parsing_mode : MMAP
verbosity : REPORT
```

**Note**: String enums are case-insensitive.

## License
locstat is licensed under the MIT license.

## Compatibility Notes
locstat ships using `cibuildwheels`, allowing for platform-specific wheels for Linux, Windows, and Mac, spanning different architectures.

However, some platforms have been excluded due to cross-compatibility pains or their packaging requiring extremely long waiting times for workflow runners (such as Mac systems using Intel chips).

This does not mean that locstat is completely incompatible on all remaining systems. The source distribution is also shipped alongside wheels.

## Acknowledgements
locstat (formerly named pycloc, but that name was taken 2 weeks before I got to publishing :P) started as a one-day project to allow a good friend to count how many lines of C++ code were present in his UE5 project.

Since then, many features and improvements have been added to this still simple tool, all of which would have been impossible without the collective effort of thousands of open-source contributors, spanning across many projects such as CPython and Perl Cloc (the gold standard!) to even make programming possible for me.

Furthermore, the online help provided by thousands of contributors on StackOverflow, HackerNews and countless personal technical blogs has made it possible for me to polish and refine this tool.

My deepest gratitude goes to everyone, however indirectly involved, in the sphere of computer programming. Even for the smallest steps I take, I stand nonetheless on the shoulders of countless giants.
