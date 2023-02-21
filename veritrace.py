import argparse
import xml.etree.ElementTree as ET
import os

FILE_PATH_PRE = ""

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

    Contant value used to tieoff ports
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
    Represents a Var. This may be:
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
    
    A constant value typically used to drive vars.
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
                out.append(last_child.find("varref"))
            elif(last_child.tag == "delay"):
                # child before delay tag is contains the load(s)
                last_child = children[children.index(last_child)-1]
                repeat = True
            else:
                print()
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
            # When last child is a delay, every child except the second to last child are typically drivers
            driver_children = xml_element.findall("./*")[:-2]
        else:
            # Every child except the last child are typically drivers
            driver_children = xml_element.findall("./*")[:-1]

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

        xml_element :   # FIXME: elaborate
        
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

        List of Objects which includes:
            - Var

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

            out.append(var_obj)
        
        return out
    
    def findInputDrivers(self, port_name: str) -> list:
        """
        Return

        List of Objects which includes:
            - Var
            - ConstVar
            - ConstLiteral

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
            var_obj = self.parent_obj.findVar("."+port_connection_name)

            if(var_obj == None and ModuleDef.nameContainsConstIndicators(port_connection_name)):
                const_xml_element = self.input_ports_dict[port_name].connections[port_connection_name]
                out.append(ConstLiteral(const_xml_element, self, self.root))
            else:
                out.append(var_obj)
        
        return out

    def findVarDrivers(self, var_name: str):
        """
        Returns 
        
        List of objects which are driver of 'var_name'
            Note:
            - Objects may be:
                - port
                - var
                - const
        
        Parameters 

        var_name : string, Name of the variable whose drivers should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        return self.module_def.findVarDrivers(var_name)
    
    def findVarLoads(self, var_name: str):
        """
        Returns 
        
        List of objects which are loads of 'var_name'
            Note:
            - Objects may be:
                - port
                - var
        
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

    def __init__(self, xml_element, xml_modules, parent_obj=None, root=None):
        """
        Params:

        xml_modules : list of xml.etree.ElementTree.Elements objects for all submodules
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
        """

        out = []

        # get all *assign* tags in the module (analogous to assignments in an RTL Module)
        # FIXME: Create a defines package/module to encapsulate all the types of assignments
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

    def _populateInstances(self, xml_element, xml_modules, root) -> list:
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
            # FIXME: consider multithreading
            out.append(ModuleInstance(xml_instance, xml_modules, self, root))

        return out

    def _populateVars(self, xml_element, root) -> list:
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
    
    def findVarDrivers(self, var_name):
        """
        Returns 
        
        List of objects which are drivers of the variable represented by 'var_name'
            Note:
            - Objects may be:
                - port
                - var
                - const

        Parameters: 

        var_name    :   string, Name of the variable whose drivers should be found. 
                        The variable must be a child of the module (i.e. self)
        """

        drivers = []

        # only check instance ports and assigns when var is not an input...
        # ...inputs can't be driven internally
        if(self.findVar("."+var_name).xml_element.get('dir') != "input"):

            # check instance ports
            for instance in self.instances:
                for output_instance_port in instance.output_ports:
                    if(var_name in output_instance_port.connections):
                        drivers.append(output_instance_port)
        
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
                            drivers.append(ConstVar(assign_driver_xml, self, self.root))
                        else:
                            drivers.append(
                                self.findVar("."+assign_driver_xml.get('name'))
                            )

        # find external loads if var is an output port and module is an instance
        elif(self.parent_obj is not None):
            drivers.extend(self.parent_obj.findInputDrivers(var_name))

        return drivers

    def findVarLoads(self, var_name):
        """
        Returns 
        
        List of objects which are loads of the variable represented by 'var_name'
            Note:
            - Objects may be:
                - port
                - var

        Parameters: 

        var_name : string, Name of the variable whose loads should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        loads = []

        # check instance ports
        for instance in self.instances:
            for input_instance_port in instance.input_ports:
                if(var_name in input_instance_port.connections):
                    loads.append(input_instance_port)

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
                    loads.append(
                        self.findVar("."+assign_load_xml.get('name'))
                    )

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
        #FIXME: Use instance path instead
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

