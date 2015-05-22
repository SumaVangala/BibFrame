# Code to generate html file for every bib id
# Usage - Usage: python HTMLGeneration.py /path/to/folder/containing/Master/RDF/files /path/to/folder/containing/Authority/RDF/files /path/to/folder/containing/Instance/RDF/files /path/to/folder/to/store/HTML/Templates
# Example - python HTMLGeneration.py "/home/suma/Desktop/UnderGradLibrary/Master" "/home/suma/Desktop/UnderGradLibrary/Authority" "/home/suma/Desktop/UnderGradLibrary/Instance" "/home/suma/Desktop/UnderGradLibrary/Templates"


from xml.dom.minidom import parse
import os
import sys
from string import Template
import requests


def main(input_master_file_path, input_authority_file_path, input_instance_file_path, output_file_path, bib_id):
    f = None
    try:
        authority_dom = parse(input_authority_file_path)
        instance_dom = parse(input_instance_file_path)
        master_dom = parse(input_master_file_path)
        f = open(output_file_path, 'w+')

        # Get the title
        title = ''
        for title_node in instance_dom.getElementsByTagName('bf:title'):
            title = title_node.firstChild.data
            break

        # Get the resource url
        resource_url = ''
        for resource_node in instance_dom.getElementsByTagName('bf:relatedTo'):
            resource_url = resource_node.attributes['rdf:resource'].value
            break

        # Get publisher name
        publisher = ''
        publication_node = instance_dom.getElementsByTagName('bf:publication')
        if publication_node.length > 0:
            label_node = publication_node[0].getElementsByTagName('bf:label')
            if label_node.length > 0:
                publisher = label_node[0].firstChild.data

        # Get classification Lcc and language from work tag
        classification_lcc = ''
        language = ''
        work_node = master_dom.getElementsByTagName('bf:Work')
        if work_node.length > 0:
            for sub_node in work_node[0].getElementsByTagName('bf:language'):
                language_url = sub_node.attributes["rdf:resource"].value
                l = language_url.split('/')
                abbreviation = l[len(l) - 1]
                language = get_language(abbreviation)
                break

            for sub_node in work_node[0].getElementsByTagName('bf:classificationLcc'):
                classification_lcc_url = sub_node.attributes["rdf:resource"].value
                l = classification_lcc_url.split('/')
                classification_lcc = l[len(l) - 1]
                break

        # Get the list of all the associated ISBN numbers
        isbn_list = ''
        for isbn in master_dom.getElementsByTagName('bf:isbn10'):
            isbn_resource = isbn.attributes["rdf:resource"].value
            l = isbn_resource.split('/')
            isbn_list += l[len(l)-1] + ', '

        for isbn in master_dom.getElementsByTagName('bf:isbn13'):
            isbn_resource = isbn.attributes["rdf:resource"].value
            l = isbn_resource.split('/')
            isbn_list += l[len(l)-1] + ', '
        isbn_list = isbn_list.rstrip(', ')

        # Get the summary of the record
        summary_url = 'http://minrva.library.illinois.edu/api/display/uiu_' + bib_id
        response = requests.get(summary_url)
        summary = response.json()['summary']

        # Get the list of all the Persons
        person_list = ''
        for person in authority_dom.getElementsByTagName('bf:Person'):
            viaf_url = person.attributes["rdf:about"].value
            author_name = person.getElementsByTagName('bf:label')[0]
            person_list += '<li class="list-group-item">' \
            '<div itemprop="author" itemscope itemtype="http://schema.org/Person">' \
            '<a href="'+ viaf_url +'" itemprop="url"><span itemprop="name">' + author_name.firstChild.data + '</span>' \
            '</a></div></li>'

        # Get the list of all the Topics
        topic_list = ''
        for topic in authority_dom.getElementsByTagName('bf:Topic'):
            subject_url = topic.attributes["rdf:about"].value
            topic_label = topic.getElementsByTagName('bf:label')[0]
            topic_type = topic.getElementsByTagName('rdf:type')[0]
            if "Genre" in topic_type.attributes["rdf:resource"].value:
                topic_list += '<li class="list-group-item"><div itemprop="about" itemscope itemtype="http://schema.org/CreativeWork">' \
                              '<a href="' + subject_url + '"itemprop="genre">' + topic_label.firstChild.data + '</a></div></li>'
            else:
                topic_list += ' <li class="list-group-item">' \
                              '<div itemprop="about" itemscope itemtype="http://schema.org/Book">' \
                              '<a href="' + subject_url + '" itemprop="url">' \
                              '<span itemprop="name">' + topic_label.firstChild.data +'</span></a></div></li>'

        # Bibframe rdf links
        work_url = 'http://sif.library.illinois.edu/bibframe/works/' + bib_id + '_work.rdf'
        instance_url = 'http://sif.library.illinois.edu/bibframe/instance/' + bib_id + '_instance.rdf'
        annotation_url = 'http://sif.library.illinois.edu/bibframe/annotation/' + bib_id + '_annotation.rdf'
        authority_url = 'http://sif.library.illinois.edu/bibframe/authority/' + bib_id + '_authority.rdf'

        template = Template(get_html_template())
        html_string = template.substitute({'title': title, 'instance_resource_url': resource_url, 'classification_lcc': classification_lcc,
                                           'language': language, 'summary': summary, 'publisher': publisher, 'isbn_list': isbn_list,
                                           'person_list_items': person_list, 'topic_list_items': topic_list, 'work_url': work_url,
                                           'instance_url': instance_url, 'annotation_url': annotation_url, 'authority_url': authority_url})

        f.write(html_string)
    except Exception as e:
        print('Error - ', output_file_path, str(e))
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
    finally:
        if f is not None:
            f.close()


