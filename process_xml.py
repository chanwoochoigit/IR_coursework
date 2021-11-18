from xml.etree import cElementTree as ET

class XMLProcesser():

    def get_xml_root(self, path):
        with open(path) as f:
            xmlstr = f.read()

        return ET.fromstring(xmlstr)

    def extract_text_from_path(self, path):
        root = self.get_xml_root(path)
        doc_dict = {}
        for page in root:
            doc_number = page.find('DOCNO').text
            text = page.find('HEADLINE').text.replace('\n',' ').replace('\t',' ').replace('  ', ' ') + \
                   page.find('TEXT').text.replace('\n',' ').replace('\t',' ').replace('  ', ' ')
            doc_dict[doc_number] = text

        return doc_dict


