# Used Python 3.4.0 for development
# Code to create Annotation RDF files from input Master RDF files
# Annotation RDF file contains tags "Annotation" and "HeldItem" from master RDF
# Usage - python Annotation.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Annotation/RDFs
# Example - python Annotation.py "/home/suma/Desktop/UnderGradLibrary/Master" "/home/suma/Desktop/UnderGradLibrary/Annotation"

# Annotation :
# Annotation resource attribute - url from the marc record: datafield tag "856" and subfield code "u"
# Subtags - descriptionConventions, annotates, label
# descriptionConventions - directly from master rdf
# annotates - url with work id
#   Get the work id by using the oclc number
#   Get oclc number from the marc record - datafield tag "035" and subfield code "a"
#   Scrape the page from worldcat.org/oclc/{oclc number} and get the url(contains work id) associated with the tag "schema:exampleOfWork"
# label - constant string

# HeldItem :
# Subtags - holdingFor, heldBy
# holdingFor - include the marc id in the url
# heldBy - constant string


from xml.dom.minidom import parse, parseString
from xml.sax.saxutils import escape
# from lxml import html #for scraping
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

        # Process Annotation tags

        for node in dom.getElementsByTagName('bf:Annotation'):
            url = 'http://quest.library.illinois.edu/GetMARC/one.aspx/' + bib_id + '.marc'
            response = requests.get(url)
            annotation_dom = parseString(response.content)

            annotation_tag = '<bf:Annotation rdf:resource="'

            # code to get resource attribute for the Annotation tag
            found = False
            for data_field in annotation_dom.getElementsByTagName('datafield'):
                for data_field_attr in data_field.attributes.items():
                    if data_field_attr[0] == 'tag' and data_field_attr[1] == '856':
                        for sub_field in data_field.getElementsByTagName('subfield'):
                            for sub_field_attr in sub_field.attributes.items():
                                if sub_field_attr[0] == 'code' and sub_field_attr[1] == 'u':
                                    annotation_tag += escape(sub_field.firstChild.data)
                                    break
                        found = True
                        break
                if found:
                    break

            annotation_tag += '" >'

            # code to get descriptionConventions subtag
            for description_node in node.getElementsByTagName('bf:descriptionConventions'):
                annotation_tag += description_node.toxml()

            # code to get oclc number
            found = False
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
                #     annotation_tag += '<bf:annotates rdf:resource="' + result[0].strip('> ;') + '"/>'
                # else:
                #     annotation_tag += '<bf:annotates rdf:resource=""/>'
                url = 'http://xisbn.worldcat.org/webservices/xid/oclcnum/' + oclc_num + '?method=getMetadata&format=xml&fl=*'
                response = requests.get(url)
                oclc_dom = parseString(response.content)
                oclc_node = oclc_dom.getElementsByTagName('oclcnum')
                if oclc_node.length > 0:
                    work_id = oclc_node[0].attributes["owi"].value.lstrip('owi')
                    annotation_tag += '<bf:annotates rdf:resource="' + 'http://worldcat.org/entity/work/id/' + work_id + '"/>'
                else:
                    annotation_tag += '<bf:annotates rdf:resource="http://worldcat.org/entity/work/id/"/>'

            annotation_tag += '<bf:label>Accessible anywhere on campus or with UIUC NetID</bf:label>'

            f.write(annotation_tag + '\n')

        # Process HeldItem tags

        held_item_tag = '<bf:HeldItem>\
            <bf:holdingFor rdf:resource="http://vufind.carli.illinois.edu/vf-uiu/Record/uiu_'+ bib_id +'/Description"/>\
            <bf:heldBy rdf:resource="http://id.loc.gov/vocabulary/organizations/iu"/>\
            </bf:HeldItem></bf:Annotation>'

        f.write(held_item_tag + '\n' + '</rdf:RDF>')

    except Exception as e:
        print('Error converting file - ', input_file_path, str(e))
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
    finally:
        if f is not None:
            f.close()


if __name__ == '__main__':
    try:
        #input_folder_path = sys.argv[1]
        #output_folder_path = sys.argv[2]

        input_folder_path = '/home/suma/Desktop/UnderGradLibrary/Master'
        output_folder_path = '/home/suma/Desktop/UnderGradLibrary/Annotation'
    except IndexError:
        print('Please provide all input parameters\nUsage: python Annotation.py /path/to/folder/containing/Master/RDF/files /path/to/folder/to/store/Annotation/RDFs')
        sys.exit(0)

    for root, dirs, file_names in os.walk(input_folder_path):
        for file in file_names:
            input_file_path = root + '/' + file
            bib_id = file.split('_')[0]
            output_file_name = bib_id + '_annotation.rdf'
            output_file_path = output_folder_path + '/' + output_file_name
            main(input_file_path, output_file_path, bib_id)