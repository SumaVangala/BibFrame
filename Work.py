# Used Python 3.4.0 for development
# Code to create Work RDF files from input Master RDF files
# Work RDF file contains tag Work from master RDF
# Usage - python Work.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Work/RDFs
# Example - python Work.py "/home/suma/Desktop/UnderGradLibrary/Master" "/home/suma/Desktop/UnderGradLibrary/Work"

# Work :
# about attribute - url with work id
#   Get the work id by using the oclc number
#   Get oclc number from the marc record - datafield tag "035" and subfield code "a"
#   Scrape the page from worldcat.org/oclc/{oclc number} and get the url(contains work id) associated with the tag "schema:exampleOfWork"
# hasInstance - url with bib id
# relatedTo - url from the marc record: datafield tag "856" and subfield code "u"
# type, authorizedAccessPoint - from master rdf
# creator - resource url with viaf id for all the Person tags
# contentCategory, language - from master rdf
# subject - resource url with subject headings for all the Topic tags
# classificationLcc, classificationDdc - from master rdf
# series -
#   Take title from second work tag and search in loc under authority names
#   If multiple matched records are returned - use title for disambiguation - using FuzzyLogic


from xml.dom.minidom import parse, parseString
from difflib import SequenceMatcher as SM
from xml.sax.saxutils import escape
# from lxml import html
import urllib
import requests
import sys
import os


def main(input_file_path, output_file_path, bib_id):
    f = None
    try:
        dom = parse(input_file_path)
        f = open(output_file_path, 'w+')

        f.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
        f.write('<rdf:RDF xmlns:relators="http://id.loc.gov/vocabulary/relators/" xmlns:madsrdf="http://www.loc.gov/mads/rdf/v1#" xmlns:bf="http://bibframe.org/vocab/" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">' + '\n')

        work_tag = ''
        node_list = dom.getElementsByTagName('bf:Work')
        if node_list.length > 0:
            url = 'http://quest.library.illinois.edu/GetMARC/one.aspx/' + bib_id + '.marc'
            response = requests.get(url)
            annotation_dom = parseString(response.content)

            work_tag = '<bf:Work rdf:about="' + get_work_id(annotation_dom) + '">'
            work_tag += '<bf:hasInstance rdf:resource="http://vufind.carli.illinois.edu/vf-uiu/Record/uiu_' + bib_id + '/Description"/>'
            work_tag += '<bf:relatedTo rdf:resource="' + get_relatedto_resource_url(annotation_dom) + '"/>'

            for sub_node in node_list[0].getElementsByTagName('rdf:type'):
                work_tag += sub_node.toxml()

            sub_node = node_list[0].getElementsByTagName('bf:authorizedAccessPoint')
            if sub_node.length > 0:
                work_tag += sub_node[0].toxml()

            sub_node = dom.getElementsByTagName('bf:titleValue')
            if sub_node.length > 0:
                work_tag += '<bf:workTitle>' + escape(sub_node[0].firstChild.data) + '</bf:workTitle>'
                # new_element = dom.createElement("bf:workTitle")
                # text_node = dom.createTextNode(sub_node[0].firstChild.data)
                # new_element.appendChild(text_node)
                # work_tag += new_element.toxml()

            for node in dom.getElementsByTagName('bf:Person'):
                label_node = node.getElementsByTagName('bf:label')
                if label_node.length > 0:
                    label = label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8')
                    work_tag += ' <bf:creator rdf:resource="' + get_creator_resource_url(dom, label) + '"/>'

            for sub_node in node_list[0].getElementsByTagName('bf:contentCategory'):
                work_tag += sub_node.toxml()

            for sub_node in node_list[0].getElementsByTagName('bf:language'):
                work_tag += sub_node.toxml()

            for node in dom.getElementsByTagName('bf:Topic'):
                subject_resource_url = ''

                label_node = node.getElementsByTagName('bf:label')
                if label_node.length > 0:
                    member_of_mads = node.getElementsByTagName('madsrdf:isMemberOfMADSScheme')
                    if member_of_mads.length > 0:
                        resource = member_of_mads[0].attributes["rdf:resource"]
                        if 'mesh' in resource.value.lower():
                            subject_resource_url = get_mesh_heading(label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))
                        else:
                            subject_resource_url = get_loc_heading(label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))
                            if subject_resource_url == '':
                                subject_resource_url = get_fast_heading(label_node[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))

                work_tag += '<bf:subject rdf:resource="' + subject_resource_url + '"/>'

            for sub_node in node_list[0].getElementsByTagName('bf:classificationLcc'):
                work_tag += sub_node.toxml()

            for sub_node in node_list[0].getElementsByTagName('bf:classificationDdc'):
                work_tag += sub_node.toxml()

            series_node = node_list[0].getElementsByTagName('bf:series')
            resource_url = ''
            if series_node.length > 0 and node_list.length > 1:
                work_node = node_list[1]
                title = work_node.getElementsByTagName('bf:title')
                if title.length > 0:
                    resource_url = get_loc_authority_name(title[0].firstChild.data.encode('ascii', 'ignore').decode('utf-8'))
                    work_tag += '<rdf:series rdf:resource="' + resource_url + '"/>'

            work_tag += '</bf:Work>'

            if series_node.length > 0 and node_list.length > 1:
                node_list[1].attributes["rdf:about"] = resource_url
                work_tag += node_list[1].toxml()

        f.write(work_tag + '\n' + '</rdf:RDF>')

    except Exception as e:
        print('Error converting file - ', input_file_path, str(e))
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
    finally:
        if f is not None:
            f.close()


