import argparse
import xml.etree.ElementTree as ET
import copy


class TypeTable():
    """
    """

    def __init__(self) -> None:
        pass

class Assign():
    """
    Represents assignments made in modules. There can be three types of assigns:
        - assign
        - assigndly
        - contassign
    """

    def __init__(self, xml_element, parent_obj) -> None:
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Assignment tag

        parent_obj  : an object which is an ancestor of this object (according to xml hierarchy)
                        This is typically a Module 
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj

        self.drivers = Assign.getDrivers(xml_element)
        self.loads = Assign.getLoads(xml_element)

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


class Var():
    """
    Represents a variable which may be:
        - module port
        - internal wire/reg (i.e. connectable)
        - localparam/param
    """

    def __init__(self, xml_element, parent_obj):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Var

        parent_obj  : a reference to the object where this var is defined. 
                      This object contains an xml element that is the ancestor of 'xml_element'
        """

        self.xml_element = xml_element
        self.parent_obj = parent_obj

    
    def getHierPath(self) -> str:
        """
        Returns:

        Hierarchical path of this instnace from the root (or top) module
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


class InstancePort():
    """
    Represents ports on module instances
    """

    def __init__(self, xml_element, parent_obj):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Instanceport

        parent_obj  : a reference to the Instance object where this port is defined. 
                      This object contains an xml element that is the ancestor of 'xml_element'
        """
        self.xml_element = xml_element
        self.parent_obj = parent_obj

        self.connections = self.getConnections(xml_element)

    def getConnections(self, xml_element):
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

        for varref in xml_element.iter("varref"):
            out_dict[varref.get('name')] = varref

        return out_dict
    
    def getHierPath(self) -> str:
        """
        Returns:

        Hierarchical path of this instnace from the root (or top) module
        """

        return self.parent_obj.getHierPath() + "." + self.xml_element.get('name')
    
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
    Represent module instances.
    """

    def __init__(self, xml_element, parent_obj):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Instance

        parent_obj  : a reference to the Module where this Instance is defined. 
                      This object contains an xml element that is the ancestor of 'xml_element'
        """
        self.xml_element = xml_element
        self.parent_obj = parent_obj
        self.module_obj = None 

        # hierarchical path relative to parent
        # self.rel_hier_path = parent_obj.xml_element.get('name') + "." + xml_element.get('name')
        
        self.ports = self.getInstancePorts(xml_element)

    def getInstancePorts(self, xml_element):
        """
        Return 

        List of InstancePort objects

        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the instance to be searched for ports
        """

        out = []

        for port in xml_element.iter("port"):
            out.append(InstancePort(port, self))
        
        return out
    
    def getInputPorts(self) -> list:
        """
        Returns 

        A list of InstancePort objects
        """

        out = []

        for port in self.ports:
            if(port.xml_element.get('direction') == "in"):
                out.append(port)

        return out
    
    def getOutputPorts(self) -> list:
        """
        Returns 

        A list of InstancePort objects
        """

        out = []

        for port in self.ports:
            if(port.xml_element.get('direction') == "out"):
                out.append(port)

        return out
    
    def linkModule(self, module_obj):
        """
        Responsibility:

        Set the 'self.module_obj' attribute with the given parameter
        
        Parameter:

        module_obj : Module Object, this is the module that defines this instance (not instantiates it).
        """

        if(self.xml_element.get('defName') == module_obj.xml_element.get('name')):
            self.module_obj = copy.deepcopy(module_obj)
            self.module_obj.parent_obj = self
        else:
            raise Exception(f"Cannot linkModule: module_obj with name '{module_obj.xml_element.get('name')}' doesn't " + \
                            f"match this instance's defName '{self.xml_element.get('defName')}'.")
        
    def getHierPath(self) -> str:
        """
        Returns:

        Hierarchical path of this instnace from the root (or top) module
        """

        return self.parent_obj.getHierPath() + "." + self.xml_element.get('name')

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

        return self.module_obj.findVarLoads(var_name)
    
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

        return self.module_obj.findVarDrivers(var_name)


class Module():
    """
    Represents verilog module
    """

    def __init__(self, xml_element):
        """
        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the xml node that defines the Instance
        """
        # store xml data
        self.xml_element = xml_element

        # get vars 
        self.vars = self.getVars(xml_element)

        # get instances
        self.instances = self.getInstances(xml_element)

        # If not none, then module object is an instnace within another module
        self.parent_obj = None

        self.assigns = self.getAssigns(xml_element)


    def getAssigns(self, xml_element):
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
                out.append(Assign(assign, self))

        return out


    def getVars(self, xml_element):
        """
        Returns
        
        List of Var objects

        Parameters

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the module to be searched for variables
        """
        out = []
        for var in xml_element.findall("./var"):
            out.append(Var(var, self))

        return out 
    
    def getInstances(self, xml_element):
        """
        Returns 
        
        A list of Instance Objects 

        Parameters:

        xml_element : an xml.etree.ElementTree.Element object. This object is...
                      ...the module to be searched for instances of other modules
        """

        out = []

        for instance in xml_element.iter("instance"):
            out.append(ModuleInstance(instance, self))

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

        var_name : string, Name of the variable whose drivers should be found. 
                    The variable must be a child of the module (i.e. self)
        """

        drivers = []

        # check instance ports
        for instance in self.instances:
            for output_instance_port in instance.getOutputPorts():
                if(var_name in output_instance_port.connections):
                    drivers.append(output_instance_port)
    
        # check all the *assign* nodes (or statement)
        for assign in self.assigns:

            # get the loads and drivers in this *assign* node 
            assign_loads = assign.loads
            assign_drivers = assign.drivers

            assign_contains_drivers = False
            # check if var_name is a load in this assign node
            for assign_load in assign_loads:
                
                if(assign_load.get('name') == var_name):
                    assign_contains_drivers = True
                    break
            
            if(assign_contains_drivers):
                # append all drivers in this assign
                for assign_driver in assign_drivers:
                    drivers.append(
                        self.getVarFromName(assign_driver.get('name'))
                    )

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
            for input_instance_port in instance.getInputPorts():
                if(var_name in input_instance_port.connections):
                    loads.append(input_instance_port)

        # check all the *assign* nodes (or statements)
        for assign in self.assigns:

            # get the loads and drivers in this *assign* node 
            assign_loads = assign.loads
            assign_drivers = assign.drivers

            assign_contains_loads = False
            # check if var_name is a driver in this assign node
            for assign_driver in assign_drivers:
                
                if(assign_driver.get('name') == var_name):
                    assign_contains_loads = True
                    break
            
            if(assign_contains_loads):
                # append all loads in this assign
                for assign_load in assign_loads:
                    loads.append(
                        self.getVarFromName(assign_load.get('name'))
                    )

        return loads


    def getInputPorts(self):
        """
        Returns 
        
        List of var objects 
        """
        
        out = []
        for var in self.vars:
            if(var.xml_element.get('dir') == "input"):
                out.append(var)

        return out
    
    def getOutputPorts(self):
        """
        Returns 
        
        List of var objects 
        """
        
        out = []
        for var in self.vars:
            if(var.xml_element.get('dir') == "output"):
                out.append(var)

        return out
    
    def getVarFromName(self, name_str: str) -> Var:
        """
        Returns 

        A 'Var' Object whose name matches 'name_str'

        Parameters

        name_str : string, name of the var for find. 
        """
        out_var = None
        
        for var in self.vars:
            if(var.xml_element.get('name') == name_str):
                out_var = var

        return out_var
    
    def linkInstancesToModules(self, modules) -> None:
        """
        Responsibility

        Links intstances in this module to their respective module objects

        Parameters:

        modules : list of Module objects
        """

        module_names = [ module.xml_element.get('name') for module in modules ]

        for instance in self.instances:
            if(instance.xml_element.get('defName') in module_names):
                # get module with that defines instance
                matching_module = modules[module_names.index(
                                            instance.xml_element.get('defName')
                                        )]

                instance.linkModule(matching_module)

    def getHierPath(self) -> str:
        """
        Returns:

        Hierarchical path of this instnace from the root (or top) module
        """
        out = ""
        if(self.parent_obj is None):
            out = self.xml_element.get('name')
        else:
            out = self.parent_obj.getHierPath()
        
        return out

