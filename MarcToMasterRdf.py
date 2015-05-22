# Code to convert all the MARC record files to Master RDF files
# Usage - python MarcToMasterRdf.py /path/to/zorba.xqy /path/to/folder/containing/MARCRecords /path/to/folder/to/store/output/MasterRDFs
# Example - python MarcToMasterRdf.py "/home/suma/Desktop/UnderGradLibrary/marc2bibframe-master/xbin/zorba.xqy" "/home/suma/Desktop/UnderGradLibrary/MARCXML" "/home/suma/Desktop/UnderGradLibrary/Master"

import os
import sys


def main(zorba_path, input_folder_path, output_folder_path):
    try:
        for root, dirs, file_names in os.walk(input_folder_path):
            for f in file_names:
                input_file_path = root + '/' + f
                output_file_path = output_folder_path + '/' + f.split('_')[0] + '_master.rdf'
                command = 'zorba -i -f -q' + zorba_path + ' -e marcxmluri:="'+ input_file_path + '" -e serialization:="rdfxml" -e baseuri:="http://www.base-uri.com/"  > ' + output_file_path
                os.system(command)
    except Exception as e:
        print('Error converting file ', input_file_path, '\nError: ', e, '\n')


if __name__ == "__main__":
    try:
        zorba_path = sys.argv[1]
        input_folder_path = sys.argv[2]
        output_folder_path = sys.argv[3]

        main(zorba_path, input_folder_path, output_folder_path)

    except IndexError:
        print('Please provide all input parameters\nUsage: python MarcToMasterRdf.py /path/to/zorba.xqy /path/to/folder/containing/MARCRecords /path/to/folder/to/store/output/MasterRDFs\n')
