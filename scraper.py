"""
    scraper.py

    The scraper class is used to scrape data from a decompiled form of the
    Tribes 2 game executable in order to build a tree of sorts that can be
    used for mapping out the various functions, global variables and
    datablock types & their associated properties.

    This software is licensed under the MIT license. Refer to LICENSE.txt for
    details.
    Copyright (c) 2016 Robert MacGregor
"""

import re
import string

class EngineComponent(object):
    """
        The base representation type for all the data the scraper will be
        pulling from the pseudo source code.
    """
    name = None
    address = None
    type_name = None
    description = None

    def __init__(self, name, address, type_name, description):
        self.name = name
        self.address = address
        self.type_name = type_name
        self.description = description

class Function(EngineComponent):
    """
        The virtual representation of a callable engine function from Torque
        Script. It contains a description, the address, argument information
        and if applicable, the object typename it is bound to.
    """
    min_args = None
    max_args = None

    def __init__(self, name, address, type_name, description, min_args, max_args):
        EngineComponent.__init__(self, name, address, type_name, description)

        self.min_args = min_args
        self.max_args = max_args

class GlobalVariable(EngineComponent):
    def __init__(self, name, address, type_name):
        EngineComponent.__init__(self, name, address, type_name, None)

class Datablock(EngineComponent):
    """
        The virtual representation of the Torque Game Engine datablock used
        for synchronization of custom simulation parameters across the network.
    """
    properties = None

    class Property(EngineComponent):
        def __init__(self, name, address, type_name):
            EngineComponent.__init__(self, name, address, type_name, None)

    def __init__(self, name):
        EngineComponent.__init__(self, name, None, None, None)

        self.properties = { }

