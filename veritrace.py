import argparse
import xml.etree.ElementTree as ET
import os
import threading

from create_RTL_HTML    import create_RTL_HTML
from create_index_html  import writeIndex


# Notes:
#   - connectivity html filename format: [folder_name][/]<instance_hier>.html
#       - <instance_hier> has instance names separated by dots '.' 
#   - RTL HTML File format: [folder_name][/]<module_name>.v.html
#   - Design tree file format: [folder_name][/]index.html

def elaborateLocs(loc_str :str, files_xml_element: ET.Element) -> str:
    """
    Responsibility:

    Replace file ids with actual file path

    Returns:

    String

    Parameters:

    loc_str :   str, string containing location, 'loc', for a given entity. 
                Eg: "c,80,33,80,48"

    files_xml_element   :   an xml.etree.ElementTree.Element object containing mapping between file ids and file paths.
                            Gotten from the xml produced by Verilator

    """

    file_id = loc_str.split(",")[0]

    file_xml_element = files_xml_element.find(f"file[@id='{file_id}']")
    
    out = loc_str.replace(file_id, file_xml_element.get('filename'))

    return out

def hexToDec(hex_str: str) -> str:
    """
    Returns

    String, Decimal equivalent of hex number 

    Parameters:

    hex_str :   string, hex number written in verilog style. 
                Eg:
                32'sh0
                32'hf
                4'ha
    """

    hex_num = hex_str.split('h')[-1]
    int_num = int(hex_num, 16)

    return int_num

def elaborateDtypeId(dtype_id: str, typetable_xml_element: ET.Element) -> dict:
    """
    Responsibility:

    Replace file ids with actual file path

    Returns:

    Dict with keys "type", "dim" 

    Parameters:

    loc_str :   str, datatype id ('dtype_id') for a given entity. 
                Id is typically a number
                Eg: "2"

    typetable_xml_element  :    an xml.etree.ElementTree.Element object containing...
                                ...mapping between dtpye_ids and typtable ids.
                                Gotten from the xml produced by Verilator

    """

    basicdtype_xml_element = typetable_xml_element.find(f"basicdtype[@id='{dtype_id}']")
    unpackarraydtype_xml_element = typetable_xml_element.find(f"unpackarraydtype[@id='{dtype_id}']")
    
    type_str = ""
    dim_str = ""
    if(basicdtype_xml_element is not None):
        type_str = basicdtype_xml_element.get('name')
        dim_str = f"[{basicdtype_xml_element.get('left')}:{basicdtype_xml_element.get('right')}]"
    elif(unpackarraydtype_xml_element is not None):
        type_str = "array"

        # get limits describing the number of rows
        arr_range_limits = unpackarraydtype_xml_element.findall("./range/const")
        left_array_limit = hexToDec(arr_range_limits[0].get('name').replace('&apos', "'"))
        right_array_limit = hexToDec(arr_range_limits[1].get('name').replace('&apos', "'"))

        # get limits describing the number of columns
        sub_type_id = unpackarraydtype_xml_element.get('sub_dtype_id')
        sub_type_xml_element = typetable_xml_element.find(f"basicdtype[@id='{sub_type_id}']")
        left_col_limit = sub_type_xml_element.get('left')
        right_col_limit = sub_type_xml_element.get('right')

        dim_str = f"[{left_array_limit}:{right_array_limit}] [{left_col_limit}:{right_col_limit}]"
        
    dim_str = dim_str.replace("None", "0")
    
    out_dict = {"type" : type_str, "dim" : dim_str}
    
    return out_dict

class ConstLiteral():
    """
    Represents:

    Contant value typically used to tieoff ports
    """

    def __init__(self, xml_element, parent_obj, root):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the constant

        parent_obj  : a reference to the ModuleInstance where this constant is used. 
                      This object contains an xml element that is the ancestor of 'xml_element'

        root        : object of Type ModuleDef, represents the root module in the design
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root

class Var():
    """
    Represents a Verilog Variable. This may be:
        - param or localparam
        - reg or wire
    """

    def __init__(self, xml_element, parent_obj, root):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Var

        parent_obj  :   module where this var is found

        root        : object of Type ModuleDef, represents the root module in the design
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root

    def getHierPath(self) -> str:
        """
        Returns:

        A string denoting the hierarchical path to this entity in rtl
        """
        return self.parent_obj.getHierPath() + "." + self.xml_element.get('name')
    
    def findVarLoads(self):
        """
        Returns 
        
        List of objects which are loads of this variable
            Note:
            - Objects may be:
                - port
                - var
        """

        return self.parent_obj.findVarLoads(self.xml_element.get('name'))
    
    def findVarDrivers(self):
        """
        Returns 
        
        List of objects which are loads of this variable
            Note:
            - Objects may be:
                - port
                - var
                - const
        """

        return self.parent_obj.findVarDrivers(self.xml_element.get('name'))

