# MIT License
#
# Copyright (c) 2023 Isaac Ogunmola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os 
import sys
import re
import argparse
import xml.etree.ElementTree as ET

# Notes:
#   - RTL HTML File format: [folder_name][/]<module_name>.v.html

###################
# FUNCTIONS
###################

def writeCSSFile(out_dir: str) -> str:
    """
    Responsibility

    Writes external CSS file used to style the...
    ...connectivity table

    Returns:

    string, Path to CSS file

    Parameter:

    out_dir   :   string, path to directory that will hold the written css file 
    """

    # some of the css below was adapted from: 
    # - https://stackoverflow.com/questions/41306797/html-how-to-add-line-numbers-to-a-source-code-block
    # - https://highlightjs.org/

    # WARNING: class names in css_text below must match class names used..
    # ...in '_reRepl_replaceRTL' function
    css_text = \
"""
body {
    background-color: #fafafa;
}
.hljs-comment {
  color: blue;
}
.hljs-keyword {
    color: #a72a2c;
    font-weight: bold;
}
.hljs-const {
    color: #ff00ff;
}
.hljs-operator {
    color: blue;
}
p {
    font-family: sans-serif;
}

pre {
    font-size: 14px;
}

pre.code {
    white-space: pre-wrap;
}
pre.code:before {
    counter-reset: listing;
}
pre.code code {
    counter-increment: listing;
}
pre.code code:before {
    content: counter(listing) "| ";
    display: inline-block;
    width: 5em;         
    padding-left: none; 
    margin-left: none;  
    text-align: right;  
    color: gray
}
/* Section Animation */
@import "compass/css3";

:target {
    -webkit-animation: target-fade 3600s;
    -moz-animation: target-fade 3600s;
    -o-animation: target-fade 3600s;
    animation: target-fade 3600s;
}

@-webkit-keyframes target-fade {
    from {
    background-color: yellow;
    }

    to {
    background-color: transparent;
    }
}

@-moz-keyframes target-fade {
    from {
    background-color: yellow;
    }

    to {
    background-color: transparent;
    }
}

@-o-keyframes target-fade {
    from {
    background-color: yellow;
    }

    to {
    background-color: transparent;
    }
}

@keyframes target-fade {
    from {
    background-color: yellow;
    }

    to {
    background-color: transparent;
    }
}
"""
    file_name = "rtl_html_style.css"

    out_file_path = os.path.join(out_dir,
                                 file_name)

    with open(out_file_path, 'w') as f:
        f.write(css_text)

    return out_file_path

def _HTML_createRTLTxt(rtl_text: str, parent_html_xe: ET.Element) -> ET.Element:
    """
    Returns

    xml.etree.ElementTree.Element, xml element containing the top-level HTML tag...
    ...for the rtl text

    Parameters:

    rtl_text    :   str, string containing RTL contents
    
    parent_html_xe  :   xml.etree.ElementTree.Element, parent xml element contaiing...
                        ...html data
    """

    # xe == 'xml element'
    pre_xe = ET.SubElement(parent_html_xe, "pre")
    pre_xe.set("class", "code")

    for line_num, line in enumerate(rtl_text.splitlines()):
        code_xe = ET.SubElement(pre_xe, "code")
        code_xe.set("id", str(line_num+1))
        code_xe.text = line

    
    return pre_xe

