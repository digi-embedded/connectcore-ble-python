# Copyright 2022, Digi International Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

def hex_to_string(byte_array, pretty=True):
    """
    Returns the provided bytearray in string format.

    Args:
        byte_array (Bytearray): the bytearray to format as string.
        pretty (Boolean, optional): `True` to use a white space separator between bytes,
                                    `False` otherwise.

    Returns:
        String: the bytearray formatted as string.
    """
    separator = " " if pretty else ""
    return separator.join(["%02X" % i for i in byte_array])


def doc_enum(enum_class, descriptions=None):
    """
    Returns a string with the description of each value of an enumeration.

    Args:
        enum_class (Enumeration): the Enumeration to get its values documentation.
        descriptions (dictionary): each enumeration's item description. The key is the enumeration
                                   element name and the value is the description.

    Returns:
        String: the string listing all the enumeration values and their descriptions.
    """
    tab = " "*4
    data = "\n| Values:\n"
    for item in enum_class:
        data += """| {:s}**{:s}**{:s} {:s}\n""".format(
            tab, str(item), ":" if descriptions is not None else " =",
            str(item.value) if descriptions is None else descriptions[item])
    return data + "| \n"