def getParamValue(param_xml_element):
    """
    Retunrs string of value assinged to a param or localparam
    """

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
    """
    # Note xml_element = xe
    td_xml_element = ET.SubElement(parent_xml_element, 'td')
    td_xml_element.set('rowspan', rowspan)

    for key, value in var_info_dict.items():
        p_xml_element = ET.SubElement(td_xml_element, "p")
        strong_xe = ET.SubElement(p_xml_element, "strong")
        strong_xe.text = key

        strong_xe.tail = f": {value}"


    if(misc_text != ""):
        p_misc_xml_element = ET.SubElement(td_xml_element, "p")
        p_misc_xml_element.text = misc_text

    return td_xml_element

def _HTML_getVarDL(var: Var,
                   parent_xml_element: ET.Element):
    """
    DL == Driver/Load
    
    Parameters:

    vars : if None, then a dash is entered in the HTML table
    """

    # Note xml_element = xe
    td_xml_element = ET.SubElement(parent_xml_element, 'td')
    if(var == None):
        p_var_name_xe = ET.SubElement(td_xml_element, 'p')
        p_var_name_xe.text = "None"
    else:
        p_var_name_xe = ET.SubElement(td_xml_element, 'p')
        p_var_name_xe.text = var.xml_element.get("name")

        p_var_link_xe = ET.SubElement(td_xml_element, 'p')
        a_var_link_xe = ET.SubElement(p_var_link_xe, 'a')

        # create link to driver/load module
        var_hier = var.getHierPath()
        var_hier_wo_name = ".".join(var_hier.split('.')[:-1])
        instance_html_fpath =   var_hier_wo_name+".html#" +\
                                var.xml_element.get('name')
        
        instance_html_fpath = os.path.join(f"{FILE_PATH_PRE}", 
                                           instance_html_fpath) 

        a_var_link_xe.set("href", instance_html_fpath)

        # add link text
        a_var_link_xe.text = var_hier

    return td_xml_element

def writeModuleHTML(module_obj:             ModuleDef, 
                    files_xml_element:      ET.Element, 
                    typetable_xml_element:  ET.Element, 
                    parent_xml_element:     ET.Element,
                    instance_name:          str=""):
    """
    Responsibility

    Writes an HTML file detailing the connectivity of variables in a module

    Parameters:

    module_obj  :   FIXME
    instance_name   :   FIXME
    """

    out_html_txt = \
"""
<!DOCTYPE html>
<html>
<head>
    <style>
        table, th, td {
            border: 1px solid black;
            vertical-align: top;
         }
        table {
            width: 100%
        }
        th, td {
            padding: 2px; 
        }
    </style>
    <h3>Module:</h3>
    <h3>Instance Hierarchy:</h3>
    <hr />
    <table>
        <tbody>
            <tr>
                <td>Vars</td>
                <td>Info</td>
                <td>Drivers</td>
                <td>Load</td>
            </tr>
"""

    vars = top_module.vars


    for var in vars:
        # create a new row for this var
        var_tr_xe = ET.SubElement(parent_xml_element, "tr")
        drivers = var.findVarDrivers()
        loads = var.findVarLoads()

        # get row span (from number of drivers/loads)
        row_span = str(max(len(drivers), len(loads), 1))

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
        loc_info_txt = loc_info_ls[0]+", " + ":".join(loc_info_ls[1:])

        var_info_dict["loc"] = loc_info_txt

        # FIXME (low priority) Conditions should be more stringent
        if(var.xml_element.get('localparam') != None):
            var_info_dict["type"] += ", localparam"
        if(var.xml_element.get('param') != None):
            var_info_dict["type"] += ", param"
        if(var.xml_element.get('dir') != None):
            var_info_dict["type"] += f", {var.xml_element.get('dir')}"

        # create var info column
        var_info_xml = _HTML_getVarInfo(var_info_dict, row_span, var_tr_xe)

        # create table listing 
        curr_var_tr_xe = var_tr_xe

        for i in range(int(row_span)):

            if(i < len(drivers)):
                var_driver_xml = _HTML_getVarDL(drivers[i], curr_var_tr_xe)
            else:
                var_driver_xml = _HTML_getVarDL(None, curr_var_tr_xe)

            if(i < len(loads)):
                var_load_xml = _HTML_getVarDL(loads[i], curr_var_tr_xe)
            else:
                var_load_xml = _HTML_getVarDL(None, curr_var_tr_xe)

            if(i < int(row_span)-1):
                curr_var_tr_xe = ET.SubElement(parent_xml_element, "tr")
                             

    print(ET.tostring(var_name_xml))
    with open("test.xml", "wb") as f:
        f.write(ET.tostring(parent_xml_element))
    print(ET.tostring(var_info_xml))
    # break

    out_html_txt += \
"""
        </tbody>
    </table>