def _reRepl_replaceRTL(match_obj: re.Match, init: bool=False) -> str:
    """
    Responsibility:

    Wraps RTL code (given in ```match_obj```) with html...
    ...tags to enable syntax highlighting when rendered

    Parameters:

    match_obj   :   re.Match object, passed from re.sub().

    init        :   bool, denotes if invocation is meant to...
                    ...initialize static vars
    """

    # to be used by code outside this function
    _reRepl_replaceRTL.PATTERN = r"""(<code[^>]+>)([^<]*)(</code>)"""
    
    # to be used internally
    _reRepl_replaceRTL.VERILOG_COMMENTS = "(//.*)"
    _reRepl_replaceRTL.VERILOG_CONSTS = "(\\b[_A-Z0-9]+)"

    _reRepl_replaceRTL.VERILOG_KEYWORDS = [
        "accept_on", "alias", "always", "always_comb", "always_ff", "always_latch", "and", "assert", "assign", "assume", "automatic", "before", "begin", "bind", "bins", "binsof", "bit", "break", "bufif0", "bufif1", "byte", "case", "casex", "casez", "cell", "chandle", "checker", "class", "clocking", "cmos", "config", "const", "constraint", "context", "continue", "cover", "covergroup", "coverpoint", "cross", "deassign", "default", "defparam", "design", "disable", "dist", "do", "edge", "else", "end", "endcase", "endchecker", "endclass", "endclocking", "endconfig", "endfunction", "endgenerate", "endgroup", "endinterface", "endmodule", "endpackage", "endprimitive", "endprogram", "endproperty", "endspecify", "endsequence", "endtable", "endtask", "enum", "event", "eventually", "expect", "export", "extends", "extern", "final", "first_match", "for", "force", "foreach", "forever", "fork", "forkjoin", "function", "generate|5", "genvar", "global", "highz0", "highz1", "if", "iff", "ifnone", "ignore_bins", "illegal_bins", "implements", "implies", "import", "incdir", "include", "initial", "inout", "input", "inside", "instance", "int", "integer", "interconnect", "interface", "intersect", "join", "join_any", "join_none", "large", "let", "liblist", "library", "local", "localparam", "logic", "longint", "macromodule", "matches", "medium", "modport", "module", "nand", "negedge", "nettype", "new", "nexttime", "nmos", "nor", "noshowcancelled", "not", "notif0", "notif1", "or", "output", "package", "packed", "parameter", "pmos", "posedge", "primitive", "priority", "program", "property", "protected", "pull0", "pull1", "pulldown", "pullup", "pulsestyle_ondetect", "pulsestyle_onevent", "pure", "rand", "randc", "randcase", "randsequence", "rcmos", "real", "realtime", "ref", "reg", "reject_on", "release", "repeat", "restrict", "return", "rnmos", "rpmos", "rtran", "rtranif0", "rtranif1", "s_always", "s_eventually", "s_nexttime", "s_until", "s_until_with", "scalared", "sequence", "shortint", "shortreal", "showcancelled", "signed", "small", "soft", "solve", "specify", "specparam", "static", "string", "strong", "strong0", "strong1", "struct", "super", "supply0", "supply1", "sync_accept_on", "sync_reject_on", "table", "tagged", "task", "this", "throughout", "time", "timeprecision", "timeunit", "tran", "tranif0", "tranif1", "tri", "tri0", "tri1", "triand", "trior", "trireg", "type", "typedef", "union", "unique", "unique0", "unsigned", "until", "until_with", "untyped", "use", "uwire", "var", "vectored", "virtual", "void", "wait", "wait_order", "wand", "weak", "weak0", "weak1", "while", "wildcard", "wire", "with", "within", "wor", "xnor", "xor",
        "\$finish", "\$stop", "\$exit", "\$fatal", "\$error", "\$warning", "\$info", "\$realtime", "\$time", "\$printtimescale", "\$bitstoreal", "\$bitstoshortreal", "\$itor", "\$signed", "\$cast", "\$bits", "\$stime", "\$timeformat", "\$realtobits", "\$shortrealtobits", "\$rtoi", "\$unsigned", "\$asserton", "\$assertkill", "\$assertpasson", "\$assertfailon", "\$assertnonvacuouson", "\$assertoff", "\$assertcontrol", "\$assertpassoff", "\$assertfailoff", "\$assertvacuousoff", "\$isunbounded", "\$sampled", "\$fell", "\$changed", "\$past_gclk", "\$fell_gclk", "\$changed_gclk", "\$rising_gclk", "\$steady_gclk", "\$coverage_control", "\$coverage_get", "\$coverage_save", "\$set_coverage_db_name", "\$rose", "\$stable", "\$past", "\$rose_gclk", "\$stable_gclk", "\$future_gclk", "\$falling_gclk", "\$changing_gclk", "\$display", "\$coverage_get_max", "\$coverage_merge", "\$get_coverage", "\$load_coverage_db", "\$typename", "\$unpacked_dimensions", "\$left", "\$low", "\$increment", "\$clog2", "\$ln", "\$log10", "\$exp", "\$sqrt", "\$pow", "\$floor", "\$ceil", "\$sin", "\$cos", "\$tan", "\$countbits", "\$onehot", "\$isunknown", "\$fatal", "\$warning", "\$dimensions", "\$right", "\$high", "\$size", "\$asin", "\$acos", "\$atan", "\$atan2", "\$hypot", "\$sinh", "\$cosh", "\$tanh", "\$asinh", "\$acosh", "\$atanh", "\$countones", "\$onehot0", "\$error", "\$info", "\$random", "\$dist_chi_square", "\$dist_erlang", "\$dist_exponential", "\$dist_normal", "\$dist_poisson", "\$dist_t", "\$dist_uniform", "\$q_initialize", "\$q_remove", "\$q_exam", "\$async\$and\$array", "\$async\$nand\$array", "\$async\$or\$array", "\$async\$nor\$array", "\$sync\$and\$array", "\$sync\$nand\$array", "\$sync\$or\$array", "\$sync\$nor\$array", "\$q_add", "\$q_full", "\$psprintf", "\$async\$and\$plane", "\$async\$nand\$plane", "\$async\$or\$plane", "\$async\$nor\$plane", "\$sync\$and\$plane", "\$sync\$nand\$plane", "\$sync\$or\$plane", "\$sync\$nor\$plane", "\$system", "\$display", "\$displayb", "\$displayh", "\$displayo", "\$strobe", "\$strobeb", "\$strobeh", "\$strobeo", "\$write", "\$readmemb", "\$readmemh", "\$writememh", "\$value\$plusargs", "\$dumpvars", "\$dumpon", "\$dumplimit", "\$dumpports", "\$dumpportson", "\$dumpportslimit", "\$writeb", "\$writeh", "\$writeo", "\$monitor", "\$monitorb", "\$monitorh", "\$monitoro", "\$writememb", "\$dumpfile", "\$dumpoff", "\$dumpall", "\$dumpflush", "\$dumpportsoff", "\$dumpportsall", "\$dumpportsflush", "\$fclose", "\$fdisplay", "\$fdisplayb", "\$fdisplayh", "\$fdisplayo", "\$fstrobe", "\$fstrobeb", "\$fstrobeh", "\$fstrobeo", "\$swrite", "\$swriteb", "\$swriteh", "\$swriteo", "\$fscanf", "\$fread", "\$fseek", "\$fflush", "\$feof", "\$fopen", "\$fwrite", "\$fwriteb", "\$fwriteh", "\$fwriteo", "\$fmonitor", "\$fmonitorb", "\$fmonitorh", "\$fmonitoro", "\$sformat", "\$sformatf", "\$fgetc", "\$ungetc", "\$fgets", "\$sscanf", "\$rewind", "\$ftell", "\$ferror"
        ]
    _reRepl_replaceRTL.VERILOG_KEYWORDS = "\\b|\\b".join(_reRepl_replaceRTL.VERILOG_KEYWORDS)
    _reRepl_replaceRTL.VERILOG_KEYWORDS =  "(\\b"+_reRepl_replaceRTL.VERILOG_KEYWORDS + "\\b)"

    _reRepl_replaceRTL.VERILOG_OPERATORS = [
        "\(", "\)", "\|", "\[", "\]", "{", "}", "&lt;", "&gt;", "-", "&amp;", "=", "==", "===", "!=", "!==", ",", ";", ":", "/", "~"
        ]
    _reRepl_replaceRTL.VERILOG_OPERATORS = "|".join(_reRepl_replaceRTL.VERILOG_OPERATORS)
    _reRepl_replaceRTL.VERILOG_OPERATORS = "("+_reRepl_replaceRTL.VERILOG_OPERATORS + ")"


    # WARNING: The class names below must match class names in...
    #           ...the CSS file (see function: 'writeCSSFile')
    KEYWORD_REPL    = '<span class="hljs-keyword">\\1</span>'
    OPERATOR_REPL   = '<span class="hljs-operator">\\1</span>'
    COMMENT_REPL    = '<span class="hljs-comment">\\1</span>'
    CONST_REPL      = '<span class="hljs-const">\\1</span>'

    # replace certain words and symbols to prevent...
    # ...complicts between substitutions
    conflict_avoidance_repl = [("class=", "<relpace_me_w_plass_eq>"),
                               ("-", "<relpace_me_w_minus>")]

    for orig, repl in conflict_avoidance_repl:
        KEYWORD_REPL = KEYWORD_REPL.replace(orig, repl)
        OPERATOR_REPL = OPERATOR_REPL.replace(orig, repl)
        COMMENT_REPL = COMMENT_REPL.replace(orig, repl)
        CONST_REPL = CONST_REPL.replace(orig, repl)


    if(not init):
        rtl_txt_combined = match_obj.group(2)

        if("//" in rtl_txt_combined):
            rtl_txt, rtl_comment = tuple(rtl_txt_combined.split("//", maxsplit=1))
        else:
            rtl_txt = rtl_txt_combined
            rtl_comment = ""

        if(rtl_comment.strip() != ""):
            rtl_comment = "//"+ rtl_comment

        # format comments
        rtl_comment = re.sub(_reRepl_replaceRTL.VERILOG_COMMENTS, COMMENT_REPL, rtl_comment)

        # format operators
        rtl_txt = re.sub(_reRepl_replaceRTL.VERILOG_OPERATORS, OPERATOR_REPL, rtl_txt)

        # format keywords
        rtl_txt = re.sub(_reRepl_replaceRTL.VERILOG_KEYWORDS, KEYWORD_REPL, rtl_txt)

        # format const
        rtl_txt = re.sub(_reRepl_replaceRTL.VERILOG_CONSTS, CONST_REPL, rtl_txt)
        
        rtl_txt_combined = rtl_txt + rtl_comment
        rtl_txt_combined = rtl_txt_combined.replace("<relpace_me_w_plass_eq>", "class=")
        rtl_txt_combined = rtl_txt_combined.replace("<relpace_me_w_minus>", "-")
        return (match_obj.group(1)+rtl_txt_combined+match_obj.group(3))

