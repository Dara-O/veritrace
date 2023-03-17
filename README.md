<h1 align="center">Veritace</h1>
A tool used to enable static signal tracing and exploration of designs which are written in (system)verilog.

The tool parses the XML representation of the design created using [Verilator](https://veripool.org/guide/latest/) and creates three types of HTML files:
1. **Design Hierarchy Index**:  This contains a tree view of instances in the design with links to each instance's connectivity table.
2. **Instance Connectivity Table**: This contains a table with all the variables (wires, regs, etc.) in a module, along with their drivers and loads. The connectivity of these variables/signals can be traced throughout the design by following the links provided in the connectivity table.
3. **RTL**: This contains the (system)verilog statements used to describe the design.

### Requirements
| Tool      | Version Info                           |
|-----------|----------------------------------------|
| Verilator | 5.003 or greater (Tested with 5.003)   |
| Python    | 3.9.15 or greater (Tested with 3.9.15) |


### Setup
1. `git clone` this repo

### Usage:
1. Create an XML representation of the design using Verilator.

    **Note**:
    In addition to the flags and filepaths required by your specific design, PLEASE add the following flags:

    ```
    -Wno-fatal --timing --fno-dfg --fno-dedup --fno-combine --fno-assemble --fno-reorder --fno-expand --fno-subst --fno-merge-const-pool --xml-only --xml-output <design_xml_filename>.xml
    ```

    Replace `<design_xml_filename>` with the name you want to give the output xml file.

    These flags prevent line number mismatches between the connectivity html files and RTL html files. They also prevent Verilator from introducing new variables into the design.

2. Call `veritrace.py` in the same directory you ran Verilator:

    ```
    python <path_to_repo>/veritrace.py <design_xml_filename>.xml <out_dir>
    ```
    Use the `-h` flag to see more options (eg multithreading)

Please see `example_output/` directory for an example html_files produced by the tool. You can begin by viewing `example_output/index.html`.

### Caveats:
- This tool is meant to be used on synthesizable portions of the design. As a result, It only traces RTL signals or variables in `module` blocks (not a `class`, `task`, `program` or similar blocks). 
- The xml file produced by Verilator does not distinguish between `reg` or `wire` variable type. Consequently, all variables are given type `logic` in the connectivity html file. Additionally, Verilator assumes all literals to be signed by default.