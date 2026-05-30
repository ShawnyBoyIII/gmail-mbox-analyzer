import unittest
import defusedxml.ElementTree as ET
from src.gmail_mbox_analyzer.filter_exporter import generate_gmail_filters_xml


class TestFilterExporter(unittest.TestCase):
    def test_generate_gmail_filters_xml_trash(self):
        emails = ["spam1@example.com", "spam2@example.com"]
        xml_str = generate_gmail_filters_xml(emails, action="trash")

        # Basic assertions on the string
        self.assertIn("spam1@example.com", xml_str)
        self.assertIn("spam2@example.com", xml_str)
        self.assertIn('name="shouldTrash" value="true"', xml_str)
        self.assertNotIn('name="shouldArchive"', xml_str)

        # Parse the XML to ensure it's valid
        root = DET.fromstring(xml_str)

        # Check namespaces
        self.assertEqual(root.tag, "{http://www.w3.org/2005/Atom}feed")

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        self.assertEqual(len(entries), 2)

        # Check the properties of the first entry
        props = entries[0].findall("{http://schemas.google.com/apps/2006}property")
        prop_names = [p.get("name") for p in props]
        self.assertIn("from", prop_names)
        self.assertIn("shouldTrash", prop_names)

    def test_generate_gmail_filters_xml_archive(self):
        emails = ["newsletter@example.com"]
        xml_str = generate_gmail_filters_xml(emails, action="archive")

        self.assertIn("newsletter@example.com", xml_str)
        self.assertIn('name="shouldArchive" value="true"', xml_str)
        self.assertNotIn('name="shouldTrash"', xml_str)

        root = DET.fromstring(xml_str)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        self.assertEqual(len(entries), 1)

        props = entries[0].findall("{http://schemas.google.com/apps/2006}property")
        prop_names = [p.get("name") for p in props]
        self.assertIn("shouldArchive", prop_names)

    def test_empty_emails(self):
        xml_str = generate_gmail_filters_xml([])
        root = DET.fromstring(xml_str)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        self.assertEqual(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