class ConstVar(Var):
    """
    Represtents 
    
    A constant value typically used to drive vars like local params.
    This type of Const Var is found in assignments
    """

    def __init__(self, xml_element, parent_obj, root) -> None:
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the constant

        parent_obj  : a reference to the object where this constant is defined. 
                      This object contains an xml element that is the ancestor of 'xml_element'

        root        : object of Type ModuleDef, represents the root module in the design
        """

        super().__init__(xml_element, parent_obj, root)

class Assign():
    """
    Represents assignments made in modules. There can be three types of assigns:
        - assign
        - assigndly
        - contassign
    """

    def __init__(self, xml_element, parent_obj, root) -> None:
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Assignment tag

        parent_obj  : an object which is an ancestor of this object (according to xml hierarchy)
                        This is typically a Module 

        root        : object of Type ModuleDef, represents the root module in the design
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root

        self.drivers_xml = Assign.getDrivers(xml_element)
        self.loads_xml = Assign.getLoads(xml_element)

    def getLoads(xml_element) -> list:
        """
        Returns 
        
        A list of xml.etree.ElementTree.Element objects. 
            Note:
            - These objects represent elements that are on left-hand side of the assignment operator

        Parameters:
        
        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the assignment
        """

        out = []

        children = xml_element.findall("./*")

        # the last child is typically the load
        last_child = children[-1]

        repeat = True
        while(repeat):
            repeat = False
            if(last_child.tag == "varref"):
                out.append(last_child)
            elif(last_child.tag == "concat"):
                out.extend(
                    list(last_child.iter('varref'))
                )
            elif(last_child.tag == "arraysel" or last_child.tag == "sel"):
                # the first varref is typically the load
                potential_load = last_child.find("varref")

                # handling of nested array selection to find true load 
                if(potential_load == None):
                    potential_load = last_child.find("arraysel")

                    # the first varref in arraysel tags tends to be the load
                    if(potential_load != None):
                        potential_load = potential_load.find("varref")
                        out.append(potential_load)
                    else:
                        potential_loads = list(last_child.iter("varref"))
                        if (potential_loads != None):
                            out.extend(potential_loads) 
                        print(f"Please inspect XML tag '{last_child.tag}'"+ \
                              f"with attributes {last_child.attrib}. "+\
                                "Getting all 'varref's in this assignment statement. "+\
                                "Some may not be true loads"
                            )
                else:
                    out.append(potential_load)

            elif(last_child.tag == "delay"):
                # child before delay tag is contains the load(s)
                last_child = children[children.index(last_child)-1]
                repeat = True
            else:
                raise Exception(f"Unnexpected tag type '{last_child.tag}' with attribues: '{last_child.items()}'")

        return out
    
    def getDrivers(xml_element) -> list:
        """
        Returns 
        
        A list of xml.etree.ElementTree.Element objects. 
            Note:
            - These objects represent elements that are on right-hand side of the assignment operator

        Parameters:
        
        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the assign
        """

        out = []

        children = xml_element.findall("./*")
        
        driver_children = None
        if(children[-1].tag == 'delay'):
            # When last child is a delay, every child except the second...
            # ...to last child are typically drivers
            driver_children = children[:-2]
        elif(children[-1].tag == 'sel'):
            
            driver_children = []

            # find all variables which may be indexes for the array
            children_arraysels = list(children[-1].iter("arraysel"))
            
            for children_arraysel in children_arraysels:
                
                driver_children.append(children_arraysel.find("varref[last()]"))

            # find all variables which may be indexes for the vector
            children_sel_varrefs = children[-1].findall("varref")
            if(len(children_arraysels) > 1):
                driver_children.extend(children_sel_varrefs[1:])

        else:
            # Every child except the last child are typically drivers
            driver_children = children[:-1]

        for driver_child in driver_children:
            if(driver_child.tag != "varref" and driver_child.tag != "const"):
                out.extend(
                    list(driver_child.iter("varref")) + \
                    list(driver_child.iter("const"))
                )
            else:
                out.append(driver_child)

        return out

class InstancePort():
    """
    Represents ports on module instances
    """

    _CONNECTION_TYPES = ["varref", "const"]

    def __init__(self, xml_element, parent_obj, root):
        """
        Parameters:

        xml_element :   an xml.etree.ElementTree.Element object. This object is...
                        ...the xml node that defines the Instanceport

        parent_obj  :   a reference to the Instance object where this port is defined. 
                        This object contains an xml element that is the ancestor of 'xml_element'

        root        :   object of Type ModuleDef, represents the root module in the design
        """
        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root

        self.connections = self._populateVarConnections(xml_element)

    def _populateVarConnections(self, xml_element):
        """
        Returns 
        
        A dictionary. 
            - The key is the name of the variable connected to instance port
            - The value is the xml_element


        Parameters:

        xml_element :   an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Instanceport to be search for connections
        """
        
        out_dict = dict()
        
        for connection_type in InstancePort._CONNECTION_TYPES:
            for varref_xml in xml_element.iter(connection_type):
                out_dict[varref_xml.get('name')] = varref_xml

        return out_dict
    
    def getHierPath(self):
        """
        Returns

        A string denoting the hierarchical path to this entity in rtl
        """

        out = ""

        if(self.parent_obj is None):
            Exception(f"InstancePort '{self.xml_element.get('name')}' has no parent."\
                        +f" XML element attributes: {self.xml_element.items()}")
        else:
            out = self.parent_obj.getHierPath() + "." + self.xml_element.get('name')

        return out

    def findVarLoads(self):
        """
        Returns 
        
        List of objects which are loads of this port
            Note:
            - Objects may be:
                - port
                - var
        """

        return self.parent_obj.findVarLoads(self.xml_element.get('name'))
    
    def findVarDrivers(self):
        """
        Returns 
        
        List of objects which are drivers of this port
            Note:
            - Objects may be:
                - port
                - var
        """

        return self.parent_obj.findVarDrivers(self.xml_element.get('name'))

class ModuleInstance():
    """
    Represent a module instatiation
    """

    def __init__(self, xml_element, xml_modules, parent_obj, root):
        """
        Parameters:

        xml_element :   an xml.etree.ElementTree.Element object. This object is...
                        ...the xml node that defines the Instance
        
        xml_modules :   list of xml.etree.ElementTree.Elements objects for all submodules
        
        parent_obj  :   module where this instance is found

        root        :   object of Type ModuleDef, represents the root module in the design
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root
    
        self.module_def = self._createModuleDef(xml_element, xml_modules, root)
        self.ports = self._populateInstancePorts(xml_element, root)
        self.output_ports = self._populateOutputPorts(self.ports)
        self.input_ports = self._populateInputPorts(self.ports)
        self.output_ports_dict = self._populateOutputPortDict(self.output_ports)
        self.input_ports_dict = self._populateInputPortDict(self.input_ports)

    def _createModuleDef(self, xml_element, xml_modules, root):
        """
        Returns:

        ModuleDef object which represents the definition for this instance

        Parameters:

        xml_element :   an xml.etree.ElementTree.Element object. This object is...
                        ...the xml node that defines the Instancee
        
        xml_modules : list of xml.etree.ElementTree.Elements objects for all submodules

        root        : object of Type ModuleDef, represents the root module in the design
        """

        out = None

        for xml_module in xml_modules:

            if(xml_module.get("name") == xml_element.get("defName")):
                out = ModuleDef(xml_module, xml_modules, self, root)
                break
        
        if(out == None):
            raise Exception(f"Module instance '{xml_element.get('name')}' with" \
                            +f" defName '{xml_element.get('defName')}' has no definition")

        return out

    def _populateInstancePorts(self, xml_element, root):
        """
        Return 

        List of InstancePort objects

        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the instance to be searched for ports

        root        :   object of Type ModuleDef, represents the root module in the design
        """

        out = []

        for port in xml_element.iter("port"):
            out.append(InstancePort(port, self, root))
        
        return out

    def _populateOutputPorts(self, ports) -> list:
        """
        Returns 

        A list of InstancePort objects

        Parameters:

        ports   :   list of InstancePort Objects
        """

        out = []

        for port in ports:
            if(port.xml_element.get('direction') == "out"):
                out.append(port)

        return out

    def _populateInputPorts(self, ports) -> list:
        """
        Returns 

        A list of InstancePort objects

        Parameters:

        ports   :   list of InstancePort Objects
        """

        out = []

        for port in ports:
            if(port.xml_element.get('direction') == "in"):
                out.append(port)

        return out

    def _populateOutputPortDict(self, output_ports_objs: list) -> dict:
        """
        Return 
        A dictionary:
            - keys   : string, output port names
            - values : InstnacePortObjects

        Parameters:

        output_ports_objs   :   list of InstancePort objects. These objects...
                                ...are the output ports belonging to this InstanceModule
        """

        return { output_port_obj.xml_element.get('name') : output_port_obj for output_port_obj in output_ports_objs }
    
    def _populateInputPortDict(self, input_ports_objs: list) -> dict:
        """
        Return 

        A dictionary:
            - keys   : string, output port names
            - values : InstnacePortObjects

        Parameters:

        input_ports_objs   :    list of InstancePort objects. These objects...
                                ...are the input ports belonging to this InstanceModule
        """

        return { input_port_obj.xml_element.get('name') : input_port_obj for input_port_obj in input_ports_objs }

    def findOutputLoads(self, port_name: str) -> list:
        """
        Return

        List of two-entry tuples:
            1) Object which includes:
                - Var
            
            2) Location of the connection. Eg: "c,32,2,32,6" 
                Explanation for example: "<file_id>,<line_no>,<begin_col_no>,<line_no>,<end_col_no>"

        Parameters:

        port_name   :   string, name of the output port whose ...
                        ...external loads should be found.
        """

        # check if port_name is actually an output port
        if(port_name not in self.output_ports_dict):
            raise Exception(f"{port_name} is not an output port. Valid output ports include: "\
                            +f"{', '.join(self.output_ports_dict.keys())}")

        out = []

        # find port & names of its connections
        port_connection_names = self.output_ports_dict[port_name].connections.keys()
        
        # convert connection names to variable objects
        for port_connection_name in port_connection_names:
            var_obj = self.parent_obj.findVar("."+port_connection_name)

            # check that only vars are connected to the output port
            if(var_obj.xml_element.tag != "var"):
                raise Exception(f"'{port_name}' is connected to an entity that isn't a var. That entity's"\
                                +f"properties includes '{var_obj.items()}'")

            connection_loc = self.output_ports_dict[port_name].connections[port_connection_name].get('loc')
            out.append((var_obj, connection_loc))
        
        return out
    
    def findInputDrivers(self, port_name: str) -> list:
        """
        Return

        List of  two-entry tuples:
            1) Object which includes:
                - Var
                - ConstVar
                - ConstLiteral
            2) location of connection between port name and driver

        Parameters:

        port_name   :   string, name of the input port whose ...
                        ...external drivers should be found.
        """

        # check if port_name is actually an input port
        if(port_name not in self.input_ports_dict):
            raise Exception(f"{port_name} is not an input port. Valid input ports include: "\
                            +f"{', '.join(self.input_ports_dict.keys())}")

        out = []

        # find port & names of its connections
        port_connection_names = self.input_ports_dict[port_name].connections.keys()
        
        # convert connection names to variable objects
        for port_connection_name in port_connection_names:

            if(ModuleDef.nameContainsConstIndicators(port_connection_name)):
                const_xml_element = self.input_ports_dict[port_name].connections[port_connection_name]
                const_assign_loc = const_xml_element.get('loc')
                out.append((ConstLiteral(const_xml_element, self, self.root), 
                            const_assign_loc))
            else:
                var_obj = self.parent_obj.findVar("."+port_connection_name)
                connection_loc = self.input_ports_dict[port_name].connections[port_connection_name].get('loc')
                out.append((var_obj, connection_loc))
        
        return out

    def findVarDrivers(self, var_name: str):
        """
        Returns 
        
        List of two-entry Tuples:
            1) object which is a driver of the variable represented by 'var_name'
                Note:
                - Object may be:
                    - port
                    - var
                    - const

            2) string, location of where the driving happens. This location...
               ...could be pointing to an assignment or port connection. 
               Eg:
                "c,3,8,3,25"
               
               In the example above 'c' is the id of a file, both '3's refer...
                ...to the line number in the 'c' file. The second number ('8')...
                ...represents the column where the var name begins, while the...
                ...last number ('25') tells us when var name ends
        
        Parameters 

        var_name : string, Name of the variable whose drivers should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        return self.module_def.findVarDrivers(var_name)
    
    def findVarLoads(self, var_name: str):
        """
        Returns 
        
        List of two-entry tuples:
            1) object which are loads of 'var_name'
                Objects may be:
                    - port
                    - var
        
            2) Location of the connection. Eg: "c,32,2,32,6" 
                Explanation for example: "<file_id>,<line_no>,<begin_col_no>,<line_no>,<end_col_no>"

        Parameters 

        var_name : string, Name of the variable whose loads should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        return self.module_def.findVarLoads(var_name)
    
    def getHierPath(self) -> str:
        """
        Returns:

        A string denoting the hierarchical path to this entity in rtl
        """

        out = ""

        if(self.parent_obj is None):
            Exception(f"ModuleInstance '{self.xml_element.get('name')}' has no parent."\
                        +f" XML element attributes: {self.xml_element.items()}")
        else:
            out = self.parent_obj.getHierPath() + "." + self.xml_element.get('name')

        return out