# Uses the dictionary from GetLanguages.py output
def get_language(lang):
    language_dict = {'fiu': 'Finno-Ugrian (Other)', 'frm': 'French, Middle (ca. 1300-1600)', 'cho': 'Choctaw', 'eng': 'English', 'bem': 'Bemba', 'nob': 'Norwegian (Bokmål)', 'chg': 'Chagatai', 'hil': 'Hiligaynon',
                     'tpi': 'Tok Pisin', 'krl': 'Karelian', 'bik': 'Bikol', 'gre': 'Greek, Modern (1453- )', 'afr': 'Afrikaans', 'sna': 'Shona', 'ukr': 'Ukrainian', 'sog': 'Sogdian', 'jav': 'Javanese', 'sas': 'Sasak',
                     'hai': 'Haida', 'apa': 'Apache languages', 'tgk': 'Tajik', 'tsn': 'Tswana', 'sgn': 'Sign languages', 'cmc': 'Chamic languages', 'wen': 'Sorbian (Other)', 'hup': 'Hupa', 'lug': 'Ganda', 'tuk': 'Turkmen',
                     'xho': 'Xhosa', 'dgr': 'Dogrib', 'iii': 'Sichuan Yi', 'new': 'Newari', 'sga': 'Irish, Old (to 1100)', 'bal': 'Baluchi', 'ile': 'Interlingue', 'kmb': 'Kimbundu', 'tib': 'Tibetan', 'pau': 'Palauan',
                     'kac': 'Kachin', 'lat': 'Latin', 'dut': 'Dutch', 'mad': 'Madurese', 'ltz': 'Luxembourgish', 'ang': 'English, Old (ca. 450-1100)', 'mkh': 'Mon-Khmer (Other)', 'lun': 'Lunda', 'oji': 'Ojibwa',
                     'efi': 'Efik', 'cpp': 'Creoles and Pidgins, Portuguese-based (Other)', 'ben': 'Bengali', 'mal': 'Malayalam', 'haw': 'Hawaiian', 'mon': 'Mongolian', 'mag': 'Magahi', 'urd': 'Urdu', 'mwr': 'Marwari',
                     'gon': 'Gondi', 'mis': 'Miscellaneous languages', 'chk': 'Chuukese', 'ain': 'Ainu', 'fao': 'Faroese', 'mwl': 'Mirandese', 'kar': 'Karen languages', 'kab': 'Kabyle', 'cze': 'Czech', 'byn': 'Bilin',
                     'gla': 'Scottish Gaelic', 'asm': 'Assamese', 'wln': 'Walloon', 'mus': 'Creek', 'yao': 'Yao (Africa)', 'ber': 'Berber (Other)', 'ban': 'Balinese', 'kor': 'Korean', 'kaz': 'Kazakh', 'uzb': 'Uzbek',
                     'uga': 'Ugaritic', 'bai': 'Bamileke languages', 'lav': 'Latvian', 'cai': 'Central American Indian (Other)', 'dyu': 'Dyula', 'cat': 'Catalan', 'scn': 'Sicilian Italian', 'tgl': 'Tagalog',
                     'myn': 'Mayan languages', 'che': 'Chechen', 'tig': 'Tigré', 'hit': 'Hittite', 'fry': 'Frisian', 'tkl': 'Tokelauan', 'ijo': 'Ijo', 'nqo': "N'Ko", 'cpe': 'Creoles and Pidgins, English-based (Other)',
                     'sal': 'Salishan languages', 'umb': 'Umbundu', 'aka': 'Akan', 'sid': 'Sidamo', 'akk': 'Akkadian', 'kum': 'Kumyk', 'kaa': 'Kara-Kalpak', 'dum': 'Dutch, Middle (ca. 1050-1350)', 'kbd': 'Kabardian',
                     'arp': 'Arapaho', 'dra': 'Dravidian (Other)', 'grc': 'Greek, Ancient (to 1453)', 'hau': 'Hausa', 'alg': 'Algonquian (Other)', 'jbo': 'Lojban (Artificial language)', 'may': 'Malay', 'snk': 'Soninke',
                     'chv': 'Chuvash', 'por': 'Portuguese', 'fin': 'Finnish', 'cpf': 'Creoles and Pidgins, French-based (Other)', 'bho': 'Bhojpuri', 'swe': 'Swedish', 'chn': 'Chinook jargon', 'grb': 'Grebo', 'vol': 'Volapük',
                     'que': 'Quechua', 'jpn': 'Japanese', 'car': 'Carib', 'mlg': 'Malagasy', 'epo': 'Esperanto', 'cau': 'Caucasian (Other)', 'kin': 'Kinyarwanda', 'mlt': 'Maltese', 'kur': 'Kurdish', 'iba': 'Iban',
                     'sit': 'Sino-Tibetan (Other)', 'bos': 'Bosnian', 'lam': 'Lamba (Zambia and Congo)', 'kok': 'Konkani', 'wal': 'Wolayta', 'udm': 'Udmurt', 'aym': 'Aymara', 'orm': 'Oromo', 'slv': 'Slovenian', 'xal': 'Oirat',
                     'ori': 'Oriya', 'nai': 'North American Indian (Other)', 'smn': 'Inari Sami', 'fan': 'Fang', 'sun': 'Sundanese', 'nwc': 'Newari, Old', 'fur': 'Friulian', 'ilo': 'Iloko', 'bih': 'Bihari (Other)',
                     'amh': 'Amharic', 'vot': 'Votic', 'ind': 'Indonesian', 'kom': 'Komi', 'zap': 'Zapotec', 'roh': 'Raeto-Romance', 'lez': 'Lezgian', 'iro': 'Iroquoian (Other)', 'iku': 'Inuktitut', 'swa': 'Swahili',
                     'peo': 'Old Persian (ca. 600-400 B.C.)', 'map': 'Austronesian (Other)', 'non': 'Old Norse', 'ath': 'Athapascan (Other)', 'mno': 'Manobo languages', 'mar': 'Marathi', 'dak': 'Dakota', 'mnc': 'Manchu',
                     'sah': 'Yakut', 'tem': 'Temne', 'fro': 'French, Old (ca. 842-1300)', 'tli': 'Tlingit', 'egy': 'Egyptian', 'alb': 'Albanian', 'kro': 'Kru (Other)', 'cus': 'Cushitic (Other)', 'chm': 'Mari', 'kau': 'Kanuri',
                     'loz': 'Lozi', 'got': 'Gothic', 'ssa': 'Nilo-Saharan (Other)', 'ira': 'Iranian (Other)', 'glv': 'Manx', 'gil': 'Gilbertese', 'crp': 'Creoles and Pidgins (Other)', 'sag': 'Sango (Ubangi Creole)',
                     'pus': 'Pushto', 'nog': 'Nogai', 'mos': 'Mooré', 'baq': 'Basque', 'lol': 'Mongo-Nkundu', 'nub': 'Nubian languages', 'mas': 'Maasai', 'nbl': 'Ndebele (South Africa)', 'ast': 'Bable', 'twi': 'Twi',
                     'tat': 'Tatar', 'bnt': 'Bantu (Other)', 'kua': 'Kuanyama', 'tai': 'Tai (Other)', 'nds': 'Low German', 'kal': 'Kalâtdlisut', 'ine': 'Indo-European (Other)', 'ter': 'Terena', 'bas': 'Basa',
                     'sio': 'Siouan (Other)', 'smj': 'Lule Sami', 'chr': 'Cherokee', 'bra': 'Braj', 'bis': 'Bislama', 'lin': 'Lingala', 'rum': 'Romanian', 'und': 'Undetermined', 'kos': 'Kosraean', 'nzi': 'Nzima',
                     'tup': 'Tupi languages', 'niu': 'Niuean', 'gwi': "Gwich'in", 'nno': 'Norwegian (Nynorsk)', 'ssw': 'Swazi', 'aar': 'Afar', 'srd': 'Sardinian', 'frr': 'North Frisian', 'pon': 'Pohnpeian',
                     'oto': 'Otomian languages', 'csb': 'Kashubian', 'san': 'Sanskrit', 'yid': 'Yiddish', 'glg': 'Galician', 'wol': 'Wolof', 'khm': 'Khmer', 'zul': 'Zulu', 'sai': 'South American Indian (Other)', 'pan': 'Panjabi',
                     'pra': 'Prakrit languages', 'lub': 'Luba-Katanga', 'gay': 'Gayo', 'snd': 'Sindhi', 'him': 'Western Pahari languages', 'lim': 'Limburgish', 'ibo': 'Igbo', 'bua': 'Buriat', 'nap': 'Neapolitan Italian',
                     'tel': 'Telugu', 'yap': 'Yapese', 'abk': 'Abkhaz', 'lao': 'Lao', 'sin': 'Sinhalese', 'rup': 'Aromanian', 'mun': 'Munda (Other)', 'tmh': 'Tamashek', 'nau': 'Nauru', 'chu': 'Church Slavic', 'pol': 'Polish',
                     'mai': 'Maithili', 'day': 'Dayak', 'fat': 'Fanti', 'ido': 'Ido', 'hmo': 'Hiri Motu', 'sad': 'Sandawe', 'gez': 'Ethiopic', 'eka': 'Ekajuk', 'mni': 'Manipuri', 'frs': 'East Frisian', 'chb': 'Chibcha',
                     'sco': 'Scots', 'tur': 'Turkish', 'nah': 'Nahuatl', 'srn': 'Sranan', 'bel': 'Belarusian', 'tet': 'Tetum', 'ton': 'Tongan', 'bul': 'Bulgarian', 'dan': 'Danish', 'dua': 'Duala', 'chp': 'Chipewyan', 'mdr': 'Mandar',
                     'syc': 'Syriac', 'aus': 'Australian languages', 'arm': 'Armenian', 'war': 'Waray', 'kir': 'Kyrgyz', 'cre': 'Cree', 'cos': 'Corsican', 'son': 'Songhai', 'rus': 'Russian', 'tvl': 'Tuvaluan', 'ada': 'Adangme',
                     'cha': 'Chamorro', 'hrv': 'Croatian', 'kan': 'Kannada', 'ave': 'Avestan', 'doi': 'Dogri', 'nyo': 'Nyoro', 'min': 'Minangkabau', 'btk': 'Batak', 'enm': 'English, Middle (1100-1500)', 'sux': 'Sumerian',
                     'sms': 'Skolt Sami', 'cop': 'Coptic', 'khi': 'Khoisan (Other)', 'phi': 'Philippine (Other)', 'nso': 'Northern Sotho', 'ina': 'Interlingua (International Auxiliary Language Association)', 'rom': 'Romani',
                     'chi': 'Chinese', 'bug': 'Bugis', 'tut': 'Altaic (Other)', 'ady': 'Adygei', 'mac': 'Macedonian', 'sel': 'Selkup', 'gaa': 'Gã', 'sla': 'Slavic (Other)', 'sam': 'Samaritan Aramaic', 'yor': 'Yoruba', 'fon': 'Fon',
                     'lui': 'Luiseño', 'din': 'Dinka', 'nor': 'Norwegian', 'mah': 'Marshallese', 'anp': 'Angika', 'nep': 'Nepali', 'lua': 'Luba-Lulua', 'kon': 'Kongo', 'ceb': 'Cebuano', 'crh': 'Crimean Tatar', 'nic': 'Niger-Kordofanian (Other)',
                     'syr': 'Syriac, Modern', 'inc': 'Indic (Other)', 'mak': 'Makasar', 'ful': 'Fula', 'div': 'Divehi', 'art': 'Artificial (Other)', 'hmn': 'Hmong', 'ara': 'Arabic', 'ale': 'Aleut', 'fil': 'Filipino', 'nde': 'Ndebele (Zimbabwe)',
                     'bla': 'Siksika', 'phn': 'Phoenician', 'bak': 'Bashkir', 'roa': 'Romance (Other)', 'den': 'Slavey', 'tsi': 'Tsimshian', 'kam': 'Kamba', 'dsb': 'Lower Sorbian', 'luo': 'Luo (Kenya and Tanzania)', 'wak': 'Wakashan languages',
                     'bin': 'Edo', 'kik': 'Kikuyu', 'znd': 'Zande languages', 'ach': 'Acoli', 'lah': 'Lahndā', 'sme': 'Northern Sami', 'chy': 'Cheyenne', 'dzo': 'Dzongkha', 'osa': 'Osage', 'grn': 'Guarani', 'suk': 'Sukuma', 'nyn': 'Nyankole',
                     'alt': 'Altai', 'gmh': 'German, Middle High (ca. 1050-1500)', 'mdf': 'Moksha', 'gle': 'Irish', 'tah': 'Tahitian', 'tum': 'Tumbuka', 'kru': 'Kurukh', 'slo': 'Slovak', 'zza': 'Zaza', 'nia': 'Nias', 'arg': 'Aragonese',
                     'sem': 'Semitic (Other)', 'ipk': 'Inupiaq', 'moh': 'Mohawk', 'spa': 'Spanish', 'nav': 'Navajo', 'tlh': 'Klingon (Artificial language)', 'tog': 'Tonga (Nyasa)', 'gor': 'Gorontalo', 'bre': 'Breton',
                     'goh': 'German, Old High (ca. 750-1050)', 'kpe': 'Kpelle', 'dar': 'Dargwa', 'kas': 'Kashmiri', 'cad': 'Caddo', 'bad': 'Banda languages', 'srr': 'Serer', 'smo': 'Samoan', 'arw': 'Arawak', 'pam': 'Pampanga', 'ace': 'Achinese',
                     'ndo': 'Ndonga', 'bat': 'Baltic (Other)', 'kha': 'Khasi', 'cor': 'Cornish', 'oci': 'Occitan (post-1500)', 'rap': 'Rapanui', 'del': 'Delaware', 'pli': 'Pali', 'elx': 'Elamite', 'kaw': 'Kawi', 'geo': 'Georgian',
                     'guj': 'Gujarati', 'inh': 'Ingush', 'pag': 'Pangasinan', 'heb': 'Hebrew', 'tir': 'Tigrinya', 'pro': 'Provençal (to 1500)', 'hsb': 'Upper Sorbian', 'sus': 'Susu', 'lad': 'Ladino', 'paa': 'Papuan (Other)', 'uig': 'Uighur',
                     'nya': 'Nyanja', 'tyv': 'Tuvinian', 'smi': 'Sami', 'mul': 'Multiple languages', 'myv': 'Erzya', 'krc': 'Karachay-Balkar', 'ypk': 'Yupik languages', 'tha': 'Thai', 'hat': 'Haitian French Creole', 'hun': 'Hungarian', 'mao': 'Maori',
                     'ota': 'Turkish, Ottoman', 'kho': 'Khotanese', 'ewo': 'Ewondo', 'man': 'Mandingo', 'ava': 'Avaric', 'zxx': 'No linguistic content', 'est': 'Estonian', 'wel': 'Welsh', 'shn': 'Shan', 'tiv': 'Tiv', 'jrb': 'Judeo-Arabic',
                     'fre': 'French', 'gem': 'Germanic (Other)', 'gsw': 'Swiss German', 'arc': 'Aramaic', 'men': 'Mende', 'hin': 'Hindi', 'srp': 'Serbian', 'bur': 'Burmese', 'vie': 'Vietnamese', 'pal': 'Pahlavi', 'sot': 'Sotho', 'lit': 'Lithuanian',
                     'mga': 'Irish, Middle (ca. 1100-1550)', 'zun': 'Zuni', 'tso': 'Tsonga', 'tam': 'Tamil', 'ger': 'German', 'fij': 'Fijian', 'nym': 'Nyamwezi', 'sat': 'Santali', 'awa': 'Awadhi', 'oss': 'Ossetic', 'aze': 'Azerbaijani',
                     'pap': 'Papiamento', 'ewe': 'Ewe', 'ita': 'Italian', 'bej': 'Beja', 'gba': 'Gbaya', 'cel': 'Celtic (Other)', 'kut': 'Kootenai', 'per': 'Persian', 'arn': 'Mapuche', 'was': 'Washoe', 'raj': 'Rajasthani', 'zbl': 'Blissymbolics',
                     'jpr': 'Judeo-Persian', 'ice': 'Icelandic', 'sma': 'Southern Sami', 'afh': 'Afrihili (Artificial language)', 'zha': 'Zhuang', 'ven': 'Venda', 'bam': 'Bambara', 'afa': 'Afroasiatic (Other)', 'run': 'Rundi', 'mic': 'Micmac',
                     'vai': 'Vai', 'her': 'Herero', 'som': 'Somali', 'rar': 'Rarotongan', 'lus': 'Lushai', 'zen': 'Zenaga'}

    if lang in language_dict:
        return language_dict[lang]
    else:
        return ''


