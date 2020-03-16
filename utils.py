def doc_enum(enum_class, descriptions=None):
    """
    Returns a string with the description of each value of an enumeration.

    Args:
        enum_class (Enumeration): the Enumeration to get its values documentation.
        descriptions (dictionary): each enumeration's item description. The key is the enumeration element name
            and the value is the description.

    Returns:
        String: the string listing all the enumeration values and their descriptions.
    """
    tab = " " * 4
    data = "\n| Values:\n"
    for x in enum_class:
        data += """| {:s}**{:s}**{:s} {:s}\n""".format(tab, x,
                                                       ":" if descriptions is not None else " =",
                                                       str(x.value) if descriptions is None else descriptions[x])
    return data + "| \n"