def get_work_id(annotation_dom):
    # code to get oclc number
    found = False
    work_id_link = 'http://worldcat.org/entity/work/id/'
    oclc_num = ''
    for data_field in annotation_dom.getElementsByTagName('datafield'):
        for data_field_attr in data_field.attributes.items():
            if data_field_attr[0] == 'tag' and data_field_attr[1] == '035':
                for sub_field in data_field.getElementsByTagName('subfield'):
                    for sub_field_attr in sub_field.attributes.items():
                        if sub_field_attr[0] == 'code' and sub_field_attr[1] == 'a':
                            oclc_num = sub_field.firstChild.data
                            break
                found = True
                break
        if found:
            break

    # code to get work id using oclc number from worldcat api
    oclc_num = oclc_num.strip('(OCoLC)ocn')
    if oclc_num and oclc_num.strip():
        # page = requests.get('http://www.worldcat.org/oclc/' + oclc_num)
        # tree = html.fromstring(page.text)
        # result = tree.xpath('//text()[contains(.,"http://worldcat.org/entity/work/id")]')
        # if len(result) > 0:
        #     work_id_link = result[0].strip('> ;')
        url = 'http://xisbn.worldcat.org/webservices/xid/oclcnum/' + oclc_num + '?method=getMetadata&format=xml&fl=*'
        response = requests.get(url)
        oclc_dom = parseString(response.content)
        oclc_node = oclc_dom.getElementsByTagName('oclcnum')
        if oclc_node.length > 0:
            work_id = oclc_node[0].attributes["owi"].value.lstrip('owi')
            work_id_link += work_id

    return work_id_link


def get_relatedto_resource_url(annotation_dom):
    for data_field in annotation_dom.getElementsByTagName('datafield'):
        for data_field_attr in data_field.attributes.items():
            if data_field_attr[0] == 'tag' and data_field_attr[1] == '856':
                for sub_field in data_field.getElementsByTagName('subfield'):
                    for sub_field_attr in sub_field.attributes.items():
                        if sub_field_attr[0] == 'code' and sub_field_attr[1] == 'u':
                            return escape(sub_field.firstChild.data)

    return ''


def get_creator_resource_url(dom, label):
    url = 'https://viaf.org/viaf/search?query=local.corporateNames+all+"' + label + '"&sortKeys=holdingscount&recordSchema=BriefVIAF&httpAccept=text/xml'
    response = requests.get(url)
    person_dom = parseString(response.content)
    record_count = person_dom.getElementsByTagName('numberOfRecords')
    resource_url = ''

    if record_count.length > 0:
        if record_count[0].firstChild.data != '0':
            resource_url = get_viaf_id(dom, person_dom, record_count[0].firstChild.data)
        elif record_count[0].firstChild.data == '0':
            url = 'https://viaf.org/viaf/search?query=local.personalNames+all+"' + label + '"&sortKeys=holdingscount&recordSchema=BriefVIAF&httpAccept=text/xml'
            response = requests.get(url)
            person_dom = parseString(response.content)
            record_count = person_dom.getElementsByTagName('numberOfRecords')

            if record_count.length > 0:
                if record_count[0].firstChild.data != '0':
                    resource_url = get_viaf_id(dom, person_dom, record_count[0].firstChild.data)
                elif record_count[0].firstChild.data == '0':
                    resource_url = ''

    return escape(resource_url)


def get_viaf_id(dom, person_dom, count):
    resource_url = 'http://viaf.org/viaf/'

    if count == '1':
        viaf_node = person_dom.getElementsByTagName('v:viafID')
        if viaf_node.length > 0:
            resource_url = 'http://viaf.org/viaf/' + viaf_node[0].firstChild.data
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
                    resource_url = 'http://viaf.org/viaf/' + viaf_node[0].firstChild.data

    return resource_url


def get_mesh_heading(label):
    resource_url = ''

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
            resource_url = uri_node[0].firstChild.data

    return resource_url


def get_loc_heading(label):
    resource_url = ''

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
            resource_url = subject_heading

    return resource_url


def get_fast_heading(label):
    resource_url = ''

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
                resource_url = subject_heading
                break

    return resource_url


def get_loc_authority_name(label):
    resource_url = ''

    url = 'http://id.loc.gov/search/?q="' + label + '"&q=cs%3Ahttp%3A%2F%2Fid.loc.gov%2Fauthorities%2Fnames&format=atom'
    response = requests.get(url)
    series_dom = parseString(response.content)

    final_record = None
    final_score = 0
    s1 = label.lower()
    for entry_list in series_dom.getElementsByTagName('entry'):
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
            authority_name = 'http://id.loc.gov/authorities/names/' + entry_node[0].firstChild.data.split('/')[length-1]
            resource_url = authority_name

    return resource_url


if __name__ == '__main__':
    try:
        #input_folder_path = sys.argv[1]
        #output_folder_path = sys.argv[2]

        input_folder_path = '/home/suma/Desktop/UnderGradLibrary/Master'
        output_folder_path = '/home/suma/Desktop/UnderGradLibrary/Work'
    except IndexError:
        print('Please provide all input parameters\nUsage: python Work.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Work/RDFs')
        sys.exit(0)

    for root, dirs, file_names in os.walk(input_folder_path):
        for file in file_names:
            input_file_path = root + '/' + file
            bib_id = file.split('_')[0]
            output_file_name = bib_id + '_work.rdf'
            output_file_path = output_folder_path + '/' + output_file_name
            main(input_file_path, output_file_path, bib_id)