def get_html_template():
    html_string = '<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="initial-scale=1.0, user-scalable=no"><meta charset="utf-8"> <title>${title}</title>' \
                  '<link rel="stylesheet" href="//cdn.jsdelivr.net/bootstrap/3.2.0/css/bootstrap.min.css"><link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css">' \
                  '<link rel="stylesheet" href="/prototyping/assets/css/homepage_layouts.css"><link rel="stylesheet" href="/prototyping/assets/css/homepage_colors_fonts.css">' \
                  '<script src="//cdn.jsdelivr.net/g/jquery@2.1,bootstrap@3.2"></script></head><header id="first-navbar"><div class="container"><div class="row"><div class="col-md-12" id="header-full-width-column">' \
                  '<div class="row"><div class="col-sm-6 col-md-7"><a href="http://library.illinois.edu/"><img class="img-responsive" src="/prototyping/assets/university_libraries_wordmark_with_imark.png"></a>' \
                  '</div></div></div></div></div></header><div itemscope itemtype="http://schema.org/Book"><title> ${title}</title><div class="container"><div class="page-header">' \
                  '<span itemprop="name"><h1>${title}<h1></span></div><div class="row"><div class="books__viewer col-md-9 col-md-push-3"><div><div class="books__title"></div>' \
                  '<div class="books__image"></div><div class="books__content"><div class="panel panel-success"><div class="panel-heading">Access</div>  <div class="panel-body"></div><ul class="list-group">' \
                  '<li class="list-group-item"><a href="${instance_resource_url}" target="_blank">e-Book<i class="fa fa-external-link"></i></a></li><li class="list-group-item"><b>LC Classification:</b> ' \
                  '${classification_lcc}</li><li class="list-group-item"> <b>Language:</b> ${language}</li><li class="list-group-item"><b>Held by:</b> University of Illinois</li></li></ul>' \
                  '</div><div class="panel panel-success"><div class="panel-heading">Item Description</div><div class="panel-body"></div><ul class="list-group"><li class="list-group-item">' \
                  '<b> Summary: </b> <span itemprop="description"> ${summary}</span></li><li itemscope itemtype="http://schema.org/Brand" class="list-group-item"><b>Publisher:</b>' \
                  '<span itemprop="name"> ${publisher}</span></li><li class="list-group-item"><b>ISBN(s):</b> ${isbn_list}</li><li class="list-group-item"><b>Notes:</b> Description based on print version record.</li>' \
                  '</ul></div><div class="panel panel-success"><div class="panel-heading">Subject Terms / Creators</div><div class="panel-body"></div><ul class="list-group">${person_list_items}${topic_list_items}' \
                  '</ul></div><div class="panel panel-info"><div class="panel-heading">Bibframe RDF</div><div class="panel-body"></div><ul class="list-group"><li class="list-group-item">Work' \
                  '<a href="${work_url}"><i class="fa fa-download"></i> </a></li><li class="list-group-item">Instance<a href="${instance_url}"><i class="fa fa-download"></i></a></li><li class="list-group-item">Annotation' \
                  '<a href="${annotation_url}"><i class="fa fa-download"></i></a></li><li class="list-group-item">Authority<a href="${authority_url}"><i class="fa fa-download"></i></a></li></li></ul></div></div><hr ' \
                  'class="hidden-md hidden-lg"></div></div><div class="books__library col-md-3 col-md-pull-9"><div class="list-group"><h6>Item(s)</h6><a class="list-group-item" href="#books/1"><h6 class="list-group-item-heading">' \
                  '${title}</h6><p class="list-group-item-text"></p></a></div></div></div></div></div></div></div><script src="//cdn.jsdelivr.net/g/jquery@2.1,bootstrap@3.2,underscorejs@1.6,backbonejs@1.1" type="text/javascript">' \
                  '</script></body></html>'

    return html_string


