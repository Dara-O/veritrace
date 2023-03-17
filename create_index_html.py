import os
import argparse
import xml.etree.ElementTree as ET

# Notes:
#   - connectivity html filename format: [folder_name][/]<instance_hier>.html
#       - <instance_hier> has instance names separated by dots '.' 
#   - Index html filename format: [folder_name][/]index.html

# forward declaration for type-hints
class Node:
    pass

class Node:

    def __init__(self, name, parent, children: list[Node]=[], node_info_dict: dict=dict()):
        self.name = name
        self.parent = parent
        self.children = children
        self.node_info_dict = node_info_dict

    def getHierPath(self) -> str:
        """
        Returns:

        String, Dot separated hierarchy of node names
        """

        result = self.name

        if(self.parent is not None):
            result = self.parent.getHierPath() + "." + result
        
        return result
    
    def getAllChildren(self) -> list[Node]:
        
        result = [] + self.children

        for child in self.children:
            result.extend(child.getAllChildren())
        
        return result

class DesignTree:

    def __init__(self, top_module: Node):
        
        self.top_module = top_module

    def grow(self, hier_path: str, node_info: dict=dict()) -> Node:
        """
        Returns 

        Newly created Node

        Parameters:

        hier_path   :   string, dot separated hierarchical path of the node
        
        node_info   :   dict, extra info to be associated with the newly...
                        ...created node
        """

        current_node = self.top_module

        # first instance name is typically the top module
        for i, instance_name in enumerate(hier_path.split('.')[1:]):

            children_names = list(map(lambda c: c.name, current_node.children))

            if(instance_name in children_names):
                child_idx = children_names.index(instance_name)
                current_node = current_node.children[child_idx]
            else:
                new_child_node = Node(instance_name, current_node, [])
                current_node.children.append(new_child_node)
                current_node = new_child_node

        current_node.node_info_dict = node_info

        return current_node

def writeCSS(file_path: str):
    # Some of the CSS code below was inspired by:
    # https://iamkate.com/code/tree-views/

    out_str = \
"""
#banner {
    border: 1px solid;
    padding: 10px;
    box-shadow: 5px 10px #888888;
}

body {
    font-family: sans-serif;
    background-color: #fafafa;
}

a:hover {
    background-color: #c6f7ed;
    ;
}

.tree {
    --spacing: 1.5rem;
    --radius: 1px;
    --top_padding: 3px;
}

/* Padding */

.tree li {
    display: block;
    position: relative;
    padding-left: calc(2 * var(--spacing) - var(--radius) - 2px);
    padding-top: var(--top_padding);
}

.tree ul {
    margin-left: calc(var(--radius) - var(--spacing));
    padding-left: 0;
    padding-top: var(--top_padding);
}

/* Vertical lines */

.tree ul li {
    border-left: 2px solid #ddd;
}

.tree ul li:last-child {
    border-color: transparent;
}

/* Horizontal lines */

.tree ul li::before {
    content: '';
    display: block;
    position: absolute;
    top: calc(var(--spacing) / -2);
    left: -2px;
    width: calc(var(--spacing) + 2px);
    height: calc(var(--spacing) + 1px);
    border: solid #ddd;
    border-width: 0 0 2px 2px;
}
"""

    with open(file_path, "w") as f:
        f.write(out_str)

def buildDesignTree(instances: list[str]) -> DesignTree:
    """
    Returns:

    A DesignTree object

    Parameters:

    instances   :   list of strings, where each string...
                    ...contains the hierarchical paths for each...
                    ...instance in the design. 
                    The top Module is expected to be the first element.
                    The format of the string: 
                        <parent>.<child>.<grandchild> (<grandchild module name>)
    """

    instance_parts = instances[0].split(' ', maxsplit=1)
    info_dict = {"module_name": instance_parts[1].strip()}

    top_node = Node(instance_parts[0].strip(), None, [], info_dict)
    design_tree = DesignTree(top_module=top_node)

    for instance in instances[1:]:
        instance_parts = instance.split(' ', maxsplit=1) 

        instance_hier = instance_parts[0].strip()
        current_node_info = {"module_name": instance_parts[1].strip()}
        current_node = design_tree.grow(instance_hier, current_node_info)

    return design_tree

