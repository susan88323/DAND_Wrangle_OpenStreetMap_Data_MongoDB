import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

OSMFILE = "vancouver.osm"

post_codes = re.compile(r'^(?!.*[DFIOQU])[A-VXY][0-9][A-Z] ?[0-9][A-Z][0-9]$', re.IGNORECASE)

def audit_postcode(bad_postcode, postcode):
    postcode = postcode.upper()
    m = post_codes.match(postcode)
    if m:
        return postcode
    else:
        bad_postcode.append(postcode)
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
                
    pprint.pprint(postcode)
    return postcode



def is_postcode(elem):
    return (elem.attrib['k'] == "addr:postcode")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    bad_postcode = []
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_postcode(tag):
                    audit_postcode(bad_postcode, tag.attrib['v'])
    osm_file.close()
    return bad_postcode

def test():
    bad_postcode = audit(OSMFILE)
    #    assert len(st_types) == 3
    pprint.pprint(bad_postcode)

if __name__ == '__main__':
    test()