if __name__ == '__main__':
    try:
        # input_master_folder_path = sys.argv[1]
        # input_authority_folder_path = sys.argv[2]
        # input_instance_folder_path = sys.argv[3]
        # output_folder_path = sys.argv[4]

        input_master_folder_path = '/home/suma/Desktop/UnderGradLibrary/Master'
        input_authority_folder_path = '/home/suma/Desktop/UnderGradLibrary/Authority'
        input_instance_folder_path = '/home/suma/Desktop/UnderGradLibrary/Instance'
        output_folder_path = '/home/suma/Desktop/UnderGradLibrary/Templates'
    except IndexError:
        print('Please provide all input parameters\nUsage: python HTMLGeneration.py /path/to/folder/containing/Master/RDF/files '
              '/path/to/folder/containing/Authority/RDF/files /path/to/folder/containing/Instance/RDF/files /path/to/folder/to/store/HTML/Templates')
        sys.exit(0)

    for root, dirs, file_names in os.walk(input_master_folder_path):
        for file in file_names:
            input_master_file_path = root + '/' + file
            bib_id = file.split('_')[0]
            input_authority_file_path = input_authority_folder_path + '/' + bib_id + '_authority.rdf'
            input_instance_file_path = input_instance_folder_path + '/' + bib_id + '_instance.rdf'
            output_file_path = output_folder_path + '/' + bib_id + '.html'
            main(input_master_file_path, input_authority_file_path, input_instance_file_path, output_file_path, bib_id)