######## MAIN ##########

parser = argparse.ArgumentParser()

parser.add_argument("xml_file", help="XML file to be parsed")

args = parser.parse_args()

# creating XML tree
tree = ET.parse(args.xml_file)

netlist_node = tree.find("netlist")

modules = []

for node in netlist_node:
    if(node.tag == "module"):
        modules.append(Module(node))
        print("Module detected")
    elif(node.tag == "typetable"):
        # create typetable
        print("TypeTable detected")

# link all instances in each module with their module definition
for module in modules:
    module.linkInstancesToModules(modules)



print("=============")
print("Num of top module output ports:", len(modules[0].getOutputPorts()))
# print(modules[0].findVarLoads(modules[0].vars[0])[0].parent_obj.parent_obj.xml_element.get('name'))
# print(modules[0].findVarLoads(modules[0].vars[0])[0].parent_obj.xml_element.get('name'))
print("Name of first load variable for first input port:", modules[0].findVarLoads(modules[0].vars[0].xml_element.get('name'))[0].xml_element.get('name'))
print("=============")

top_module = None 
for module in modules:
    if(module.xml_element.get('topModule') == "1"):
        top_module = module
        break
del modules

find_load_str = "tc_cache_hit"

print("Printing Loads for", find_load_str)
for load in top_module.findVarLoads(find_load_str):
    print("\tLoad tag: ", load.xml_element.tag)
    print("\tLoad Attibutes:", load.xml_element.items())
    print("\tLoad Parent tag:", load.parent_obj.xml_element.tag)
    print("\tLoad Parent Attibutes", load.parent_obj.xml_element.items())
    print("\t"+load.getHierPath())

    if(load.xml_element.tag == "port"):
        loads_loads = load.findVarLoads()
        for loads_load in loads_loads:
            print("\t\tLoad's load tag: ", loads_load.xml_element.tag)
            print("\t\tLoad's load Attibutes:", loads_load.xml_element.items())
            print("\t\tLoad's load Parent tag:", loads_load.parent_obj.xml_element.tag)
            print("\t\tLoad's load Parent Attibutes", loads_load.parent_obj.xml_element.items())
            print("\t\t"+loads_load.getHierPath())

    print()

print("=============")

find_driver_str = "o_valid"
for driver in top_module.findVarDrivers(find_driver_str):
    print("\tDriver tag: ", driver.xml_element.tag)
    print("\tDriver Attibutes:", driver.xml_element.items())
    print("\tDriver Parent tag:", driver.parent_obj.xml_element.tag)
    print("\tDriver Parent Attibutes", driver.parent_obj.xml_element.items())
    print("\t"+driver.getHierPath())
    print()

    if(driver.xml_element.tag == "port"):
        driver_drivers = driver.findVarDrivers()
        for driver_driver in driver_drivers:
            print("\t\tDriver's driver tag: ", driver_driver.xml_element.tag)
            print("\t\tDriver's driver Attibutes:", driver_driver.xml_element.items())
            print("\t\tDriver's driver Parent tag:", driver_driver.parent_obj.xml_element.tag)
            print("\t\tDriver's driver Parent Attibutes", driver_driver.parent_obj.xml_element.items())
            print("\t\t"+driver_driver.getHierPath())
            print()

# with open("out.xml", "wb") as f:
#     f.write(ET.tostring(top_module.xml_element))