def writeIndexHTML(file_path: str, design_tree: DesignTree, css_filename: str):
    """
    Responsibility:

    Writes an HTML file with an expandable tree view of the...
    ...design hierarchy
    
    Parameters:

    file_path   :   str, output file path

    design_tree  :  DesignTree object

    css_filename :  str, filename of css file that styles the html page.
                    It is assumed that the css file is in the same...
                    ...directory as the index html file
    """

    # xe == xml element
    html_xe = ET.Element("html")

    head_html_xe = ET.SubElement(html_xe, "head")
    
    # link css file
    link_h_html_xe = ET.SubElement(head_html_xe, "link")
    link_h_html_xe.set("rel", "stylesheet")
    link_h_html_xe.set("href", css_filename)

    # add title
    html_page_title = "Design Hierarchy Index"
    title_h_html_xe = ET.SubElement(head_html_xe, "title")
    title_h_html_xe.text = html_page_title

    body_html_xe = ET.SubElement(html_xe, "body")
    
    ## write banner
    HEADER_TAG = "h3"
    div_body_html_xe = ET.SubElement(body_html_xe, "div")
    div_body_html_xe.set("id", "banner")
    header_d_body_html_xe = ET.SubElement(div_body_html_xe, HEADER_TAG)
    header_d_body_html_xe.text = "Design Hierarchy Index"
    p_d_body_html_xe = ET.SubElement(div_body_html_xe, "pre")
    p_d_body_html_xe.text = "Usage:\n"+\
                            "- Each entry shows '<instance_name> (<module_name>)'. The <module_name> may be parametrized\n" +\
                            "- Each link leads to the connectivity table for that instance\n"+\
                            "- Refresh the page to collapse all levels.\n" +\
                            "- A link to this index can be found at the bottom of the connectivity table."

    ## write hierarchy
    top_ul_html_xe = ET.SubElement(body_html_xe,  "ul")
    top_ul_html_xe.set("class", "tree")
    top_li_html_xe = ET.SubElement(top_ul_html_xe, "li")
    top_details_html_xe = ET.SubElement(top_li_html_xe, "details")
    top_summary_html_xe = ET.SubElement(top_details_html_xe, "summary")
    
    # link to connectivity table for top module
    # format: "<instance hierarchical path>.html". Eg: top.cpu.cache.html
    top_instance_name = design_tree.top_module.name
    connectivity_table_html_link = top_instance_name + ".html"
    a_ts_html_xe = ET.SubElement(top_summary_html_xe, "a")
    a_ts_html_xe.set("href", connectivity_table_html_link)
    a_ts_html_xe.text = top_instance_name + " " +\
                        design_tree.top_module.node_info_dict["module_name"]

    # build tree view
    design_tree_dict = {design_tree.top_module.getHierPath(): top_details_html_xe}

    for node in design_tree.top_module.getAllChildren():
        hier_parts = node.getHierPath().split(".")
        
        parent_hier = ".".join(hier_parts[:-1])
        child_name = hier_parts[-1]

        if(parent_hier in design_tree_dict):
            ul_html_xe = ET.SubElement(design_tree_dict[parent_hier], "ul")
            li_html_xe = ET.SubElement(ul_html_xe, "li")

            if(len(node.children) == 0):
                a_ts_html_xe = ET.SubElement(li_html_xe, "a")
                a_ts_html_xe.set("href", connectivity_table_html_link)
                a_ts_html_xe.text = child_name + " " + \
                                    node.node_info_dict["module_name"]
                
            else:
                details_html_xe = ET.SubElement(li_html_xe, "details")
                summary_html_xe = ET.SubElement(details_html_xe, "summary")

                # link module connectivity table
                child_hier_path = ".".join(hier_parts) 
                
                connectivity_table_html_link = child_hier_path + ".html"
                a_ts_html_xe = ET.SubElement(summary_html_xe, "a")
                a_ts_html_xe.set("href", connectivity_table_html_link)
                a_ts_html_xe.text = child_name + " " + \
                                    node.node_info_dict["module_name"]
                
                design_tree_dict[child_hier_path] = details_html_xe
                
        else:
            # This shouldn't happen since children are gotten through Depth-First Traversal
            raise Exception(f"HTML entry for parent of '{'.'.join(hier_parts)}' not created yet")

    html_xe = ET.ElementTree(html_xe)
    ET.indent(html_xe)        
    html_xe.write(file_path, method='html', short_empty_elements=False)
    
def writeIndex(out_dir: str, instances: list[str], index_filename: str) -> str:
    """
    Returns:

    String, filepath of the newly created html file
    
    Parameters:

    out_dir     :   string, path to output directory where the files will be placed.

    instances   :   list of strings, where each string...
                    ...contains the hierarchical paths for each...
                    ...instance in the design. 
                    The top Module is expected to be the first element.
                    The format of the string: 
                        <parent>.<child>.<grandchild> (<grandchild module name>)
    """
    design_tree = buildDesignTree(instances)

    css_filename = "index_style.css"
    css_fpath = os.path.join(out_dir, css_filename)

    writeCSS(css_fpath)

    html_file_name = index_filename
    html_fpath = os.path.join(out_dir, html_file_name)
    writeIndexHTML(html_fpath, design_tree, css_filename)
    
    return html_fpath

if(__name__ == "__main__"):
        
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("instances_file", 
                        help="Path to a file containing instance hierarchies on separate lines.\n"+\
                            "Eg: '<parent>.<child>.<grandchild> (<grandchild module name>)'")
    parser.add_argument("out_dir", 
                        help="Path to output directory. Files will be written there")
    args = parser.parse_args()

    instances = []
    with open(args.instances_file, "r") as f:
        instances = f.readlines() 

    writeIndex(args.out_dir, instances)