class ModuleDef():
    """
    Represent a module definition
    """

    __CONST_INDICATOR_1 = "&apos"
    __CONST_INDICATOR_2 = "'"

    def __init__(self, 
                 xml_element: ET.Element, 
                 xml_modules: list, 
                 parent_obj: ModuleInstance=None, 
                 root=None):
        """
        Params:

        xml_element : xml.etree.ElementTree.Element object

        xml_modules :   list of xml.etree.ElementTree.Elements objects...
                        ...for all submodules. 
        
        parent_obj  :   ModuleInstance object, which is an instance in RTL of This module type

        root        : ModuleDef Object, The root module in the design heirarchy
        """
        
        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.root = root

        if(parent_obj is None):
            self.instances = self._populateInstances(xml_element, xml_modules, self)
            self.vars = self._populateVars(xml_element, self)
        else:
            self.instances = self._populateInstances(xml_element, xml_modules, root)
            self.vars = self._populateVars(xml_element, root)

        assert(len(self.vars) > 0 and f"Number of Variables in '{xml_element.get('name')}' is zero")


        self.input_vars = self._populateInputVars(self.vars)
        self.output_vars = self._populateOutputVars(self.vars)
        self.assigns = self._populateAssigns(xml_element, root)

    def _populateAssigns(self, xml_element, root):
        """
        Returns

        List of Assign Objects

        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the module to be searched for assignment tags. 
                      There are 3 kinds of assings:
                        - assign
                        - assigndly
                        - contassign

        root        : ModuleDef Object, The root module in the design heirarchy
        """

        out = []

        # get all *assign* tags in the module (analogous to assignments in an RTL Module)
        for assign_type in ["contassign", "assign", "assigndly"]:
            for assign in xml_element.iter(assign_type):
                out.append(Assign(assign, self, root))

        return out

    def _populateInputVars(self, vars: list[Var]) -> list[Var]:
        """
        Returns 
        
        List of var objects

        Parameters:

        vars    :   list of Var objects, These objects must be immediate children...
                    ...of this ModuleDef 
        """
        
        out = []
        for var in vars:
            if(var.xml_element.get('dir') == "input"):
                out.append(var)

        return out
    
    def _populateOutputVars(self, vars: list[Var]) -> list[Var]:
        """
        Returns 
        
        List of var objects

        Parameters:

        vars    :   list of Var objects, These objects must be immediate children...
                    ...of this ModuleDef 
        """
        
        out = []
        for var in vars:
            if(var.xml_element.get('dir') == "output"):
                out.append(var)

        return out

    def _populateInstances(self, 
                           xml_element: ET.Element, 
                           xml_modules: list[ET.Element], 
                           root) -> list:
        """
        Returns: 

        List of ModuleInstances

        Parameters:

        xml_element : object of type 'xml.etree.ElementTree.Element', This Element contains xml data that...
                      ...defines this module

        xml_modules : list of xml.etree.ElementTree.Elements objects for all submodules

        root        : object of Type ModuleDef, represents the root module in the design
        """

        out = []

        for xml_instance in xml_element.iter("instance"):
        
            out.append(ModuleInstance(xml_instance, xml_modules, self, root))

        return out

    def _populateVars(self, xml_element: ET.Element, root) -> list:
        """
        Returns:

        List of Vars

        Parameters:

        xml_element : object of type 'xml.etree.ElementTree.Element', This Element contains xml data that...
                      ...defines this module

        root        : object of Type ModuleDef, represents the root module in the design
        """

        out = []

        for var in xml_element.iter("var"):
            out.append(Var(var, self, root))

        return out

    def getHierPath(self) -> str:
        """
        Returns:

        A string denoting the hierarchical path to this entity in rtl
        """

        out = ""

        if(self.parent_obj is None):
            out = self.xml_element.get('name')
        else:
            out = self.parent_obj.getHierPath()

        return out

    def findVar(self, hier_path: str) -> Var:
        """
        Returns:

        Var object at the given hierarchical path. None if var object not found.

        Parameters:

        hier_path   :   string, hierarchical path to a target variable. Hierarchies are...
                        ...separated by periods "." and are relative to this module.
                        The first character in this parameter should be a period ".".

                        Eg (searching from current module):
                            fileVar(self, ".rel_lvl1_module.rel_lvl2_module.var_name")
        """

        out = None

        # enforce hier_path begining with period
        if(hier_path[0] != '.'):
            raise Exception(f"hier_path '{hier_path}' doesn't begin with a period "+"\".\"")

        
        path_stages = hier_path[1:].split('.', 1)

        # if path contains only var name
        if(len(path_stages) == 1):
            for var in self.vars:
                if(path_stages[-1] == var.xml_element.get('name')):
                    out = var
        else:
            # find instance whose name matches first path
            for instance in self.instances:
                if(path_stages[0] == instance.xml_element.get('name')):
                    out = instance.module_def.findVar("."+".".join(path_stages[1:]))
            
        return out

    def getAllVars(self):
        """
        Retunrs:

        A list of Var objects
        """

        out = self.vars

        for instance in self.instances:
            out = out + instance.module_def.getAllVars()

        return out

    def getAllInstances(self):
        """
        Retunrs:

        A list of ModuleInstance objects
        """

        out = self.instances

        for instance in self.instances:
            out = out + instance.module_def.getAllInstances()

        return out
    
    def findVarDrivers(self, var_name: str) -> list[tuple]:
        """
        Returns 
        
        List of two-entry Tuples:
            1) object which is a driver of the variable represented by 'var_name'
                Note:
                - Object may be:
                    - port
                    - var
                    - const

            2) string, location of where the driving happens. This location...
               ...could be pointing to an assignment or port connection. 
               Eg:
                "c,3,8,3,25"
               
               In the example above 'c' is the id of a file, both '3's refer...
                ...to the line number in the 'c' file. The second number ('8')...
                ...represents the column where the var name begins, while the...
                ...last number ('25') tells us when var name ends

        Parameters: 

        var_name    :   string, Name of the variable whose drivers should be found. 
                        The variable must be a child of the module (i.e. self)
        """

        drivers = []

        # only check instance ports and assigns when var is not an input...
        # ...since inputs can't be driven internally
        if(self.findVar("."+var_name).xml_element.get('dir') != "input"):

            # check instance ports
            for instance in self.instances:
                for output_instance_port in instance.output_ports:
                    if(var_name in output_instance_port.connections):
                        drivers.append((output_instance_port, 
                                        output_instance_port.connections[var_name].get('loc')))
        
            # check all the *assign* nodes (or statement)
            for assign in self.assigns:

                # get the loads and drivers in this *assign* node 
                assign_loads_xml = assign.loads_xml
                assign_drivers_xml = assign.drivers_xml

                assign_contains_drivers = False
                # check if var_name is a load in this assign node
                for assign_load_xml in assign_loads_xml:
                    
                    if(assign_load_xml.get('name') == var_name):
                        assign_contains_drivers = True
                        break
                
                if(assign_contains_drivers):
                    # append all drivers in this assign
                    for assign_driver_xml in assign_drivers_xml:
                        
                        if(ModuleDef.nameContainsConstIndicators(assign_driver_xml.get('name'))):
                            drivers.append((ConstVar(assign_driver_xml, self, self.root),
                                            assign_driver_xml.get('loc')))
                        else:
                            drivers.append((
                                self.findVar("."+assign_driver_xml.get('name')),
                                assign_driver_xml.get('loc')
                            ))

        # find external loads if var is an output port and module is an instance
        elif(self.parent_obj is not None):
            drivers.extend(self.parent_obj.findInputDrivers(var_name))

        return drivers

    def findVarLoads(self, var_name: str) -> list[tuple]:
        """
        Returns 
        
          List of two-entry Tuples:
            1) object which is a load of the variable represented by 'var_name'
                Note:
                - Objects may be:
                    - port
                    - var

            2) string, location of where the loading happens. This location...
               ...could be pointing to an assignment or port connection. 
               Eg:
                "c,3,8,3,25"
               
               In the example above 'c' is the id of a file, both '3's refer...
                ...to the line number in the 'c' file. The second number ('8')...
                ...represents the column where the var name begins, while the...
                ...last number ('25') tells us when var name ends

        Parameters: 

        var_name : string, Name of the variable whose loads should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        loads = []

        # check instance ports
        for instance in self.instances:
            for input_instance_port in instance.input_ports:
                if(var_name in input_instance_port.connections):
                    loads.append((input_instance_port,
                                 input_instance_port.connections[var_name].get('loc')))

        # check all the *assign* nodes (or statements)
        for assign in self.assigns:

            # get the loads and drivers in this *assign* node 
            assign_loads_xml = assign.loads_xml
            assign_drivers_xml = assign.drivers_xml

            assign_contains_loads = False
            # check if var_name is a driver in this assign node
            for assign_driver_xml in assign_drivers_xml:
                if(assign_driver_xml.get('name') == var_name):
                    
                    assign_contains_loads = True
                    break
            
            if(assign_contains_loads):
                # append all loads in this assign
                for assign_load_xml in assign_loads_xml:
                    loads.append((
                        self.findVar("."+assign_load_xml.get('name')),
                        assign_load_xml.get('loc')
                    ))

        # find external loads if var is an output port and module is an instance
        if(
                (self.parent_obj is not None )
            and (self.findVar("."+var_name).xml_element.get('dir') == "output") 
        ):
            loads.extend(self.parent_obj.findOutputLoads(var_name))

        
        return loads

    def getInstancePortConnections(self, instance_name: str, port_name: str) -> list:
        """
        Returns:

        List of Vars Objects or consts Objects. These objects represent...
        ...variables or constants connected to ports of instances (or subblocks)...
        ...within this module 

        Parameters:

        instance_name   :   string, name of instance whose port will be searched for connections

        port_name   :   string, name of port on the instance to search for connections
        """

        out = []

        instnace_obj = None

        # find instance
        for instance in self.instances:
            if(instance.xml_element.get('name') == instance_name):
                instnace_obj = instance
                break
        if(instnace_obj == None):
            Exception(f"Instance named '{instance_name}' can't be found in module '{self.xml_element.get('name')}'")

        # find port & names of its connections
        port_connection_names = []
        for port in instnace_obj.ports:
            if(port.xml_element.get('name') == port_name):
                port_connection_names = port.connections.keys()
                break
        
        # convert connection names to variable names
        for port_connection_name in port_connection_names:
            out.append(self.findVar("."+port_connection_name))
        
        return out

    def nameContainsConstIndicators(name: str) -> bool:
            """
            Returns

            True only if 'name' contains indications...
            ...that is is a const

            Parameters:

            name    :   string, 'name' attribute of (xml) element 
            """

            out =   (
                    ModuleDef.__CONST_INDICATOR_1 in name \
                or  ModuleDef.__CONST_INDICATOR_2 in name
            )
            
            return out

def _HTML_getVarName(var_name: str, 
                     rowspan: str, 
                     parent_xml_element: ET.Element,
                     misc_text="") -> ET.Element:
    """
    Returns 
    
    xml.etree.ElementTree.Element, a <td> htm tag with the variable name

    Parameter:

    rowspan : string, Number grater than 0
    """

    td_xml_element = ET.SubElement(parent_xml_element, 'td')
    td_xml_element.set('rowspan', str(rowspan))
    td_xml_element.set('id', var_name)

    p_xml_element = ET.SubElement(td_xml_element, "p")
    p_xml_element.text = var_name

    if(misc_text != ""):
        p_misc_xml_element = ET.SubElement(td_xml_element, "p")
        p_misc_xml_element.text = misc_text

    return td_xml_element

def _HTML_getVarInfo(var_info_dict: dict, 
                     rowspan: str, 
                     parent_xml_element: ET.Element,
                     misc_text: str="") -> ET.Element:
    """
    Returns 
    
    String, a <td> htm tag with the variable name

    Parameters:

    var_info_dict   :   dict, contains fields and values to...
                        be displayed in the Variable Info column. 
                        keys    -> string
                        values  -> string
                        
                        Note:
                        Expected keys include "type", "dim" and "loc"
    """
    # Note xml_element = xe
    td_xml_element = ET.SubElement(parent_xml_element, 'td')
    td_xml_element.set('rowspan', rowspan)

    for key, value in var_info_dict.items():
        p_xml_element = ET.SubElement(td_xml_element, "p")
        strong_xe = ET.SubElement(p_xml_element, "strong")
        strong_xe.text = key
        
        # add link to variable declaration in RTL HTML
        if(key == "loc"):
            strong_xe.tail = ": "

            a_xe = ET.SubElement(p_xml_element, "a")
        
            loc_parts = value.replace("/", "__").split(", ")
            rtl_html_fname = loc_parts[0]
            rtl_line_number = loc_parts[1].split(":")[0].strip()
            rtl_html_link = rtl_html_fname+".html"+"#"+str(rtl_line_number)
            a_xe.set("href", rtl_html_link)
            a_xe.text = str(value)
        else:
            strong_xe.tail = f": {value}"


    if(misc_text != ""):
        p_misc_xml_element = ET.SubElement(td_xml_element, "p")
        p_misc_xml_element.text = misc_text

    return td_xml_element

def _HTML_getVarDL(var:                 Var,
                   dl_loc_ls:           list,
                   parent_xml_element:  ET.Element,
                ):
    """
    Responsibility:

    Creates a HTML table entry for the driver/load variable/const
    
    Returns:

    td_xml_element : xml.etree.ElementTree.Element for the...
                        HTML data created by this function

    Parameters:

    var : if None, then a None is entered in the HTML table.
            Else, Var object
    
    dl_loc_ls  :    list of two items, location where driving/loading takes place.
                    1) string, file where driver-load connection is made
                    2) string, line number of where driver-load connection is made
    """

    # Note xml_element = xe
    # create table data
    td_xml_element = ET.SubElement(parent_xml_element, 'td')
    if(var == None):
        p_var_name_xe = ET.SubElement(td_xml_element, 'p')
        p_var_name_xe.text = "None"

    elif(var.xml_element.tag != "const"):
        h4_var_name_xe = ET.SubElement(td_xml_element, 'h4')
        h4_var_name_xe.text = var.xml_element.get("name")

        # create link to driver/load connectivity table
        p_var_link_xe = ET.SubElement(td_xml_element, 'p')
        a_var_link_xe = ET.SubElement(p_var_link_xe, 'a')

        var_hier = var.getHierPath()
        var_hier_wo_name = ".".join(var_hier.split('.')[:-1])
        instance_html_fpath =   var_hier_wo_name+".html#" +\
                                var.xml_element.get('name')

        a_var_link_xe.set("href", instance_html_fpath)

        # add link text
        a_var_link_xe.text = var_hier

        # create link to driver/load connection in RTL
        p_var_dl_loc_link_xe = ET.SubElement(td_xml_element, 'p')
        p_var_dl_loc_link_xe.text = "Examine RTL: "
        a_var_dl_loc_link_xe = ET.SubElement(p_var_dl_loc_link_xe, 'a')

        # create hyperlink to file
        html_file = dl_loc_ls[0].replace("//", "/").replace("/", "__")+".html"

        html_id = "#"+dl_loc_ls[1]
        a_var_dl_loc_link_xe.set("href", html_file+html_id)

        # add link text. "<filepath>:<line_number>"
        a_var_dl_loc_link_xe.text = dl_loc_ls[0].replace("//", "/") +":"+ dl_loc_ls[1]
    
    else: 
        # no link for constants
        p_var_name_xe = ET.SubElement(td_xml_element, 'p')
        p_var_name_xe.text = var.xml_element.get("name").replace('&apos', "'")

        # create link to driver/load connection in RTL
        p_var_dl_loc_link_xe = ET.SubElement(td_xml_element, 'p')
        p_var_dl_loc_link_xe.text = "Examine RTL: "
        a_var_dl_loc_link_xe = ET.SubElement(p_var_dl_loc_link_xe, 'a')

        # create hyperlink to file
        html_file = dl_loc_ls[0].replace("//", "/").replace("/", "__")+".html"

        html_id = "#"+dl_loc_ls[1]
        a_var_dl_loc_link_xe.set("href", html_file+html_id)

        # add link text
        a_var_dl_loc_link_xe.text = dl_loc_ls[0].replace("//", "/") +":"+ dl_loc_ls[1]

    return td_xml_element

def _HTML_createConnectivityTable(
                    module_obj:             ModuleDef, 
                    files_xml_element:      ET.Element, 
                    typetable_xml_element:  ET.Element,
                    parent_xml_element:     ET.Element,
    ):
    """
    Responsibility

    Create an HTML file detailing the connectivity of variables in a module

    Parameters:

    module_obj              :   ModuleDef Object containing information regarding...
                                ...RTL module and variable connectivity
    
    files_xml_element       :   xml.etree.ElementTree object, containing mapping...
                                ...between file IDs and file paths

    typetable_xml_element   :   xml.etree.ElementTree object, containing mapping...
                                ...between datatype IDs and data type properties
    
    parent_xml_element      :   xml.etree.ElementTree object, used to create Subelements...
                                ...of higher level elements like HTML tables
    """

    vars = module_obj.vars


    for var in vars:
        # create a new row for this var
        var_tr_xe = ET.SubElement(parent_xml_element, "tr")

        # list of tuples. (Var-like object, string)
        drivers_w_loc = var.findVarDrivers()
        loads_w_loc = var.findVarLoads()

        # get row span (from number of drivers/loads)
        row_span = str(max(len(drivers_w_loc), len(loads_w_loc), 1))

        # create var name column
        var_name_xml = _HTML_getVarName(var.xml_element.get('name'),
                                         row_span,
                                         var_tr_xe)
        
        # ged data for var info
        var_info_dict = elaborateDtypeId(var.xml_element.get('dtype_id'), 
                                           typetable_xml_element)

        loc_info_ls = elaborateLocs(var.xml_element.get('loc'), 
                                    files_xml_element).split(",")[:-2]
        
        # format location info text
        # "filepath, row_num:col_num"
        loc_info_txt = loc_info_ls[0].replace("//", "/")+", " + ":".join(loc_info_ls[1:])

        var_info_dict["loc"] = loc_info_txt

        if(var.xml_element.get('localparam') != None):
            var_info_dict["type"] += ", localparam"
        if(var.xml_element.get('param') != None):
            var_info_dict["type"] += ", parameter"
        if(var.xml_element.get('dir') != None):
            var_info_dict["type"] += f", {var.xml_element.get('dir')}"

        # create var info column
        var_info_xml = _HTML_getVarInfo(var_info_dict, row_span, var_tr_xe)

        # create table listing 
        curr_var_tr_xe = var_tr_xe
        
        # populate table with drivers and loads
        for i in range(int(row_span)):

            if(i < len(drivers_w_loc)):
                driving_loc_ls = elaborateLocs(drivers_w_loc[i][1], 
                                            files_xml_element).split(",")[:-2]
                
                var_driver_xml = _HTML_getVarDL(drivers_w_loc[i][0], 
                                                driving_loc_ls, 
                                                curr_var_tr_xe)
            
            elif(i == 0 and (var.xml_element.get('localparam') is not None 
                             or var.xml_element.get('parameter') is not None)):
                
                tmp_const_obj = ConstVar(var.xml_element.find("const"), None, None)
                tmp_const_loc_str = tmp_const_obj.xml_element.get('loc')
                tmp_const_loc_ls = elaborateLocs(tmp_const_loc_str, 
                                                files_xml_element).split(",")[:-2]
                
                var_driver_xml = _HTML_getVarDL(tmp_const_obj, 
                                                tmp_const_loc_ls,
                                                curr_var_tr_xe)
            
            else:
                var_driver_xml = _HTML_getVarDL(None, 
                                                ["", ""], 
                                                curr_var_tr_xe)

            if(i < len(loads_w_loc)):
                loading_loc_ls = elaborateLocs(loads_w_loc[i][1], 
                                            files_xml_element).split(",")[:-2]

                var_load_xml = _HTML_getVarDL(loads_w_loc[i][0], 
                                              loading_loc_ls, 
                                              curr_var_tr_xe)
            else:
                var_load_xml = _HTML_getVarDL(None, 
                                              ["", ""], 
                                              curr_var_tr_xe)

            if(i < int(row_span)-1):
                curr_var_tr_xe = ET.SubElement(parent_xml_element, "tr")

def _HTML_createInstHierHeading(
                    parent_html_xe:     ET.Element,
                    heading_tag:        str,
                    hier_path:          str  
    ):
    """
    Returns 
    
    xml.etree.ElementTree.Element, a <h*> html tag (* could be 3,4, etc)

    Parameters:

    parent_html_xe  :   xml.etree.ElementTree.Element, represents the...
                        ...parent HTML tag within which the heading will...
                        ...be created

                        Typically a <body> tag
    
    heading_tag     :   string, the HTML tag to be used for the heading

    hier_path       :   string, the hierarchical path of the module instance     
    """

    ### Instance Hierarchy header ###
    inst_hier_header_html_xe = ET.SubElement(parent_html_xe, heading_tag)
    inst_hier_header_html_xe.text = "Instance Hierarchy: " 

    # not boldened
    nb_inst_hier_header_html_xe = ET.SubElement(inst_hier_header_html_xe, "span")
    nb_inst_hier_header_html_xe.set("style", "font-weight:normal")

    # links to parent and ancestor instances
    ancestral_instances = hier_path.split(".")
    for i in range(len(ancestral_instances)):
        links_inst_hier_header_html_xe = ET.SubElement(nb_inst_hier_header_html_xe, "a")
        
        ancestor_link = ".".join(ancestral_instances[:(i+1)])
        ancestor_link += ".html"
        
        links_inst_hier_header_html_xe.set("href", ancestor_link)
        links_inst_hier_header_html_xe.text = ancestral_instances[i]

        if(i < len(ancestral_instances)-1):
            links_inst_hier_header_html_xe.tail = "."

def writeCSSFile(html_fpath_prefix: str) -> str:
    """
    Responsibility

    Writes external CSS file used to style the...
    ...connectivity table

    Returns:

    string, Path to CSS file

    Parameter:

    html_fpath_prefix   :   string, prefix 
    """

    # some of the css below was adapted from: 
    # - https://codepen.io/anon/pen/xfjrh
    # - https://dev.to/dcodeyt/creating-beautiful-html-tables-with-css-428l

    css_text = \
"""
h3 {
    font-family: sans-serif;
}