</head>
</html>
"""

######## MAIN ##########

parser = argparse.ArgumentParser()

parser.add_argument("xml_file", help="XML file to be parsed")

args = parser.parse_args()

# creating XML tree
design_xml_tree = ET.parse(args.xml_file)

# get top module
xml_top_module = None
xml_submodules = []

for module in design_xml_tree.findall("./netlist/module"):
    if(module.get('topModule') == "1"):

        if(xml_top_module is not None):
            raise Exception(f"There appear to be multiple topModules." \
            + f" '{xml_top_module.get('name')}' appears to be the second")
        else:
            xml_top_module = module

    else:
        xml_submodules.append(module)

top_module = ModuleDef(xml_top_module, xml_submodules, None)

print("Top Module name:", top_module.xml_element.get('name'))
# print("Top Module Instances:")
# for instance in top_module.instances:
#     print("\tInstance Attrs:",instance.xml_element.items())


test_var = top_module.instances[5].module_def.instances[2].module_def.instances[0].module_def.vars[0]
print(test_var.getHierPath())
# test_find_var_out = top_module.findVar("."+".".join(test_var.getHierPath().split('.')[1:]))
test_find_var_out = top_module.findVar(".i_addr")
print(test_find_var_out.xml_element.get('name'))

all_vars = top_module.getAllVars()

print("Num of vars:", len(all_vars))

# for var in all_vars:
#     print(var.getHierPath())

print()

all_instances = top_module.getAllInstances()

print("Num of Instances:", len(all_instances))

# for instance in all_instances:
#     print(instance.getHierPath())

print()

find_load_str = ".i_mem_data"
# print("Printing Loads for", find_load_str)
# for load in top_module.findVar(find_load_str).findVarLoads():
#     print(" Load tag: ", load.xml_element.tag)
#     print(" Load Attibutes:", load.xml_element.items())
#     print(" Load Parent tag:", load.parent_obj.xml_element.tag)
#     print(" Load Parent Attibutes", load.parent_obj.xml_element.items())
#     print(" "+load.getHierPath())

#     count = 2
#     while(not((load.parent_obj.parent_obj is None) and (load.xml_element.get('dir') == "output"))):
#         load = load.findVarLoads()[0]
#         print(("  "*count)+"Load tag: ", load.xml_element.tag)
#         print(("  "*count)+"Load Attibutes:", load.xml_element.items())
#         print(("  "*count)+"Load Parent tag:", load.parent_obj.xml_element.tag)
#         print(("  "*count)+"Load Parent Attibutes", load.parent_obj.xml_element.items())
#         print(("  "*count)+load.getHierPath())

#         count += 1

# get top level ports

print("Printing ports and their drivers")
print(">>>>>>>>>>>>>")
for var in top_module.vars:
    for driver in var.findVarDrivers():
        
        print("{: <30} -> {: <30} {: <20}".format(
            var.xml_element.get('name'), 
            driver.xml_element.get('name'), 
            driver.getHierPath()))
print("<<<<<<<<<<<<<")

files_xml_element = design_xml_tree.find("files")
typetable_xml_element = design_xml_tree.find("netlist/typetable")

print()
print(">>>>>>>>>>>>>")
print(var.xml_element.attrib)
print(elaborateLocs(var.xml_element.get('loc'), files_xml_element).split(",")[:-2])
print(elaborateDtypeId("29", typetable_xml_element))
print("<<<<<<<<<<<<<")

parent_xml_element = ET.Element("top")

writeModuleHTML(top_module, files_xml_element, typetable_xml_element, parent_xml_element)