# initialize static vars
_reRepl_replaceRTL(None, init=True)

def format_RTLtxt(html_str: str) -> str:
    """
    Responsibility:

    Format RTL code within the html text to enable syntax highlighting

    Returns:

    string, containing formatted RTL code

    Parameters:

    html_str    :   string, contains html text
    """

    # replace all '&' with a placeholder text
    # this is done to prevent the javascript function from adversely modifying the html

    # regex replace
    out_str = re.sub(_reRepl_replaceRTL.PATTERN, _reRepl_replaceRTL, html_str)
    # replace AMP_PLACEHOLDER
    
    return out_str

def writeRTL_HTML(rtl_file_path: str, html_file_path: str, css_file_path: str):
    """
    Responsibility

    Converts RTL to HTML with bookmarks. The generated HTML is linked...
    ...with a connectivity table to permit examining of driver-load...
    ...connection logic

    Parameters:
    
    rtl_file_path   :   string, path/filename for source rtl file

    html_file_path  :   string, path to html file to be created

    css_file_path   :   string, path to css file
    """

    # css file name to be linked in html
    css_fname = os.path.basename(css_file_path)

    # read rtl file 
    rtl_file_txt = ""
    try:
        with open(rtl_file_path, "r") as f:
            rtl_file_txt = f.read()
    except FileNotFoundError as e:
        print("="*8)
        print(f"ERROR: RTL filepath '{rtl_file_path}' not found. Its RTL HTML file will not be generated.", file=sys.stderr)
        print("="*8)
        return

    # create html file
    html_xe = ET.Element("html")
    head_html_xe = ET.SubElement(html_xe, "head")
    head_css_link_html_xe = ET.SubElement(head_html_xe, "link")
    head_css_link_html_xe.set("rel", "stylesheet")
    head_css_link_html_xe.set("href", css_fname)

    body_html_xe = ET.SubElement(html_xe, "body")
    bheader_html_xe = ET.SubElement(body_html_xe, "p")
    bheader_html_xe.text = f"File path: {rtl_file_path}"
    bhr_html_xe = ET.SubElement(body_html_xe, "hr")

    # add rtl
    rtl_xe = _HTML_createRTLTxt(rtl_file_txt, body_html_xe)

    # write html file
    html_xe = ET.ElementTree(html_xe)
    ET.indent(html_xe)
    ET.indent(rtl_xe, space="")

    # format rtl to create syntax higlighting
    html_str = ET.tostring(
        html_xe.getroot(), 
        method='html', 
        short_empty_elements=False
    )
    html_str = html_str.decode("ascii")

    html_str = format_RTLtxt(html_str)

    # html_xe.write(html_file_path, method='html', short_empty_elements=False)
    with open(html_file_path, "w") as f:
        f.write(html_str)

    return html_file_path

def create_RTL_HTML(rtl_files: list[str], out_dir: str):
    """
    Responsibility:

    Create a series of HTML pages containing RTL code

    Parameters:

    rtl_files   :   list of strings, strings are paths to rtl files
    
    out_dir     :   string, Path to a directory that will contain...
                    ...the output files
    """

    css_file_path = writeCSSFile(out_dir)

    for rtl_file in rtl_files:
        # convert '/' to _ and remove extension from filename 
        rtl_file_name = rtl_file.replace("/", "__").split(".")[:-1]
        rtl_file_name = ".".join(rtl_file_name)

        html_file_path = os.path.join(out_dir, rtl_file_name) + ".v.html"

        writeRTL_HTML(rtl_file, html_file_path, css_file_path)    

###################
# MAIN
###################

if(__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="Create a series of HTML pages containing RTL code")

    parser.add_argument("rtl_files", nargs='+', metavar="<file>.v", 
                        help="Path to verilog files.")
    parser.add_argument("out_dir", metavar="dir_name", 
                        help="Path to a directory that will contain the output files")

    args = parser.parse_args()

    print(f"Number of Verilog files: {len(args.rtl_files)}")

    create_RTL_HTML(args.rtl_files, args.out_dir)