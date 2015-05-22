# Used Python 3.4.0 for development
# Code to create Authority RDF files from input Master RDF files
# Authority RDF file contains tags Person and Topic from master RDF
# Usage - python Authority.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Authority/RDFs
# Example - python Authority.py "/home/suma/Desktop/UnderGradLibrary/Master" "/home/suma/Desktop/UnderGradLibrary/Authority"

# Person :
# Take the label and lookup VIAF for VIAF ID
# First check under corporate names, if not found then check personal names
# If multiple records are returned - use title for disambiguation - using FuzzyLogic

# Topic :
# If the title is a mesh title - search MESH headings
# If not mesh heading search library of congress
# If library of congress returns no results - search FAST
# If FAST returns no results - empty heading
# If multiple matched records are returned - use title for disambiguation - using FuzzyLogic


from xml.dom.minidom import parse, parseString
from difflib import SequenceMatcher as SM
import urllib
import requests
import sys
import os


def main(input_file_path, output_file_path):
    f = None
    try:
        dom = parse(input_file_path)

        f = open(output_file_path, 'w+')

        f.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
        f.write('<rdf:RDF xmlns:relators="http://id.loc.gov/vocabulary/relators/" xmlns:madsrdf="http://www.loc.gov/mads/rdf/v1#" xmlns:bf="http://bibframe.org/vocab/" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">' + '\n')

        # Process Person tags
        for node in dom.getElementsByTagName('bf:Person'):
            label_node = node.getElementsByTagName('bf:label')
            if label_node.length > 0:

                url = 'https://viaf.org/viaf/search?query=local.corporateNames+all+"' + label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8') + '"&sortKeys=holdingscount&recordSchema=BriefVIAF&httpAccept=text/xml'
                response = requests.get(url)
                person_dom = parseString(response.content)
                record_count = person_dom.getElementsByTagName('numberOfRecords')

                if record_count.length > 0:

                    if record_count[0].firstChild.data != '0':
                        get_viaf_id(dom, person_dom, node, record_count[0].firstChild.data)
                    elif record_count[0].firstChild.data == '0':
                        url = 'https://viaf.org/viaf/search?query=local.personalNames+all+"' + label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8')  + '"&sortKeys=holdingscount&recordSchema=BriefVIAF&httpAccept=text/xml'
                        response = requests.get(url)
                        person_dom = parseString(response.content)
                        record_count = person_dom.getElementsByTagName('numberOfRecords')

                        if record_count.length > 0:
                            if record_count[0].firstChild.data != '0':
                                get_viaf_id(dom, person_dom, node, record_count[0].firstChild.data)
                            elif record_count[0].firstChild.data == '0':
                                node.attributes["rdf:about"] = 'http://viaf.org/viaf/'
                                print('No result viaf id returned for ', url, '\n')

            f.write(node.toxml() + '\n')

        # Process Topic tags
        for node in dom.getElementsByTagName('bf:Topic'):
            label_node = node.getElementsByTagName('bf:label')
            if label_node.length > 0:
                member_of_mads = node.getElementsByTagName('madsrdf:isMemberOfMADSScheme')
                if member_of_mads.length > 0:
                    resource = member_of_mads[0].attributes["rdf:resource"]
                    if 'mesh' in resource.value.lower():
                        get_mesh_heading(node, label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))
                    else:
                        subject_found = get_loc_heading(node, label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))
                        if not subject_found:
                            get_fast_heading(node, label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))

            f.write(node.toxml() + '\n')

        f.write('</rdf:RDF>')
    except Exception as e:
        print('Error converting file - ', input_file_path, ' ', str(e))
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
    finally:
        if f is not None:
            f.close()


def get_viaf_id(dom, person_dom, node, count):
    if count == '1':
        viaf_node = person_dom.getElementsByTagName('v:viafID')
        if viaf_node.length > 0:
            viaf_id = 'http://viaf.org/viaf/' + viaf_node[0].firstChild.data
            node.attributes["rdf:about"] = viaf_id
        else:
            node.attributes["rdf:about"] = 'http://viaf.org/viaf/'

    elif count != '0':
        title_node = dom.getElementsByTagName('bf:titleValue')
        if title_node.length > 0:
            title = title_node[0].firstChild.data  # using title for disambiguation when multiple records are returned

            s1 = title.lower().encode('ascii', 'ignore').decode('utf-8')
            final_record = None
            final_score = 0
            for record in person_dom.getElementsByTagName('record'):
                for title_list in record.getElementsByTagName('v:title'):
                    s2 = title_list.firstChild.data.lower().encode('ascii', 'ignore').decode('utf-8')
                    score = SM(None, s1, s2).ratio()  # Fuzzy Search
                    if score > final_score:
                        final_score = score
                        final_record = record

            if final_record is not None:
                viaf_node = final_record.getElementsByTagName('v:viafID')
                if viaf_node.length > 0:
                    viaf_id = 'http://viaf.org/viaf/' + viaf_node[0].firstChild.data
                    node.attributes["rdf:about"] = viaf_id
                else:
                    node.attributes["rdf:about"] = 'http://viaf.org/viaf/'


