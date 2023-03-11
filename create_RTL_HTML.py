import os 
import re
import argparse
import xml.etree.ElementTree as ET

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

    # FIXME: Consider reading the css file from a...
    # ...template rather than hardcoding it
    css_text = \
"""
p {
    font-family: sans-serif;
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
    width: 8em;         
    padding-left: auto; 
    margin-left: auto;  
    text-align: right;  
}
/* Section Animation */
@import "compass/css3";

:target {
    -webkit-animation: target-fade 1.5s;
    -moz-animation: target-fade 1.5s;
    -o-animation: target-fade 1.5s;
    animation: target-fade 1.5s;
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
    with open(rtl_file_path, "r") as f:
        rtl_file_txt = f.read()

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
    html_xe.write(html_file_path, method='html', short_empty_elements=False)

    return html_file_path

    # write the name of the RTL file as a header...
    # Eg:
    #   **Filename**: instruction_cache.v

    # Next, RTL code listing:
    # Inspiration
    # - https://stackoverflow.com/questions/41306797/html-how-to-add-line-numbers-to-a-source-code-block
    # - https://www.hdlworks.com/products/companion/eth_html/fuz_a0a0a070bc038d162af15600c378a62f.htm#Line_75 


parser = argparse.ArgumentParser(description="Create a series of HTML pages containing RTL code")

parser.add_argument("rtl_files", nargs='+', metavar="<file>.v", help="Path to verilog files.")
parser.add_argument("out_dir", metavar="dir_name", 
                    help="Path to a directory that will contain the output files")

args = parser.parse_args()

print(f"Number of Verilog files: {len(args.rtl_files)}")

# write css file
css_file_path = writeCSSFile(args.out_dir)

for rtl_file in args.rtl_files:
    rtl_file_name = os.path.basename(rtl_file).split(".")[:-1]
    rtl_file_name = ".".join(rtl_file_name)

    html_file_path = os.path.join(args.out_dir, rtl_file_name) + ".html"

    writeRTL_HTML(rtl_file, html_file_path, css_file_path)