class Scraper(object):
    """
        The meat and potatoes of the scraper system. This is your primary
        class to instantiate
    """

    _global_function_registry = ["426650", "426590", "4265D0", "426550", "426610"]
    """
        The global function registry is used by the scraper to determine prefixes
        of all the sub routines that register global functions in the Tribes 2
        engine. They take the following format: sub_######
    """

    _type_function_registry = ["426450", "426510", "426450", "425960"]
    """
        The type function registry is the same as the global function registry,
        except used for type contextual functions. The registration signatures
        for these functions are slightly different.
    """

    _datablock_property_registry = ["423F20"]
    """
        Registration subroutines regarding static fields of datablocks.
    """

    _global_value_registry = ["4263B0"]
    """
        Registration subroutines regarding globally addressible variables.
    """

    _registration_expression_template = "sub_(%s)[^;{]+;[^\"]"
    """
        Base regular expression used for matching the various registration
        calls. It is formatted with the above values in-place for operating
        within the different contexts.
    """

    _datablock_type_table = {
        "61E7A0": "ExplosionData",
        "5B4F60": "WaterBlockData",
        "612400": "WheeledVehicleData",
        "6161E0": "HoverVehicleData",
        "5CE810": "PlayerData",
        "6034C0": "ItemData",
        "69C170": "TriggerData",
        "50DC70": "AudioProfileData",
        "62B3C0": "LinearProjectile",
        "60F820": "FlyingVehicleData",
        "6370D0": "SeekingProjectileData",
        "69B0F0": "PrecipitationData",
        "641480": "SniperProjectileData",
        "66A270": "SensorData",

        "6303F0": "GrenadeProjectileData",
        "6333D0": "GrenadeProjectileData",

        "694B40": "TracerProjectileData",
        "6470D0": "TargetProjectileData",

        "653E10": "TurretData",
        "654AE0": "TurretData",
        "5E4C20": "TurretData", # Camera?

        "654330": "TurretImageData", # TurretData?

        "64E2B0": "LightningData",
        "627150": "LightningData",

        "621DF0": "ParticleEmitterData",
        "622E60": "ParticleData",

        "644910": "ELFProjectileData",
        "64A860": "ELFProjectileData",

        "5F4D90": "ShapeBaseImageData",

        "602940": "StaticShapeData",
        "66B000": "SpawnSphere",

        "6099E0": "VehicleData",

        "47D880": "AI Task?",

        "63D870": "LinearFlareData",

        "59A870": "TerrainData",
        "68C4B0": "ShockwaveData",

        "4B5840": "CorpseData",

        "619B30": "Sky",
        "5AB310": "Sky",

        "68AAA0": "PhysicalZone",

        "626240": "Debris",
        "684000": "Debris",

        "6751A0": "ForceFieldBareData",

        "631A50": "ProjectileData", # Base?
        "69AF10": "FireballAtmosphere",
    }
    """
        The datablock type table is used when looking up the context of a given static datablock field registration
        call. This context is merely the address of the calling subroutine, so multiple entries may have to be added
        for a single datablock type.
    """

    # Hacks
    string_expression = re.compile("\" *\S+\" *")

    # Global method material
    global_method_add_expression = re.compile(_registration_expression_template % string.join(_global_function_registry, "|"), re.IGNORECASE)
    type_method_add_expression = re.compile(_registration_expression_template % string.join(_type_function_registry, "|"), re.IGNORECASE)
    datablock_property_add_expression = re.compile(_registration_expression_template % string.join(_datablock_property_registry, "|"), re.IGNORECASE)
    global_value_add_expression = re.compile(_registration_expression_template % string.join(_global_value_registry, "|"), re.IGNORECASE)

    type_function_total = 0
    global_function_count = 0
    type_function_counts = None

    primitive_type_mapping = [
        "Unknown",
        "Integer",
        "Unknown",
        "Boolean",
        "Unknown",
        "Float",
        "Unknown"
    ]

    # Dictionary containing type name to inheritance list mappings
    type_name_inheritance = {
    "HTTPObject": ["HTTPObject", "TCPObject", "SimObject"],
    "FileObject": ["FileObject", "SimObject"],
    "Item": ["Item", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "SceneObject": ["SceneObject", "NetObject", "SimObject"],
    "Player": ["Player", "Player", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "DebugView": ["DebugView", "GuiTextCtrl", "GuiControl", "SimGroup", "SimSet", "SimObject"],
    "GameBase": ["GameBase", "SceneObject", "NetObject", "SimObject"],
    "SimpleNetObject": ["SimpleNetObject", "SimObject"],
    "SimObject": ["SimObject"],
    "Canvas": ["Canvas", "GuiCanvas", "GuiControl", "SimGroup", "SimSet", "SimObject"],
    "GuiCanvas": ["GuiCanvas", "GuiControl", "SimGroup", "SimSet", "SimObject"],
    "AIObjectiveQ": ["AIObjectiveQ", "SimSet", "SimObject"],
    "ForceFieldBare": ["ForceFieldBare", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "PhysicalZone": ["PhysicalZone", "SceneObject", "NetObject", "SimObject" ],
    "AIConnection": ["AIConnection", "GameConnection", "GameConnection", "GameConnection", "NetConnection", "SimGroup", "SimSet", "SimObject"],
    "Turret": ["Turret", "StaticShape", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject" ],
    "TerrainBlock": ["TerrainBlock", "SceneObject", "NetObject", "SimObject"],
    "PlayerData": ["PlayerData", "ShapeBaseData", "GameBaseData", "SimDataBlock", "SimObject"],
    "InheriorInstance": ["InteriorInstance", "SceneObject", "NetObject", "SimObject"],
    "StaticShape": ["StaticShape", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "Trigger": ["Trigger", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "WaterBlock": ["WaterBlock", "SceneObject", "NetObject", "SimObject"],
    "FireballAtmosphere": ["FireballAtmosphere", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "MissionArea": ["MissionArea", "NetObject", "SimObject"],
    "TSStatic": ["TSStatic", "SceneObject", "NetObject", "SimObject"],

    # Projectile Types
    "LinearProjectile": ["LinearProjectile", "Projectile", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "EnergyProjectile": ["EnergyProjectile", "GrenadeProjectile", "Projectile", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "GrenadeProjectile": ["GrenadeProjectile", "Projectile", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "TargetProjectile": ["TargetProjectile", "Projectile", "GameBase", "SceneObject", "NetObject", "SimObject"],

    # Vehicle Types
    "HoverVehicle": ["HoverVehicle", "Vehicle", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "FlyingVehicle": ["FlyingVehicle", "Vehicle", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],
    "WheeledVehicle": ["WheeledVehicle", "Vehicle", "ShapeBase", "GameBase", "SceneObject", "NetObject", "SimObject"],

    # Datablock Types
    "HoverVehicleData": ["HoverVehicleData", "VehicleData", "ShapeBaseData", "GameBaseData", "SimDataBlock", "SimObject"],
    "FlyingVehicleData": ["FlyingVehicleData", "VehicleData", "ShapeBaseData", "GameBaseData", "SimDataBlock", "SimObject"],
    "WheeledVehicleData": ["WheeledVehicleData", "VehicleData", "ShapeBaseData", "GameBaseData", "SimDataBlock", "SimObject"],
    "ForceFieldBareData": ["ForceFieldBareData", "GameBaseData", "SimDataBlock", "SimObject"],
    "LinearProjectileData": ["LinearProjectileData", "ProjectileData", "GameBaseData", "SimDataBlock", "SimObject"],
    "EnergyProjectileData": ["EnergyProjectileData", "GrenadeProjectileData", "ProjectileData", "GameBaseData", "SimDataBlock", "SimObject"],
    "GrenadeProjectileData": ["GrenadeProjectileData", "ProjectileData", "GameBaseData", "SimDataBlock", "SimObject"],
    "FireballAtmosphereData": ["FireballAtmosphereData", "GameBaseData", "SimDataBlock", "SimObject"],
    "TargetProjectileData": ["TargetProjectileData", "ProjectileData", "GameBaseData", "SimDataBlock", "SimObject"],
     }
    """
        FIXME: This is a huge pile of filth used for generating the inheritance hierarchy for all the various object types.
    """

    # Outputs
    global_functions = None
    type_methods = None
    global_values = None

    datablocks = None

    def __init__(self, filename):
        file_buffer = ""
        with open(filename, "r") as handle:
             file_buffer = handle.read()

        # First, we skip the first 33350 or so because there's lots of declarations
        # that the simplified regex will get tripped up on.
        chopped_lines = file_buffer.split("\r\n")
        chopped_lines = chopped_lines[33350:len(chopped_lines)]

        file_buffer = string.join(chopped_lines)

        """
            Now we perform a bit of a hack here because of unnecessary immutable
            memory bullshit: Strings in Python are immutable and due to the way
            the Regex works (can probably be fixed properly at some point),
            methods that have a semicolon in their description (most do) will cause
            the regex to match up until that semicolon, not the one that actually
            delineates the entire method. So as a quick hack, we create a mutable
            memory buffer (just a list) to do single character replacements of ;
            with ~ within the context of strings. We can't simply use replace or any
            of the regular string modification methods because they create copies of
            the string memory which bogs down the system massively at this point: times
            went down from an absolute unknown to merely ~2sec to run the entirety of this
            software using this work around.
        """
        mutable_buffer = list(file_buffer)

        string_search = re.finditer(self.string_expression, file_buffer)
        for string_occurrence in string_search:
            string_text = string_occurrence.group(0)

            for semi_occurrence in range(string_text.count(";")):
                semi_location = string_text.find(";", semi_occurrence)
                mutable_buffer[string_occurrence.start() + semi_location] = "~"

        # Implode the list together using "" as a delineator, so it just reassembles the payload
        file_buffer = string.join(mutable_buffer, "")

        # A list of tuples with the following structure: (addr, name, desc, minArgs, maxArgs)
        self.global_functions = [ ]

        global_method_add_search = re.finditer(self.global_method_add_expression, file_buffer)
        for global_function in global_method_add_search:
            global_function_source = global_function.group(0)

            opening_index = global_function_source.find("(")
            closing_index = global_function_source.rfind(")", global_function_source.count(")") - 1)

            global_function_source = global_function_source[opening_index + 1:closing_index]

            # Extract the description first; this is a huge hack due to the commas in the desc
            global_function_source, global_method_description = self._extract_description(global_function_source)
            global_method_arguments = global_function_source.split(",")

            # Strip out the global method info
            global_method_name = self._extract_name(global_method_arguments, 0)

            try:
                global_method_address = self._extract_address(global_method_arguments, 1)
                global_method_minargs = int(global_method_arguments[3])
                global_method_maxargs = int(global_method_arguments[4])

                self.global_function_count = self.global_function_count + 1

                global_function = Function(global_method_name, global_method_address, None, global_method_description, global_method_minargs, global_method_maxargs)
                self.global_functions.append(global_function)
            except ValueError:
                pass

        # A dictionary of classname to tuples with the following structure: (typename, addr, name, desc, minArgs, maxArgs)
        self.type_methods = { }
        self.type_function_counts = { }

        type_method_add_search = re.finditer(self.type_method_add_expression, file_buffer)
        for type_method in type_method_add_search:
            type_method_source = type_method.group(0)

            opening_index = type_method_source.find("(")
            closing_index = type_method_source.rfind(")")

            type_method_source = type_method_source[opening_index + 1:closing_index]

            # Extract the description first; this is a huge hack due to the commas in the desc
            type_method_source, type_method_description = self._extract_description(type_method_source)
            type_method_arguments = type_method_source.split(",")

            # Strip out the type method info
            type_method_type = self._extract_name(type_method_arguments, 1)
            type_method_name = self._extract_name(type_method_arguments, 2)
            type_method_address = self._extract_address(type_method_arguments, 3)

            try:
                type_method_minargs = int(type_method_arguments[5])
                type_method_maxargs = int(type_method_arguments[6])

                self.type_methods.setdefault(type_method_type, [])
                self.type_function_counts.setdefault(type_method_type, 0)

                self.type_function_total = self.type_function_total + 1
                self.type_function_counts[type_method_type] = self.type_function_counts[type_method_type] + 1

                self.type_methods[type_method_type] .append((type_method_type, type_method_address, type_method_name, type_method_description, type_method_minargs, type_method_maxargs))
            except ValueError:
                continue

        self.global_values = [ ]

        global_value_add_search = re.finditer(self.global_value_add_expression, file_buffer)
        for global_value in global_value_add_search:
            global_value_source = global_value.group(0)

            opening_index = global_value_source.find("(")
            closing_index = global_value_source.rfind(")")

            global_value_source = global_value_source[opening_index + 1:closing_index]
            global_value_arguments = global_value_source.split(",")

            # Strip out the global value info
            global_value_name = self._extract_name(global_value_arguments, 0)
            global_value_address = self._extract_address(global_value_arguments, 2)

            global_value_type = int(global_value_arguments[1])
            self.global_values.append(GlobalVariable(global_value_address, global_value_type, 0))

        # Extract the datablock properties now
        self.datablocks = { }

        datablock_property_add_search = re.finditer(self.datablock_property_add_expression, file_buffer)
        for datablock_property in datablock_property_add_search:
            datablock_property_source = datablock_property.group(0)

            """
                Here we don't have to worry about anything with their own scopes
                sitting above our declarations in the input file this was built for,
                so we just search backwards for the type declaration (Which is always an int)
                and use that to copy out the declaration source.
            """
            declaration_start = file_buffer.rfind("//----- ", 0, datablock_property.start())
            declaration_end = file_buffer.rfind("-", declaration_start,  datablock_property.start())
            declaration_source = file_buffer[declaration_start:declaration_end]

            calling_method = self._extract_caller(declaration_source)

            # If we don't know what it is, just add a default value and resolve it this way
            self._datablock_type_table.setdefault(calling_method, calling_method)
            datablock_type = self._datablock_type_table[calling_method]
            self.datablocks.setdefault(datablock_type, Datablock(datablock_type))

            # Pull the datablock property information now
            datablock_arguments = datablock_property_source.split(",")
            datablock_property_name = self._extract_name(datablock_arguments, 0)
            datablock_property_address = self._extract_address(datablock_arguments, 2)

            # Write it out and we should be fine.
            current_datablock = self.datablocks[datablock_type]
            current_datablock.properties[datablock_property_name] = Datablock.Property(datablock_property_name, datablock_property_address, "Bla")

    # Helper Functions
    def _extract_description(self, source):
            desc_end = source.rfind("\"")

            # We found the end, now we need to look for the previous parameter delineator
            desc_begin = -1
            ignore_delineator = True # Used for if we're in a quotation
            for index in reversed(range(desc_end)):
                current_character = source[index]

                if (current_character == "," and not ignore_delineator):
                       desc_begin = index + 1
                       break
                elif (current_character == "\""):
                    ignore_delineator = not ignore_delineator

            desc = source[desc_begin + 1:desc_end]
            desc = desc.lstrip()
            desc = desc.replace("(int)\"", "")

            source = source[0:desc_begin] + source[desc_end:len(source)]
            desc = desc.replace("~", ";")

            return source, desc

    def _extract_name(self, source, index):
        name = source[index].lstrip()
        name = name[name.find("\"") + 1:len(name)].rstrip("\" ")

        # Hack fix for the way the engine registers functions for the Sky type
        name = name.replace("(int)&off_7957AC", "Sky")

        return name

    def _extract_address(self, source, index):
        address = source[index]
        address = address[address.find("_") + 1:len(address)].rstrip("\" ")

        return address.lstrip()

    def _extract_caller(self, source):
        start = source.find("(")
        end = source.find(")", start)

        result = int(source[start + 1:end],16)
        return hex(result)[2:].upper()
