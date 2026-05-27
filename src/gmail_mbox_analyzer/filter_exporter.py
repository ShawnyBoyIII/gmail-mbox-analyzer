from typing import List, Literal
import xml.etree.ElementTree as ET  # nosec B405 Required to build the tree
from defusedxml.minidom import parseString


def generate_gmail_filters_xml(
    emails: List[str], action: Literal["trash", "archive"] = "trash"
) -> str:
    """
    Generates a Gmail filter XML string for a list of emails.
    """
    # Create the root atom feed element
    feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
    feed.set("xmlns:apps", "http://schemas.google.com/apps/2006")

    title = ET.SubElement(feed, "title")
    title.text = "Mail Filters"

    for email in emails:
        if not email:
            continue

        entry = ET.SubElement(feed, "entry")

        ET.SubElement(entry, "category", term="filter")

        title_entry = ET.SubElement(entry, "title")
        title_entry.text = "Mail Filter"

        ET.SubElement(entry, "content")

        # Filter condition (From)
        ET.SubElement(entry, "apps:property", name="from", value=email)

        # Filter action
        if action == "trash":
            ET.SubElement(
                entry, "apps:property", name="shouldTrash", value="true"
            )
        elif action == "archive":
            ET.SubElement(
                entry, "apps:property", name="shouldArchive", value="true"
            )

    # Pretty print
    rough_string = ET.tostring(feed, "utf-8")
    reparsed = parseString(rough_string)

    # We remove the xml declaration <?xml version="1.0" ?> to match typical Google exports,
    # but it's valid with it too. We will keep the default minidom output which includes it.
    return reparsed.toprettyxml(indent="    ")
