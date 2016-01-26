"""
    scraper.py

    The DokuWiki frontend for generating a web page from the scraper tree
    which is in use for the following web page:
    http://dx.no-ip.org/doku.php?id=documents:t2engine

    This software is licensed under the MIT license. Refer to LICENSE.txt for
    details.
    Copyright (c) 2016 Robert MacGregor
"""

import re
import time
import string

import scraper

def build_inheritance_tree(inheritance_list, type_names):
    inheritance_tree = ""

    for tree_element in inheritance_list:
        if (tree_element in type_names):
            inheritance_tree += "[[#%s]] -> " % tree_element
        else:
            inheritance_tree += "%s -> " % tree_element

    inheritance_tree = inheritance_tree.rstrip(" -> ")

    return inheritance_tree

# Main App
class Application(object):
    global_method_heading = "===== Global Methods (%u total) =====\r\n"
    global_method_arith_heading = "==== Arithmetic Methods (%u total) ====\r\n"
    global_method_alx_heading = "==== Audio Methods (%u total) ====\r\n"
    global_method_template = "=== %s ===\r\nAddress in Executable: 0x%s\r\n\r\nDescription: %s\r\n\r\nMinimum Arguments: %u\r\n\r\nMaximum Arguments: %u\r\n"

    global_value_heading = "===== Global Values (%u total): =====\r\n"
    global_value_template = "=== %s ===\r\nType: %s\r\n\r\nAddress in Executable: 0x%s\r\n\r\n"

    type_method_heading = "===== Type Methods (%u total methods, %u total types) =====\r\n"
    type_name_template = "==== %s ====\r\n%u total native methods\r\n\r\nInheritance: %s\r\n"
    type_method_template = "=== %s ===\r\nAddress in Executable: 0x%s\r\n\r\nDescription: %s\r\n\r\nMinimum Arguments: %u\r\n\r\nMaximum Arguments: %u\r\n"

    datablock_list_heading =  "===== Datablocks (%u total) =====\r\n"
    datablock_heading = "==== %s ====\r\nTotal Properties: %u\r\n\r\nInheritance: %s\r\n"
    datablock_property_template = "=== %s ===\r\nOffset: %s\r\nType: %s\r\n"

    def main(self):
            scrape = scraper.Scraper("Tribes2.c")

            # Now build a ref file with our compiled information
            with open("out.txt", "w") as handle:
                handle.write("====== Tribes 2 Engine Reference ======\r\n")
                handle.write("Compiled by Robert MacGregor\r\n\r\n")

                # Collect specific types of global methods
                global_arith_functions = [ ]
                global_alx_functions = [ ]

                for index, global_function in enumerate(scrape.global_functions):
                    if (len(global_function.name) != 0 and (global_function.name[0] == "m" or global_function.name.find("Vector") != -1 or global_function.name.find("Matrix") != -1)):
                        global_arith_functions.append(scrape.global_functions.pop(index))
                    elif (global_function.name.find("alx") != -1 or global_function.name.find("audio") != -1 or global_function.name.find("getAudio") != -1):
                        global_alx_functions.append(scrape.global_functions.pop(index))

                # Write the Global Method Listing
                handle.write(self.global_method_heading % scrape.global_function_count)
                handle.write("\r\n")

                for global_function in scrape.global_functions:
                    handle.write(self.global_method_template % (global_function.name, global_function.address, global_function.description, global_function.min_args - 1, global_function.max_args - 1))

                handle.write("\r\n")

                # Arithmetic Global Methods
                handle.write(self.global_method_arith_heading % len(global_arith_functions))
                handle.write("\r\n")

                for global_arith_function in global_arith_functions:
                    handle.write(self.global_method_template % (global_arith_function.name, global_arith_function.address, global_arith_function.address, global_arith_function.min_args - 1, global_arith_function.max_args - 1))

                handle.write("\r\n")

                # Audio Global Methods
                handle.write(self.global_method_alx_heading % len(global_alx_functions))
                handle.write("\r\n")

                for global_alx_function in global_alx_functions:
                    handle.write(self.global_method_template % (global_alx_function.name, global_alx_function.address, global_alx_function.description, global_alx_function.min_args - 1, global_alx_function.max_args - 1))

                handle.write("\r\n")

                # Write out the known types
                #handle.write("

                # Now the type methods
                handle.write(self.type_method_heading % (scrape.type_function_total, len(scrape.type_methods.keys())))
                handle.write("\r\n")

                for type_name in scrape.type_methods.keys():
                    inheritance_tree = "<Unknown>"
                    if (type_name in scrape.type_name_inheritance.keys()):
                        inheritance_tree = build_inheritance_tree(scrape.type_name_inheritance[type_name], scrape.type_methods.keys())
                    handle.write(self.type_name_template % (type_name, len(scrape.type_methods[type_name]), inheritance_tree))

                    # Native Methods First
                    for type_method_type, type_method_address, type_method_name, type_method_description, type_method_minargs, type_method_maxargs in scrape.type_methods[type_name]:
                        handle.write(self.type_method_template % (type_method_name, type_method_address, type_method_description, type_method_minargs - 1, type_method_maxargs - 1))

                    handle.write("\r\n")

                # And Global Values
                handle.write(self.global_value_heading % len(scrape.global_values))
                handle.write("\r\n")

                for global_value in scrape.global_values:
                    if (global_value.name[0] != "$"):
                        global_value.name = "%s%s" % ("$", global_value.name)

                    handle.write(self.global_value_template % (global_value.name, scrape.primitive_type_mapping[global_value.type_name], global_value.address))

                handle.write("\r\n")

                # Write datablocks
                handle.write(self.datablock_list_heading  % len(scrape.datablocks.keys()))

                for datablock_type in scrape.datablocks.keys():
                    inheritance_tree = "<Unknown>"
                    if (datablock_type in scrape.type_name_inheritance.keys()):
                        inheritance_tree = build_inheritance_tree(scrape.type_name_inheritance[datablock_type], scrape.type_name_inheritance[datablock_type])

                    datablock = scrape.datablocks[datablock_type]
                    handle.write(self.datablock_heading % (datablock.name, len(datablock.properties.keys()), inheritance_tree))

                    for datablock_property_name in datablock.properties.keys():
                        datablock_property = datablock.properties[datablock_property_name]

                        handle.write(self.datablock_property_template % (datablock_property.name, datablock_property.address, datablock_property.type_name))

if __name__ == "__main__":
    time_before = time.time()
    Application().main()
    time_after = time.time()

    print("Processed in %f seconds" % (time_after - time_before))
