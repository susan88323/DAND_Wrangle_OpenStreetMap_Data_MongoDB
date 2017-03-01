#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
"""
    Your task is to wrangle the data and transform the shape of the data
    into the model we mentioned earlier. The output should be a list of dictionaries
    that look like this:
    
    {
    "id": "2406124091",
    "type: "node",
    "visible":"true",
    "created": {
    "version":"2",
    "changeset":"17206049",
    "timestamp":"2013-08-03T16:43:42Z",
    "user":"linuxUser16",
    "uid":"1219059"
    },
    "pos": [41.9757030, -87.6921867],
    "address": {
    "housenumber": "5157",
    "postcode": "60625",
    "street": "North Lincoln Ave"
    },
    "amenity": "restaurant",
    "cuisine": "mexican",
    "name": "La Cabana De Don Luis",
    "phone": "1 (773)-271-5176"
    }
    
    You have to complete the function 'shape_element'.
    We have provided a function that will parse the map file, and call the function with the element
    as an argument. You should return a dictionary, containing the shaped data for that element.
    We have also provided a way to save the data in a file, so that you could use
    mongoimport later on to import the shaped data into MongoDB.
    
    Note that in this exercise we do not use the 'update street name' procedures
    you worked on in the previous exercise. If you are using this code in your final
    project, you are strongly encouraged to use the code from previous exercise to
    update the street names before you save them to JSON.
    
    In particular the following things should be done:
    - you should process only 2 types of top level tags: "node" and "way"
    - all attributes of "node" and "way" should be turned into regular key/value pairs, except:
    - attributes in the CREATED array should be added under a key "created"
    - attributes for latitude and longitude should be added to a "pos" array,
    for use in geospacial indexing. Make sure the values inside "pos" array are floats
    and not strings.
    - if the second level tag "k" value contains problematic characters, it should be ignored
    - if the second level tag "k" value starts with "addr:", it should be added to a dictionary "address"
    - if the second level tag "k" value does not start with "addr:", but contains ":", you can
    process it in a way that you feel is best. For example, you might split it into a two-level
    dictionary like with "addr:", or otherwise convert the ":" to create a valid key.
    - if there is a second ":" that separates the type/direction of a street,
    the tag should be ignored, for example:
    
    <tag k="addr:housenumber" v="5158"/>
    <tag k="addr:street" v="North Lincoln Avenue"/>
    <tag k="addr:street:name" v="Lincoln"/>
    <tag k="addr:street:prefix" v="North"/>
    <tag k="addr:street:type" v="Avenue"/>
    <tag k="amenity" v="pharmacy"/>
    
    should be turned into:
    
    {...
    "address": {
    "housenumber": 5158,
    "street": "North Lincoln Avenue"
    }
    "amenity": "pharmacy",
    ...
    }
    
    - for "way" specifically:
    
    <nd ref="305896090"/>
    <nd ref="1719825889"/>
    
    should be turned into
    "node_refs": ["305896090", "1719825889"]
    """

OSMFILE = "vancouver.osm"

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$|St. Vancouver', re.IGNORECASE)
street_end_with_number_re = re.compile(r'\d+$')
post_codes = re.compile(r'^(?!.*[DFIOQU])[A-VXY][0-9][A-Z] ?[0-9][A-Z][0-9]$', re.IGNORECASE)


CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

# For street type check
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons", "Broadway", "Kingsway", "Way", "West", "Crescent", "East",
            "North", "South", "Connector", "Jarvis", "Highway", "Mews", "Alley", "Mall", "Walk",
            "Esplanade", "Jervis", "Nanaimo", "Pender", "Terminal", "Broughton"]

mapping = { " St\.": "Street",
            "Ave": "Avenue",
            "Rd\.": "Road",
            " St": "Street",
            "Blvd": "Boulevard",
            "Steet": "Street",
            " Venue": " Avenue",
            "W ": "West ",
            "Denmanstreet": "Denman Street",
            " E": " East",
            " street": " Street",
            "W\. ": "West ",
            " W\.": " West",
            " W": "West"
        }

special_keys = [" St.", " St", " W"]

def audit_street_type(street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
#            street_types[street_type].add(street_name)
            return update_name(street_name, mapping)
    return street_name


def is_street_name(address_key):
    return (address_key == "addr:street")

def update_name(name, mapping):
    
    if " St " in name:
        name = re.sub(" St ", " Street ", name)
    
    for key in mapping.iterkeys():
        if re.search(key, name):
            if key in special_keys:
                if street_end_with_number_re.search(name):
                    continue
                else:
                    name = re.sub(street_type_re, mapping[key], name)
            else:
                name = re.sub(key, mapping[key], name)
                if key == " Venue":
                    break

    return name

def audit_postcode(postcode):
    postcode = postcode.upper()
    m = post_codes.match(postcode)
    if m:
        return postcode
    else:
#        bad_postcode.append(postcode)
        # Correct postal code
        if "BC " in postcode:
            postcode = postcode[3:]
        elif "OC" in postcode:
            postcode = postcode.replace("OC", "0C")
        elif "V5T" in postcode:
            postcode = postcode[8:]
        elif "," in postcode:
            postcode = postcode[:7]
        elif "6HH" in postcode:
            postcode = postcode.replace("6HH", "6H")
        elif "V5N5H7 " in postcode:
            postcode = postcode[:6]

    return postcode



def is_postcode(postcode_key):
    return (postcode_key == "addr:postcode")


def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way" :
        # YOUR CODE HERE
        node = {'created': {}, 'type': element.tag}
        
        # Deal with lat and lon
        if 'lat' in element.attrib and 'lon' in element.attrib:
            node['pos'] = [float(element.attrib['lat']), float(element.attrib['lon'])]
        
        # Deal with other attributes
        for k in element.attrib:
            if k in CREATED:
                node['created'][k] = element.attrib[k]
            elif k == 'lat' or k == 'lon':
                continue
            else:
                node[k] = element.attrib[k]
        
        # Deal with second level tag
        # for nd ref node in way
        node_refs = []
        for nd in element.iter('nd'):
            node_refs.append(nd.attrib['ref'])
        
        if len(node_refs) > 0:
            node['node_refs'] = node_refs
        
        # for the other tags
        for tag in element.iter('tag'):
            k = tag.attrib['k']
            v = tag.attrib['v']
            if problemchars.search(k):
                continue
            elif k.startswith('addr:'):
                components = k.split(':')
                if len(components) == 2:
                    if 'address' not in node:
                        node['address'] = {}
                    
                    if is_street_name(k):
                        v = audit_street_type(v)
                    elif is_postcode(k):
                        v = audit_postcode(v)
                    node['address'][components[1]] = v
            else:
#                node[k] = v
                components = k.split(':')
                if len(components) == 1:
                    node[k] = v
                elif len(components) == 2:
                    if components[0] not in node:
                        node[components[0]] = {}
                    node[components[0]] = v

        return node
    else:
        return None


def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

def test():
    # NOTE: if you are running this code on your computer, with a larger dataset,
    # call the process_map procedure with pretty=False. The pretty=True option adds
    # additional spaces to the output, making it significantly larger.
    data = process_map('sample_vancouver.osm', False)
    #pprint.pprint(data)
    


if __name__ == "__main__":
    test()
