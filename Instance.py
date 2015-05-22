# Used Python 3.4.0 for development
# Code to create Instance RDF files from input Master RDF files
# Instance RDF file contains tag Instance from master RDF
# Usage - python Instance.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Instance/RDFs
# Example - python Instance.py "/home/suma/Desktop/UnderGradLibrary/Master" "/home/suma/Desktop/UnderGradLibrary/Instance"

# Instance :
# about attribute - url with bib id
# relatedTo - url from the marc record: datafield tag "856" and subfield code "u"
# title, type, publication, modeOfIssuance, illustrationNote, titleStatement, formDesignation - from master rdf
# providerStatement, note, systemNumber, stockNumber, mediaCategory, carrierCategory - from master rdf
# instanceOf - url with work id
#   Get the work id by using the oclc number
#   Get oclc number from the marc record - datafield tag "035" and subfield code "a"
#   Scrape the page from worldcat.org/oclc/{oclc number} and get the url(contains work id) associated with the tag "schema:exampleOfWork"
# isbn - take isbn13 from master rdf
# descriptionConventions - from Annotation tag


from xml.dom.minidom import parse, parseString
# from lxml import html
from xml.sax.saxutils import escape
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

        instance_tag = '<bf:Instance rdf:about="http://vufind.carli.illinois.edu/vf-uiu/Record/uiu_' + bib_id + '/Description">'

        url = 'http://quest.library.illinois.edu/GetMARC/one.aspx/' + bib_id + '.marc'
        response = requests.get(url)
        annotation_dom = parseString(response.content)
        instance_tag += '<bf:relatedTo rdf:resource="' + get_relatedto_resource_url(annotation_dom) + '"/>'

        title = dom.getElementsByTagName('bf:titleValue')
        if title.length > 0:
            instance_tag += '<bf:title>' + escape(title[0].firstChild.data) + '</bf:title>'
            # new_element = dom.createElement("bf:title")
            # text_node = dom.createTextNode(title[0].firstChild.data)
            # new_element.appendChild(text_node)
            # instance_tag += new_element.toxml()

        instance_node = dom.getElementsByTagName('bf:Instance')
        if instance_node.length > 0:
            for type_node in instance_node[0].getElementsByTagName('rdf:type'):
                instance_tag += type_node.toxml()

            for publication_node in instance_node[0].getElementsByTagName('bf:publication'):
                instance_tag += publication_node.toxml()

            for issuance_mode_node in instance_node[0].getElementsByTagName('bf:modeOfIssuance'):
                instance_tag += issuance_mode_node.toxml()

            for illustration_node in instance_node[0].getElementsByTagName('bf:illustrationNote'):
                instance_tag += illustration_node.toxml()

            for title_statement_node in instance_node[0].getElementsByTagName('bf:titleStatement'):
                instance_tag += title_statement_node.toxml()

            for form_designation_node in instance_node[0].getElementsByTagName('bf:formDesignation'):
                instance_tag += form_designation_node.toxml()

            for provider_node in instance_node[0].getElementsByTagName('bf:providerStatement'):
                instance_tag += provider_node.toxml()

            for note_node in instance_node[0].getElementsByTagName('bf:note'):
                instance_tag += note_node.toxml()

            for system_num_node in instance_node[0].getElementsByTagName('bf:systemNumber'):
                instance_tag += system_num_node.toxml()

            for stock_num_node in instance_node[0].getElementsByTagName('bf:stockNumber'):
                instance_tag += stock_num_node.toxml()

            for media_node in instance_node[0].getElementsByTagName('bf:mediaCategory'):
                instance_tag += media_node.toxml()

            for carrier_node in instance_node[0].getElementsByTagName('bf:carrierCategory'):
                instance_tag += carrier_node.toxml()

            instance_tag += '<bf:instanceOf rdf:resource="' + get_work_id_url(annotation_dom) + '"/>'

            isbn_node = instance_node[0].getElementsByTagName('bf:isbn13')
            if isbn_node.length > 0:
                isbn_num = isbn_node[0].attributes['rdf:resource'].value.lstrip('http://isbn.example.org/')
                instance_tag += ' <bf:isbn>\
                                    <bf:Identifier>\
                                        <bf:identifierValue>' + isbn_num + '</bf:identifierValue>\
                                        <bf:identifierScheme>isbn</bf:identifierScheme>\
                                    </bf:Identifier>\
                                </bf:isbn>'

            annotation_node = dom.getElementsByTagName('bf:Annotation')
            if annotation_node.length > 0:
                for description_node in annotation_node[0].getElementsByTagName('bf:descriptionConventions'):
                    instance_tag += description_node.toxml()

        f.write(instance_tag + '</bf:Instance></rdf:RDF>')

    except Exception as e:
        print('Error converting file - ', input_file_path, str(e))
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
    finally:
        if f is not None:
            f.close()


def get_relatedto_resource_url(annotation_dom):
    for data_field in annotation_dom.getElementsByTagName('datafield'):
        for data_field_attr in data_field.attributes.items():
            if data_field_attr[0] == 'tag' and data_field_attr[1] == '856':
                for sub_field in data_field.getElementsByTagName('subfield'):
                    for sub_field_attr in sub_field.attributes.items():
                        if sub_field_attr[0] == 'code' and sub_field_attr[1] == 'u':
                            return escape(sub_field.firstChild.data)

    return ''


def get_work_id_url(annotation_dom):
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


if __name__ == '__main__':
    try:
        #input_folder_path = sys.argv[1]
        #output_folder_path = sys.argv[2]

        input_folder_path = '/home/suma/Desktop/UnderGradLibrary/Master'
        output_folder_path = '/home/suma/Desktop/UnderGradLibrary/Instance'
    except IndexError:
        print('Please provide all input parameters\nUsage: python Instance.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Instance/RDFs')
        sys.exit(0)

    for root, dirs, file_names in os.walk(input_folder_path):
        for file in file_names:
            input_file_path = root + '/' + file
            bib_id = file.split('_')[0]
            output_file_name = bib_id + '_instance.rdf'
            output_file_path = output_folder_path + '/' + output_file_name
            main(input_file_path, output_file_path, bib_id)