a:hover {
    background-color: #c6f7ed;;
}

table {
    border-collapse: collapse;
    margin: 25px 0;
    font-size: 0.95em;
    font-family: sans-serif;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
    min-width: 400px;
    max-width: 100%;
    position: relative;
}

thead {
    -webkit-box-shadow:rgba(0, 0, 0, 0.15) 2px 2px 10px;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
}

thead tr {
    background-color: #009879;
    color: #ffffff;
    text-align: left;
}

thead td {
    vertical-align: middle;
    font-weight:  bold;
    padding: 12px 15px;
}

tbody td {
    padding: 12px 15px;
    border-left: 1px solid #dddddd;
    vertical-align: top;
}

tbody tr {
    border-bottom: 1px solid #dddddd;
}

tbody tr:nth-of-type(even) {
    background-color: #f3f3f3;
}

tbody tr:last-of-type {
    border-bottom: 2px solid #009879;
}

tbody tr.active-row {
    font-weight: bold;
    color: #009879;
}

thead {
    position: sticky;
    top: 0;
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

    file_name = "connectivity_table_styles.css"
    out_file_path = os.path.join(html_fpath_prefix,
                                 file_name)

    with open(out_file_path, 'w') as f:
        f.write(css_text)

    return out_file_path

def writeModuleConnectivityHTML(                    
                    module_obj:             ModuleDef, 
                    files_xml_element:      ET.Element, 
                    typetable_xml_element:  ET.Element, 
                    html_fpath_prefix:      str,        
                    css_fname:              str,
                    instance_name:          str="",
                    index_html_file_name:   str="index.html"
    ) -> str:
    """
    Responsibility:

    Writes HTML file contaning connectivity table

    Returns:

    string, filepath of the written HTML file

    Parameters:

    module_obj          :   ModuleDef object, contains RTL module information 

    files_xml_element   :   xml.etree.ElementTree.Element object, contains..
                            ...mapping between file id's and file paths

    typetable_xml_element : xml.etree.ElementTree.Element object, contains..
                            ...mapping between data type id's and data type properties

    html_fpath_prefix   :   string, path to folder that will hold...
                            ...html files

    css_fname           :   string, file name for external css file used to...
                            ...style the html
    instance_name       :   string, instance name of the given module

    index_html_file_name:   string, file name to be used when linking connectivity...
                            ...table to design hierarchy index
    """

    # xe == xml_element
    html_xe = ET.Element("html")
    head_html_xe = ET.SubElement(html_xe, "head")
    head_css_link_html_xe = ET.SubElement(head_html_xe, "link")
    head_css_link_html_xe.set("rel", "stylesheet")
    head_css_link_html_xe.set("href", css_fname)

    HTML_HEADING_TAG = "h3"

    _instance_name = "" 
    if(instance_name == ""):
        _instance_name = module_obj.xml_element.get('name')
    else:
        _instance_name = instance_name

    body_html_xe = ET.SubElement(html_xe, "body")
    
    ### Instance name header ###
    inst_name_header_html_xe = ET.SubElement(body_html_xe, HTML_HEADING_TAG)
    inst_name_header_html_xe.text = "Instance Name: "

    # not boldened
    nb_inst_name_header_html_xe = ET.SubElement(inst_name_header_html_xe, "span")
    nb_inst_name_header_html_xe.set("style", "font-weight:normal")
    nb_inst_name_header_html_xe.text = _instance_name

    ### Module name header ###
    module_header_html_xe = ET.SubElement(body_html_xe, HTML_HEADING_TAG)
    module_header_html_xe.text = "Module: " 

    # not boldened
    nb_module_header_html_xe = ET.SubElement(module_header_html_xe, "span")
    nb_module_header_html_xe.set("style", "font-weight:normal")
    nb_module_header_html_xe.text = module_obj.xml_element.get('name')

    ### Instance Hierarchy header ###
    _HTML_createInstHierHeading(body_html_xe, HTML_HEADING_TAG, module_obj.getHierPath())


    ### Connectivity Table ###
    table_html_xe = ET.SubElement(body_html_xe, "table")

    # header row
    thead_html_xe = ET.SubElement(table_html_xe, "thead")
    tr_thead_html_xe = ET.SubElement(thead_html_xe, "tr")
    td_tr_table_header_html_xe = ET.SubElement(tr_thead_html_xe, "td")
    td_tr_table_header_html_xe.text = "Variable Name"

    td_tr_table_header_html_xe = ET.SubElement(tr_thead_html_xe, "td")
    td_tr_table_header_html_xe.text = "Variable Info"

    td_tr_table_header_html_xe = ET.SubElement(tr_thead_html_xe, "td")
    td_tr_table_header_html_xe.text = "Driver"

    td_tr_table_header_html_xe = ET.SubElement(tr_thead_html_xe, "td")
    td_tr_table_header_html_xe.text = "Load"

    tbody_html_xe = ET.SubElement(table_html_xe, "tbody")

    _HTML_createConnectivityTable(module_obj, 
                                files_xml_element, 
                                typetable_xml_element, 
                                tbody_html_xe)


    # lik to design Hierarchy Index
    p_html_xe = ET.SubElement(html_xe, "p")
    a_p_html_xe = ET.SubElement(p_html_xe, "a")
    a_p_html_xe.set("href", index_html_file_name)
    a_p_html_xe.text = "Design Hierarchy Index"

    # Write HTML file
    html_xe = ET.ElementTree(html_xe)
    ET.indent(html_xe)
    out_html_file_path = os.path.join(html_fpath_prefix, 
                                      module_obj.getHierPath()+".html")
    
    html_xe.write(out_html_file_path, method='html', short_empty_elements=False)

    return out_html_file_path

###################
# MAIN 
###################

# >>>>>>>>>>
# ARGS 
# >>>>>>>>>>

parser = argparse.ArgumentParser(
    description=\
"""
    Creates three kinds of HTML webpages to aid in exploring an RTL design.

    1) Desin Hierarchy Index:           This contains a tree view of instances in the design, 
                                        with links to each instance's connectivity table.

    2) Instance Connectivity Table:     This contains a table of all a modules's variables, 
                                        along with their drivers and loads. The connectivity 
                                        of variables (regs, wires, etc) across the design can be traced 
                                        by following the links provided in the connectivity table.
                                
    3) RTL:                             This contains the (system)verilog statements used to describe the design.
""",
    formatter_class=argparse.RawDescriptionHelpFormatter and argparse.RawTextHelpFormatter

)

parser.add_argument("xml_file", 
                    help="XML file to be parsed\n"+
                    "**Note:** \nTo create this file PLEASE use Verilator with the following\n"+ \
                            "flags (in addtion to the paths to your design files and other flags)\n\n"+ \
                            "\t'-Wno-fatal --timing --fno-dfg --fno-dedup --fno-combine --fno-assemble \n" + \
                            "\t--fno-reorder --fno-expand --fno-subst --fno-merge-const-pool\n"+ \
                            "\t--xml-only --xml-output <design_xml_filename>.xml'\n\n"+ \
                            "Relpace '<design_xml_filename>' with the filename for the output xml file\n"+ \
                            "Tested with Verilator 5.003.\n ")

parser.add_argument("out_dir", 
                    help="Directory in which HTML (and other) files will be placed")
parser.add_argument("-m", action="store_true",  default=False, dest="multithread_enabled", 
                    help="If specified, will launch 3 threads"+\
                         " to parallellize the creation of connitivity html"+\
                         " files, verilog html files, and index html files.")

args = parser.parse_args()

# <<<<<<<<<<<<
# ARGS 
# <<<<<<<<<<<<

# ensure out_dir exists
if(not os.path.exists(args.out_dir)):
    print(f"Path '{args.out_dir}' does not exist.")
    exit(1)

# creating XML tree
design_xml_tree = ET.parse(args.xml_file)

# get files
files = design_xml_tree.findall("./module_files/file")
files = list(map(lambda xe: xe.get("filename").replace("//", "/"), files))

# >>>>>>>>>>>>>>>>>
### create rtl HTML & CSS files ###
if(args.multithread_enabled):
    thread_rtl_html = threading.Thread(target=create_RTL_HTML, args=(files, args.out_dir))
    thread_rtl_html.start()
else:
    create_RTL_HTML(files, args.out_dir)
# <<<<<<<<<<<<<<<<<

# get top module
xml_top_module = None
xml_submodules = []

# get all xml tag elements of type module
for module in design_xml_tree.findall("./netlist/module"):
    if(module.get('topModule') == "1"):

        if(xml_top_module is not None):
            raise Exception(f"There appear to be multiple top Modules." \
            + f" '{xml_top_module.get('name')}' appears to be the second")
        else:
            xml_top_module = module

    else:
        xml_submodules.append(module)

### create object model of design ###
top_module = ModuleDef(xml_top_module, xml_submodules, None)



# print stats
print("Top Module name:", top_module.xml_element.get('name'))
print()

all_vars = top_module.getAllVars()
print("Number of vars:", len(all_vars))

all_instances = top_module.getAllInstances()
print("Number of Instances:", len(all_instances), "\n")

# create a formatted list of instance hierarchies
instances_str = top_module.getHierPath() + f" ({top_module.xml_element.get('name')})" '\n' 
instances_ls  = [instances_str] + \
                list(map(
                    lambda s: s.getHierPath() + f" ({s.xml_element.get('defName')})", 
                    all_instances
                ))


# >>>>>>>>>>>>>>>>>
### create index HTML & CSS files ###
index_html_file_name = "index.html"

if(args.multithread_enabled):
    thread_index_html = threading.Thread(target=writeIndex, args=(args.out_dir, instances_ls, index_html_file_name))
    thread_index_html.start()
else:
    create_RTL_HTML(files, args.out_dir)
# <<<<<<<<<<<<<<<<<


# write out all instances to a file
instances_file_name = "instances.txt"
instances_fpath = os.path.join(args.out_dir, instances_file_name)
with open(instances_fpath, "w") as f:
    f.write("\n".join(instances_ls))

print(f"All instance hierarchical paths & module names dumped to '{instances_fpath}'")

# write out all vars to a file
vars_file_name = "vars.txt"
vars_str = "\n".join(list(map(lambda v : v.getHierPath(), all_vars)))
vars_fpath = os.path.join(args.out_dir, vars_file_name)
with open(vars_fpath, "w") as f:
    f.write(vars_str)

print(f"All hierarchical paths for variables (i.e. regs/wires/localparams) dumped to '{instances_fpath}'")

# >>>>>>>>>>>>>>>>
# HTML CREATION 
# >>>>>>>>>>>>>>>>

files_xml_element = design_xml_tree.find("files")
typetable_xml_element = design_xml_tree.find("netlist/typetable")

html_folder = args.out_dir
css_fpath = writeCSSFile(html_folder)
css_fname = os.path.basename(css_fpath)

top_module_html_fpath = writeModuleConnectivityHTML(top_module, 
                                                    files_xml_element, 
                                                    typetable_xml_element, 
                                                    html_folder, css_fname,"", index_html_file_name)

for instance in all_instances:
    writeModuleConnectivityHTML(instance.module_def, files_xml_element, typetable_xml_element, 
                             html_folder, css_fname, instance.xml_element.get('name'), index_html_file_name)

# <<<<<<<<<<<<<<<<
# HTML CREATION 
# <<<<<<<<<<<<<<<<

if(args.multithread_enabled):
    thread_rtl_html.join()
    thread_index_html.join()
    
print(f"\nRoot connectivity table: {top_module_html_fpath}")
print(f"Design Hierarchy Index: {os.path.join(args.out_dir, index_html_file_name)}")