def get_mesh_heading(node, label):
    # SPARQL query
    query = 'PREFIX mesh: <http://id.nlm.nih.gov/mesh/>\
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>\
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\
    SELECT ?d ?dName FROM <http://id.nlm.nih.gov/mesh2014> WHERE { ?d a meshv:Descriptor .?d meshv:concept ?c .?d rdfs:label ?dName .?c rdfs:label ?cName FILTER(REGEX(?dName,"'+ label +'","i") || REGEX(?cName,"'+ label +'","i"))} ORDER BY ?d'

    url = 'http://id.nlm.nih.gov/mesh/servlet/query?query=' + urllib.parse.quote_plus(query) + '&format=XML&limit=10&offset=0&inference=true'
    response = requests.get(url)
    topic_dom = parseString(response.content)
    s1 = label.lower()
    final_record = None
    final_score = 0
    for result_list in topic_dom.getElementsByTagName('result'):
        literal = result_list.getElementsByTagName('literal')
        if literal.length > 0:
            s2 = literal[0].firstChild.data.lower()
            score = SM(None, s1, s2).ratio()  # Fuzzy Search
            if score > final_score:
                final_score = score
                final_record = result_list
    if final_record is not None:
        uri_node = final_record.getElementsByTagName('uri')
        if uri_node.length > 0:
            node.attributes["rdf:about"] = uri_node[0].firstChild.data
    else:
        node.attributes["rdf:about"] = ''


def get_loc_heading(node, label):
    url = 'http://id.loc.gov/search/?q="' + label + '"&q=cs%3Ahttp%3A%2F%2Fid.loc.gov%2Fauthorities%2Fsubjects&format=atom'
    response = requests.get(url)
    topic_dom = parseString(response.content)

    final_record = None
    final_score = 0
    s1 = label.lower()
    for entry_list in topic_dom.getElementsByTagName('entry'):
        entry_title = entry_list.getElementsByTagName('title')
        if entry_title.length > 0:
            s2 = entry_title[0].firstChild.data.lower().encode('ascii', 'ignore').decode('utf-8')
            score = SM(None, s1, s2).ratio()  # Fuzzy Search
            if score > final_score:
                final_score = score
                final_record = entry_list

    if final_record is not None:
        entry_node = final_record.getElementsByTagName('id')
        if entry_node.length > 0:
            length = len(entry_node[0].firstChild.data.split('/'))
            subject_heading = 'http://id.loc.gov/authorities/subjects/' + entry_node[0].firstChild.data.split('/')[length-1]
            node.attributes["rdf:about"] = subject_heading
            return True

    return False


def get_fast_heading(node, label):
    url = 'http://experimental.worldcat.org/fast/search?query=cql.any+all+"' + label + '"&sortKeys=usage&maximumRecords=20&httpAccept=application/xml'
    response = requests.get(url)
    topic_dom = parseString(response.content)

    final_record = None
    final_score = 0
    s1 = label.lower()

    for record_list in topic_dom.getElementsByTagName('mx:record'):
        for data_field in record_list.getElementsByTagName('mx:datafield'):
            for data_field_attr in data_field.attributes.items():
                if data_field_attr[0] == 'tag' and data_field_attr[1] == '150':
                    s2 = ''
                    for sub_field in data_field.getElementsByTagName('mx:subfield'):
                        # for sub_field_attr in sub_field.attributes.items():
                        #     if sub_field_attr[0] == 'code' and sub_field_attr[1] == 'a':
                        s2 += sub_field.firstChild.data.lower() + ' '
                    s2 = s2.rstrip()
                    score = SM(None, s1, s2).ratio()  # Fuzzy Search
                    if score > final_score:
                        final_score = score
                        final_record = record_list
                    break

    if final_record is not None:
        for control_fields in final_record.getElementsByTagName('mx:controlfield'):
            if control_fields.attributes["tag"].value == '001':
                fast_heading = control_fields.firstChild.data.lstrip("fst0")
                subject_heading = 'http://experimental.worldcat.org/fast/' + fast_heading + '/'
                node.attributes["rdf:about"] = subject_heading
                break
    else:
        node.attributes["rdf:about"] = ''


if __name__ == '__main__':
    try:
        #input_folder_path = sys.argv[1]
        #output_folder_path = sys.argv[2]

        input_folder_path = '/home/suma/Desktop/UnderGradLibrary/Master'
        output_folder_path = '/home/suma/Desktop/UnderGradLibrary/Authority'
    except IndexError:
        print('Please provide all input parameters\nUsage: python Authority.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Authority/RDFs')
        sys.exit(0)

    for root, dirs, file_names in os.walk(input_folder_path):
        for file in file_names:
            input_file_path = root + '/' + file
            output_file_name = file.split('_')[0] + '_authority.rdf'
            output_file_path = output_folder_path + '/' + output_file_name
            main(input_file_path, output_file_path)