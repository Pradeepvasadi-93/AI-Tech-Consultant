import requests
import xml.etree.ElementTree as ET

def parse_sitemap(url: str):
    resp = requests.get(url)
    root = ET.fromstring(resp.text)
    urls = [elem.text for elem in root.findall(".//{*}loc")]
    return urls
